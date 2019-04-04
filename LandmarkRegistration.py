from __future__ import division
from __future__ import print_function
import os, string
import time
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *

import RegistrationLib

#
# LandmarkRegistration
#

class LandmarkRegistration(ScriptedLoadableModule):
  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    parent.title = "Landmark Registration"
    parent.categories = ["Registration"]
    parent.dependencies = []
    parent.contributors = ["Steve Pieper (Isomics)"] # replace with "Firstname Lastname (Org)"
    parent.helpText = string.Template("""
    This module organizes a fixed and moving volume along with a set of corresponding
    landmarks (paired fiducials) to assist in manual registration.

Please refer to <a href=\"$a/Documentation/$b.$c/Modules/LandmarkRegistration\"> the documentation</a>.

    """).substitute({ 'a':parent.slicerWikiUrl, 'b':slicer.app.majorVersion, 'c':slicer.app.minorVersion })
    parent.acknowledgementText = """
    This file was originally developed by Steve Pieper, Isomics, Inc.
    It was partially funded by NIH grant 3P41RR013218-12S1 and P41 EB015902 the
    Neuroimage Analysis Center (NAC) a Biomedical Technology Resource Center supported
    by the National Institute of Biomedical Imaging and Bioengineering (NIBIB).
    And this work is part of the "National Alliance for Medical Image
    Computing" (NAMIC), funded by the National Institutes of Health
    through the NIH Roadmap for Medical Research, Grant U54 EB005149.
    Information on the National Centers for Biomedical Computing
    can be obtained from http://nihroadmap.nih.gov/bioinformatics.
    This work is also supported by NIH grant 1R01DE024450-01A1
    "Quantification of 3D Bony Changes in Temporomandibular Joint Osteoarthritis"
    (TMJ-OA).
    """ # replace with organization, grant and thanks.

#
# qLandmarkRegistrationWidget
#

class LandmarkRegistrationWidget(ScriptedLoadableModuleWidget):
  """The module GUI widget"""

  def __init__(self, parent=None):
    ScriptedLoadableModuleWidget.__init__(self, parent)
    self.logic = LandmarkRegistrationLogic()
    self.logic.registrationState = self.registrationState
    self.sliceNodesByViewName = {}
    self.sliceNodesByVolumeID = {}
    self.observerTags = []
    self.viewNames = ("Fixed", "Moving", "Transformed")
    self.volumeSelectDialog = None
    self.currentRegistrationInterface = None
    self.currentLocalRefinementInterface = None

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    if self.developerMode:
      # reload and run specific tests
      scenarios = ("Basic", "Affine", "ThinPlate", "VTKv6Picking", "ManyLandmarks")
      for scenario in scenarios:
        button = qt.QPushButton("Reload and Test %s" % scenario)
        self.reloadAndTestButton.toolTip = "Reload this module and then run the %s self test." % scenario
        self.reloadCollapsibleButton.layout().addWidget(button)
        button.connect('clicked()', lambda s=scenario: self.onReloadAndTest(scenario=s))

    self.selectVolumesButton = qt.QPushButton("Select Volumes To Register")
    self.selectVolumesButton.connect('clicked(bool)', self.enter)
    self.layout.addWidget(self.selectVolumesButton)

    self.interfaceFrame = qt.QWidget(self.parent)
    self.interfaceFrame.setLayout(qt.QVBoxLayout())
    self.layout.addWidget(self.interfaceFrame)

    #
    # Parameters Area
    #
    parametersCollapsibleButton = ctk.ctkCollapsibleButton()
    parametersCollapsibleButton.text = "Parameters"
    self.interfaceFrame.layout().addWidget(parametersCollapsibleButton)
    parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)

    self.volumeSelectors = {}
    for viewName in self.viewNames:
      self.volumeSelectors[viewName] = slicer.qMRMLNodeComboBox()
      self.volumeSelectors[viewName].nodeTypes = ( ("vtkMRMLScalarVolumeNode"), "" )
      self.volumeSelectors[viewName].selectNodeUponCreation = False
      self.volumeSelectors[viewName].addEnabled = False
      self.volumeSelectors[viewName].removeEnabled = True
      self.volumeSelectors[viewName].noneEnabled = True
      self.volumeSelectors[viewName].showHidden = False
      self.volumeSelectors[viewName].showChildNodeTypes = True
      self.volumeSelectors[viewName].setMRMLScene( slicer.mrmlScene )
      self.volumeSelectors[viewName].setToolTip( "Pick the %s volume." % viewName.lower() )
      self.volumeSelectors[viewName].enabled = False
      parametersFormLayout.addRow("%s Volume " % viewName, self.volumeSelectors[viewName])

    self.volumeSelectors["Transformed"].addEnabled = True
    self.volumeSelectors["Transformed"].selectNodeUponCreation = True
    self.volumeSelectors["Transformed"].setToolTip( "Pick the transformed volume, which is the target for the registration." )

    self.transformSelector = slicer.qMRMLNodeComboBox()
    self.transformSelector.nodeTypes = ( ("vtkMRMLTransformNode"), "" )
    self.transformSelector.selectNodeUponCreation = True
    self.transformSelector.addEnabled = True
    self.transformSelector.removeEnabled = True
    self.transformSelector.noneEnabled = True
    self.transformSelector.showHidden = False
    self.transformSelector.showChildNodeTypes = False
    self.transformSelector.setMRMLScene( slicer.mrmlScene )
    self.transformSelector.setToolTip( "The transform for linear registration" )
    self.transformSelector.enabled = False
    parametersFormLayout.addRow("Target Transform ", self.transformSelector)

    #
    # Visualization Widget
    # - handy options for controlling the view
    #
    self.visualizationWidget = RegistrationLib.VisualizationWidget(self.logic)
    self.visualizationWidget.connect("layoutRequested(mode,volumesToShow)", self.onLayout)
    parametersFormLayout.addRow(self.visualizationWidget.widget)

    #
    # Landmarks Widget
    # - manages landmarks
    #
    self.landmarksWidget = RegistrationLib.LandmarksWidget(self.logic)
    self.landmarksWidget.connect("landmarkPicked(landmarkName)", self.onLandmarkPicked)
    self.landmarksWidget.connect("landmarkMoved(landmarkName)", self.onLandmarkMoved)
    self.landmarksWidget.connect("landmarkEndMoving(landmarkName)", self.onLandmarkEndMoving)
    parametersFormLayout.addRow(self.landmarksWidget.widget)

    #
    # Local landmark refinement
    #
    self.localRefinementCollapsibleButton = ctk.ctkCollapsibleButton()
    self.localRefinementCollapsibleButton.text = "Local Refinement"
    self.interfaceFrame.layout().addWidget(self.localRefinementCollapsibleButton)
    localRefinementFormLayout = qt.QFormLayout(self.localRefinementCollapsibleButton)

    self.localRefineButton = qt.QPushButton()
    self.localRefineButton.text = 'No landmark selected for local refinement'
    self.localRefineButton.toolTip = 'Refine the currently selected landmark using local registration'
    self.localRefineButton.connect('clicked()', self.onLocalRefineClicked)
    localRefinementFormLayout.addRow(self.localRefineButton)

    try:
      slicer.modules.registrationPlugins
    except AttributeError:
      slicer.modules.registrationPlugins = {}

    self.localRefinementMethodBox = qt.QGroupBox("Local Refinement Method")
    self.localRefinementMethodBox.setLayout(qt.QFormLayout())
    self.localRefinementMethodButtons = {}
    self.localRefinementMethods = sorted(slicer.modules.registrationPlugins.keys())
    for localRefinementMethod in self.localRefinementMethods:
      plugin = slicer.modules.registrationPlugins[localRefinementMethod]
      if plugin.type == "Refinement":
        self.localRefinementMethodButtons[localRefinementMethod] = qt.QRadioButton()
        self.localRefinementMethodButtons[localRefinementMethod].text = plugin.name
        self.localRefinementMethodButtons[localRefinementMethod].setToolTip(plugin.tooltip)
        self.localRefinementMethodButtons[localRefinementMethod].connect("clicked()",
                                  lambda t=localRefinementMethod: self.onLocalRefinementMethod(t))
        self.localRefinementMethodBox.layout().addWidget(
                                  self.localRefinementMethodButtons[localRefinementMethod])
    localRefinementFormLayout.addWidget(self.localRefinementMethodBox)


    #
    # Registration Options
    #
    self.registrationCollapsibleButton = ctk.ctkCollapsibleButton()
    self.registrationCollapsibleButton.text = "Registration"
    self.interfaceFrame.layout().addWidget(self.registrationCollapsibleButton)
    registrationFormLayout = qt.QFormLayout(self.registrationCollapsibleButton)

    #
    # registration type selection
    # - allows selection of the active registration type to display
    #
    try:
      slicer.modules.registrationPlugins
    except AttributeError:
      slicer.modules.registrationPlugins = {}

    self.registrationTypeBox = qt.QGroupBox("Registration Type")
    self.registrationTypeBox.setLayout(qt.QFormLayout())
    self.registrationTypeButtons = {}
    self.registrationTypes = sorted(slicer.modules.registrationPlugins.keys())
    for registrationType in self.registrationTypes:
      plugin = slicer.modules.registrationPlugins[registrationType]
      if plugin.type == "Registration":
        self.registrationTypeButtons[registrationType] = qt.QRadioButton()
        self.registrationTypeButtons[registrationType].text = plugin.name
        self.registrationTypeButtons[registrationType].setToolTip(plugin.tooltip)
        self.registrationTypeButtons[registrationType].connect("clicked()",
                                  lambda t=registrationType: self.onRegistrationType(t))
        self.registrationTypeBox.layout().addWidget(
                                  self.registrationTypeButtons[registrationType])
    registrationFormLayout.addWidget(self.registrationTypeBox)

    # connections
    for selector in self.volumeSelectors.values():
      selector.connect("currentNodeChanged(vtkMRMLNode*)", self.onVolumeNodeSelect)

    # listen to the scene
    self.addObservers()

    # Add vertical spacer
    self.layout.addStretch(1)

  def enter(self):
    self.interfaceFrame.enabled = False
    self.setupDialog()

  def setupDialog(self):
    """setup dialog"""

    if not self.volumeSelectDialog:
      self.volumeSelectDialog = qt.QDialog(slicer.util.mainWindow())
      self.volumeSelectDialog.objectName = 'LandmarkRegistrationVolumeSelect'
      self.volumeSelectDialog.setLayout( qt.QVBoxLayout() )

      self.volumeSelectLabel = qt.QLabel()
      self.volumeSelectDialog.layout().addWidget( self.volumeSelectLabel )

      self.volumeSelectorFrame = qt.QFrame()
      self.volumeSelectorFrame.objectName = 'VolumeSelectorFrame'
      self.volumeSelectorFrame.setLayout( qt.QFormLayout() )
      self.volumeSelectDialog.layout().addWidget( self.volumeSelectorFrame )

      self.volumeDialogSelectors = {}
      for viewName in ('Fixed', 'Moving',):
        self.volumeDialogSelectors[viewName] = slicer.qMRMLNodeComboBox()
        self.volumeDialogSelectors[viewName].nodeTypes = ( ("vtkMRMLScalarVolumeNode"), "" )
        self.volumeDialogSelectors[viewName].selectNodeUponCreation = False
        self.volumeDialogSelectors[viewName].addEnabled = False
        self.volumeDialogSelectors[viewName].removeEnabled = True
        self.volumeDialogSelectors[viewName].noneEnabled = True
        self.volumeDialogSelectors[viewName].showHidden = False
        self.volumeDialogSelectors[viewName].showChildNodeTypes = True
        self.volumeDialogSelectors[viewName].setMRMLScene( slicer.mrmlScene )
        self.volumeDialogSelectors[viewName].setToolTip( "Pick the %s volume." % viewName.lower() )
        self.volumeSelectorFrame.layout().addRow("%s Volume " % viewName, self.volumeDialogSelectors[viewName])

      self.volumeButtonFrame = qt.QFrame()
      self.volumeButtonFrame.objectName = 'VolumeButtonFrame'
      self.volumeButtonFrame.setLayout( qt.QHBoxLayout() )
      self.volumeSelectDialog.layout().addWidget( self.volumeButtonFrame )

      self.volumeDialogApply = qt.QPushButton("Apply", self.volumeButtonFrame)
      self.volumeDialogApply.objectName = 'VolumeDialogApply'
      self.volumeDialogApply.setToolTip( "Use currently selected volume nodes." )
      self.volumeButtonFrame.layout().addWidget(self.volumeDialogApply)

      self.volumeDialogCancel = qt.QPushButton("Cancel", self.volumeButtonFrame)
      self.volumeDialogCancel.objectName = 'VolumeDialogCancel'
      self.volumeDialogCancel.setToolTip( "Cancel current operation." )
      self.volumeButtonFrame.layout().addWidget(self.volumeDialogCancel)

      self.volumeDialogApply.connect("clicked()", self.onVolumeDialogApply)
      self.volumeDialogCancel.connect("clicked()", self.volumeSelectDialog.hide)

    self.volumeSelectLabel.setText( "Pick the volumes to use for landmark-based linear registration" )
    self.volumeSelectDialog.show()

  # volumeSelectDialog callback (slot)
  def onVolumeDialogApply(self):
    self.volumeSelectDialog.hide()
    fixedID = self.volumeDialogSelectors['Fixed'].currentNodeID
    movingID = self.volumeDialogSelectors['Moving'].currentNodeID
    if fixedID and movingID:
      self.volumeSelectors['Fixed'].setCurrentNodeID(fixedID)
      self.volumeSelectors['Moving'].setCurrentNodeID(movingID)
      # create transform and transformed if needed
      transform = self.transformSelector.currentNode()
      if not transform:
        self.transformSelector.addNode()
        transform = self.transformSelector.currentNode()
      transformed = self.volumeSelectors['Transformed'].currentNode()
      if not transformed:
        volumesLogic = slicer.modules.volumes.logic()
        moving = self.volumeSelectors['Moving'].currentNode()
        transformedName = "%s-transformed" % moving.GetName()
        transformed = slicer.mrmlScene.GetFirstNodeByName(transformedName)
        if not transformed:
          transformed = volumesLogic.CloneVolume(slicer.mrmlScene, moving, transformedName)
        transformed.SetAndObserveTransformNodeID(transform.GetID())
      self.volumeSelectors['Transformed'].setCurrentNode(transformed)
      self.onLayout()
      self.interfaceFrame.enabled = True

  def cleanup(self):
    self.removeObservers()
    self.landmarksWidget.removeLandmarkObservers()

  def addObservers(self):
    """Observe the mrml scene for changes that we wish to respond to.
    scene observer:
     - whenever a new node is added, check if it was a new fiducial.
       if so, transform it into a landmark by creating a matching
       fiducial for other volumes
    fiducial obserers:
     - when fiducials are manipulated, perform (or schedule) an update
       to the currently active registration method.
    """
    tag = slicer.mrmlScene.AddObserver(slicer.mrmlScene.NodeAddedEvent, self.landmarksWidget.requestNodeAddedUpdate)
    self.observerTags.append( (slicer.mrmlScene, tag) )
    tag = slicer.mrmlScene.AddObserver(slicer.mrmlScene.NodeRemovedEvent, self.landmarksWidget.requestNodeAddedUpdate)
    self.observerTags.append( (slicer.mrmlScene, tag) )

  def removeObservers(self):
    """Remove observers and any other cleanup needed to
    disconnect from the scene"""
    for obj,tag in self.observerTags:
      obj.RemoveObserver(tag)
    self.observerTags = []

  def registrationState(self):
    """Return an instance of RegistrationState populated
    with current gui parameters"""
    state = RegistrationLib.RegistrationState()
    state.logic = self.logic
    state.fixed = self.volumeSelectors["Fixed"].currentNode()
    state.moving = self.volumeSelectors["Moving"].currentNode()
    state.transformed = self.volumeSelectors["Transformed"].currentNode()
    state.fixedFiducials = self.logic.volumeFiducialList(state.fixed)
    state.movingFiducials = self.logic.volumeFiducialList(state.moving)
    state.transformedFiducials = self.logic.volumeFiducialList(state.transformed)
    state.transform = self.transformSelector.currentNode()
    state.currentLandmarkName = self.landmarksWidget.selectedLandmark

    return(state)

  def currentVolumeNodes(self):
    """List of currently selected volume nodes"""
    volumeNodes = []
    for selector in self.volumeSelectors.values():
      volumeNode = selector.currentNode()
      if volumeNode:
        volumeNodes.append(volumeNode)
    return(volumeNodes)

  def onVolumeNodeSelect(self):
    """When one of the volume selectors is changed"""
    volumeNodes = self.currentVolumeNodes()
    self.landmarksWidget.setVolumeNodes(volumeNodes)
    fixed = self.volumeSelectors['Fixed'].currentNode()
    moving = self.volumeSelectors['Moving'].currentNode()
    transformed = self.volumeSelectors['Transformed'].currentNode()
    self.registrationCollapsibleButton.enabled = bool(fixed and moving)
    self.logic.hiddenFiducialVolumes = (transformed,)

  def onLayout(self, layoutMode="Axi/Sag/Cor",volumesToShow=None):
    """When the layout is changed by the VisualizationWidget
    volumesToShow: list of the volumes to include, None means include all
    """
    volumeNodes = []
    activeViewNames = []
    for viewName in self.viewNames:
      volumeNode = self.volumeSelectors[viewName].currentNode()
      if volumeNode and not (volumesToShow and viewName not in volumesToShow):
        volumeNodes.append(volumeNode)
        activeViewNames.append(viewName)
    import CompareVolumes
    compareLogic = CompareVolumes.CompareVolumesLogic()
    oneViewModes = ('Axial', 'Sagittal', 'Coronal',)
    if layoutMode in oneViewModes:
      self.sliceNodesByViewName = compareLogic.viewerPerVolume(volumeNodes,viewNames=activeViewNames,orientation=layoutMode)
    elif layoutMode == 'Axi/Sag/Cor':
      self.sliceNodesByViewName = compareLogic.viewersPerVolume(volumeNodes)
    self.overlayFixedOnTransformed()
    self.updateSliceNodesByVolumeID()
    self.onLandmarkPicked(self.landmarksWidget.selectedLandmark)

  def overlayFixedOnTransformed(self):
    """If there are viewers showing the tranfsformed volume
    in the background, make the foreground volume be the fixed volume
    and set opacity to 0.5"""
    fixedNode = self.volumeSelectors['Fixed'].currentNode()
    transformedNode = self.volumeSelectors['Transformed'].currentNode()
    if transformedNode:
      compositeNodes = slicer.util.getNodesByClass('vtkMRMLSliceCompositeNode')
      for compositeNode in compositeNodes:
        if compositeNode.GetBackgroundVolumeID() == transformedNode.GetID():
          compositeNode.SetForegroundVolumeID(fixedNode.GetID())
          compositeNode.SetForegroundOpacity(0.5)

  def onRegistrationType(self,pickedRegistrationType):
    """Pick which registration type to display"""
    if self.currentRegistrationInterface:
      self.currentRegistrationInterface.destroy()
    interfaceClass = slicer.modules.registrationPlugins[pickedRegistrationType]
    self.currentRegistrationInterface = interfaceClass(self.registrationCollapsibleButton)
    # argument registrationState is a callable that gets current state
    self.currentRegistrationInterface.create(self.registrationState)
    self.currentRegistrationInterface.onLandmarkEndMoving(self.registrationState)

  def onLocalRefinementMethod(self,pickedLocalRefinementMethod):
    """Pick which local refinement method to display"""
    if self.currentLocalRefinementInterface:
      self.currentLocalRefinementInterface.destroy()
    interfaceClass = slicer.modules.registrationPlugins[pickedLocalRefinementMethod]
    self.currentLocalRefinementInterface = interfaceClass(self.localRefinementCollapsibleButton)
    # argument registrationState is a callable that gets current state, current same instance is shared for registration and local refinement
    self.currentLocalRefinementInterface.create(self.registrationState)

  def updateSliceNodesByVolumeID(self):
    """Build a mapping to a list of slice nodes
    node that are currently displaying a given volumeID"""
    compositeNodes = slicer.util.getNodesByClass('vtkMRMLSliceCompositeNode')
    self.sliceNodesByVolumeID = {}
    if self.sliceNodesByViewName:
      for sliceNode in self.sliceNodesByViewName.values():
        for compositeNode in compositeNodes:
          if compositeNode.GetLayoutName() == sliceNode.GetLayoutName():
            volumeID = compositeNode.GetBackgroundVolumeID()
            if volumeID in self.sliceNodesByVolumeID:
              self.sliceNodesByVolumeID[volumeID].append(sliceNode)
            else:
              self.sliceNodesByVolumeID[volumeID] = [sliceNode,]

  def restrictLandmarksToViews(self):
    """Set fiducials so they only show up in the view
    for the volume on which they were defined.
    Also turn off other fiducial lists, since leaving
    them visible can interfere with picking.
    Since multiple landmarks will be in the same lists, keep track of the
    lists that have been processed to avoid duplicated updates.
    """
    slicer.mrmlScene.StartState(slicer.mrmlScene.BatchProcessState)
    volumeNodes = self.currentVolumeNodes()
    if self.sliceNodesByViewName:
      landmarks = self.logic.landmarksForVolumes(volumeNodes)
      activeFiducialLists = []
      processedFiducialLists = []
      for landmarkName in landmarks:
        for fiducialList,index in landmarks[landmarkName]:
          if fiducialList in processedFiducialLists:
            continue
          processedFiducialLists.append(fiducialList)
          activeFiducialLists.append(fiducialList)
          displayNode = fiducialList.GetDisplayNode()
          displayNode.RemoveAllViewNodeIDs()
          volumeNodeID = fiducialList.GetAttribute("AssociatedNodeID")
          if volumeNodeID:
            if volumeNodeID in self.sliceNodesByVolumeID:
              for sliceNode in self.sliceNodesByVolumeID[volumeNodeID]:
                displayNode.AddViewNodeID(sliceNode.GetID())
                for hiddenVolume in self.logic.hiddenFiducialVolumes:
                  if hiddenVolume and volumeNodeID == hiddenVolume.GetID():
                    displayNode.SetVisibility(False)
      allFiducialLists = slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode')
      for fiducialList in allFiducialLists:
        if fiducialList not in activeFiducialLists:
          displayNode = fiducialList.GetDisplayNode()
          if displayNode:
            displayNode.SetVisibility(False)
            displayNode.RemoveAllViewNodeIDs()
            displayNode.AddViewNodeID("__invalid_view_id__")
    slicer.mrmlScene.EndState(slicer.mrmlScene.BatchProcessState)

  def onLocalRefineClicked(self):
    """Refine the selected landmark"""
    timing = True
    slicer.mrmlScene.StartState(slicer.mrmlScene.BatchProcessState)

    if self.landmarksWidget.selectedLandmark != None :
      if self.currentLocalRefinementInterface:
        state = self.registrationState()
        self.currentLocalRefinementInterface.refineLandmark(state)
      if timing: onLandmarkPickedStart = time.time()
      self.onLandmarkPicked(self.landmarksWidget.selectedLandmark)
      if timing: onLandmarkPickedEnd = time.time()
      if timing: print('Time to update visualization ' + str(onLandmarkPickedEnd - onLandmarkPickedStart) + ' seconds')

    slicer.mrmlScene.EndState(slicer.mrmlScene.BatchProcessState)

  def onLandmarkPicked(self,landmarkName):
    """Jump all slice views such that the selected landmark
    is visible"""
    if not self.landmarksWidget.movingView:
      # only change the fiducials if they are not being manipulated
      self.restrictLandmarksToViews()
    self.updateSliceNodesByVolumeID()
    volumeNodes = self.currentVolumeNodes()
    landmarksByName = self.logic.landmarksForVolumes(volumeNodes)
    if landmarkName in landmarksByName:
      for fiducialList,index in landmarksByName[landmarkName]:
        volumeNodeID = fiducialList.GetAttribute("AssociatedNodeID")
        if volumeNodeID in self.sliceNodesByVolumeID:
          point = [0,]*3
          fiducialList.GetNthFiducialPosition(index,point)
          for sliceNode in self.sliceNodesByVolumeID[volumeNodeID]:
            if sliceNode.GetLayoutName() != self.landmarksWidget.movingView:
              sliceNode.JumpSliceByCentering(*point)
    if landmarkName != None :
      self.localRefineButton.text = 'Refine landmark ' + landmarkName
    else:
      self.localRefineButton.text = 'No landmark selected for refinement'

  def onLandmarkMoved(self,landmarkName):
    """Called when a landmark is moved (probably through
    manipulation of the widget in the slice view).
    This updates the active registration"""
    if self.currentRegistrationInterface:
      state = self.registrationState()
      self.currentRegistrationInterface.onLandmarkMoved(state)

  def onLandmarkEndMoving(self,landmarkName):
    """Called when a landmark is done being moved (e.g. when mouse button released)"""
    if self.currentRegistrationInterface:
      state = self.registrationState()
      self.currentRegistrationInterface.onLandmarkEndMoving(state)

  def onReload(self,moduleName="LandmarkRegistration"):
    """Generic reload method for any scripted module.
    ModuleWizard will subsitute correct default moduleName.
    Note: customized for use in LandmarkRegistration
    """

    # Print a clearly visible separator to make it easier
    # to distinguish new error messages (during/after reload)
    # from old ones.
    print('\n' * 2)
    print('-' * 30)
    print('Reloading module: '+self.moduleName)
    print('-' * 30)
    print('\n' * 2)

    import imp, sys, os, slicer

    # first, destroy the current plugin, since it will
    # contain subclasses of the RegistrationLib modules
    if self.currentRegistrationInterface:
      self.currentRegistrationInterface.destroy()
    if self.currentLocalRefinementInterface:
      self.currentLocalRefinementInterface.destroy()

    # now reload the RegistrationLib source code
    # - set source file path
    # - load the module to the global space
    filePath = eval('slicer.modules.%s.path' % moduleName.lower())
    p = os.path.dirname(filePath)
    if not sys.path.__contains__(p):
      sys.path.insert(0,p)
    for subModuleName in ("pqWidget", "Visualization", "Landmarks", ):
      fp = open(filePath, "r")
      globals()[subModuleName] = imp.load_module(
          subModuleName, fp, filePath, ('.py', 'r', imp.PY_SOURCE))
      fp.close()

    # now reload all the support code and have the plugins
    # re-register themselves with slicer
    oldPlugins = slicer.modules.registrationPlugins
    slicer.modules.registrationPlugins = {}
    for plugin in oldPlugins.values():
      pluginModuleName = plugin.__module__.lower()
      if hasattr(slicer.modules,pluginModuleName):
        # for a plugin from an extension, need to get the source path
        # from the module
        module = getattr(slicer.modules,pluginModuleName)
        sourceFile = module.path
      else:
        # for a plugin built with slicer itself, the file path comes
        # from the pyc path noted as __file__ at startup time
        sourceFile = plugin.sourceFile.replace('.pyc', '.py')
      imp.load_source(plugin.__module__, sourceFile)
    oldPlugins = None

    slicer.util.reloadScriptedModule("LandmarkRegistration")

#
# LandmarkRegistrationLogic
#

class LandmarkRegistrationLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget

  The representation of Landmarks is in terms of matching FiducialLists
  with one list per VolumeNode.

  volume1 <-- associated node -- FiducialList1
                                 - anatomy 1
                                 - anatomy 2
                                 ...
  volume2 <-- associated node -- FiducialList2
                                 - anatomy 1
                                 - anatomy 2
                                 ...

  The Fiducial List is only made visible in the viewer that
  has the associated node in the bg.

  Set of identically named fiducials in lists associated with the
  current moving and fixed volumes define a 'landmark'.

  Note that it is the name, not the index, of the anatomy that defines
  membership in a landmark.  Use a pair (fiducialListNodes,index) to
  identify a fiducial.
  """
  def __init__(self):
    ScriptedLoadableModuleLogic.__init__(self)
    self.linearMode = 'Rigid'
    self.hiddenFiducialVolumes = ()
    self.cropLogic = None
    if hasattr(slicer.modules, 'cropvolume'):
      self.cropLogic = slicer.modules.cropvolume.logic()


  def setFiducialListDisplay(self,fiducialList):
    displayNode = fiducialList.GetDisplayNode()
    # TODO: pick appropriate defaults
    # 135,135,84
    displayNode.SetTextScale(6.)
    displayNode.SetGlyphScale(6.)
    displayNode.SetGlyphTypeFromString('StarBurst2D')
    displayNode.SetColor((1,1,0.4))
    displayNode.SetSelectedColor((1,1,0))
    #displayNode.GetAnnotationTextDisplayNode().SetColor((1,1,0))
    displayNode.SetVisibility(True)

  def addFiducial(self,name,position=(0,0,0),associatedNode=None):
    """Add an instance of a fiducial to the scene for a given
    volume node.  Creates a new list if needed.
    If list already has a fiducial with the given name, then
    set the position to the passed value.
    """

    markupsLogic = slicer.modules.markups.logic()
    originalActiveListID = markupsLogic.GetActiveListID() # TODO: naming convention?
    slicer.mrmlScene.StartState(slicer.mrmlScene.BatchProcessState)

    # make the fiducial list if required
    listName = associatedNode.GetName() + "-landmarks"
    fiducialList = slicer.mrmlScene.GetFirstNodeByName(listName)
    if not fiducialList:
      fiducialListNodeID = markupsLogic.AddNewFiducialNode(listName,slicer.mrmlScene)
      fiducialList = slicer.mrmlScene.GetNodeByID(fiducialListNodeID)
      if associatedNode:
        fiducialList.SetAttribute("AssociatedNodeID", associatedNode.GetID())
      self.setFiducialListDisplay(fiducialList)

    # make this active so that the fids will be added to it
    markupsLogic.SetActiveListID(fiducialList)

    foundLandmarkFiducial = False
    fiducialSize = fiducialList.GetNumberOfFiducials()
    for fiducialIndex in range(fiducialSize):
      if fiducialList.GetNthFiducialLabel(fiducialIndex) == name:
        fiducialList.SetNthFiducialPosition(fiducialIndex, *position)
        foundLandmarkFiducial = True
        break

    if not foundLandmarkFiducial:
      if associatedNode:
        # clip point to min/max bounds of target volume
        rasBounds = [0,]*6
        associatedNode.GetRASBounds(rasBounds)
        for i in range(3):
          if position[i] < rasBounds[2*i]:
            position[i] = rasBounds[2*i]
          if position[i] > rasBounds[2*i+1]:
            position[i] = rasBounds[2*i+1]
      fiducialList.AddFiducial(*position)
      fiducialIndex = fiducialList.GetNumberOfFiducials()-1

    fiducialList.SetNthFiducialLabel(fiducialIndex, name)
    fiducialList.SetNthFiducialSelected(fiducialIndex, False)
    fiducialList.SetNthMarkupLocked(fiducialIndex, False)

    originalActiveList = slicer.mrmlScene.GetNodeByID(originalActiveListID)
    if originalActiveList:
      markupsLogic.SetActiveListID(originalActiveList)
    slicer.mrmlScene.EndState(slicer.mrmlScene.BatchProcessState)

  def addLandmark(self,volumeNodes=[], position=(0,0,0), movingPosition=(0,0,0)):
    """Add a new landmark by adding correspondingly named
    fiducials to all the current volume nodes.
    Find a unique name for the landmark and place it at the origin.
    As a special case if the fiducial list corresponds to the
    moving volume in the current state, then assign the movingPosition
    (this way it can account for the current transform).
    """
    state = self.registrationState()
    landmarks = self.landmarksForVolumes(volumeNodes)
    index = 0
    while True:
      landmarkName = 'L-%d' % index
      if not landmarkName in landmarks.keys():
        break
      index += 1
    for volumeNode in volumeNodes:
      # if the volume is the moving on, map position through transform to world
      if volumeNode == state.moving:
        positionToAdd = movingPosition
      else:
        positionToAdd = position
      fiducial = self.addFiducial(landmarkName, position=positionToAdd, associatedNode=volumeNode)
    return landmarkName

  def removeLandmarkForVolumes(self,landmark,volumeNodes):
    """Remove the fiducial nodes from all the volumes.
    """
    slicer.mrmlScene.StartState(slicer.mrmlScene.BatchProcessState)
    landmarks = self.landmarksForVolumes(volumeNodes)
    if landmark in landmarks:
      for fiducialList,fiducialIndex in landmarks[landmark]:
        fiducialList.RemoveMarkup(fiducialIndex)
    slicer.mrmlScene.EndState(slicer.mrmlScene.BatchProcessState)

  def volumeFiducialList(self,volumeNode):
    """return fiducial list node that is
    list associated with the given volume node"""
    if not volumeNode:
      return None
    listName = volumeNode.GetName() + "-landmarks"
    listNode = slicer.mrmlScene.GetFirstNodeByName(listName)
    if listNode:
      if listNode.GetAttribute("AssociatedNodeID") != volumeNode.GetID():
        self.setFiducialListDisplay(listNode)
        listNode.SetAttribute("AssociatedNodeID",volumeNode.GetID())
    return listNode

  def landmarksForVolumes(self,volumeNodes):
    """Return a dictionary of keyed by
    landmark name containing pairs (fiducialListNodes,index)
    Only fiducials that exist for all volumes are returned."""
    landmarksByName = {}
    for volumeNode in volumeNodes:
      listForVolume = self.volumeFiducialList(volumeNode)
      if listForVolume:
        fiducialSize = listForVolume.GetNumberOfMarkups()
        for fiducialIndex in range(fiducialSize):
          fiducialName = listForVolume.GetNthFiducialLabel(fiducialIndex)
          if fiducialName in landmarksByName:
            landmarksByName[fiducialName].append((listForVolume,fiducialIndex))
          else:
            landmarksByName[fiducialName] = [(listForVolume,fiducialIndex),]
    for fiducialName in list(landmarksByName.keys()):
      if len(landmarksByName[fiducialName]) != len(volumeNodes):
        landmarksByName.__delitem__(fiducialName)
    return landmarksByName

  def ensureFiducialInListForVolume(self,volumeNode,landmarkName,landmarkPosition):
    """Make sure the fiducial list associated with the given
    volume node contains a fiducial named landmarkName and that it
    is associated with volumeNode.  If it does not have one, add one
    and put it at landmarkPosition.
    Returns landmarkName if a new one is created, otherwise none
    """
    fiducialList = self.volumeFiducialList(volumeNode)
    if not fiducialList:
      return None
    fiducialSize = fiducialList.GetNumberOfMarkups()
    for fiducialIndex in range(fiducialSize):
      if fiducialList.GetNthFiducialLabel(fiducialIndex) == landmarkName:
        fiducialList.SetNthMarkupAssociatedNodeID(fiducialIndex, volumeNode.GetID())
        return None
    # if we got here, then there is no fiducial with this name so add one
    fiducialList.AddFiducial(*landmarkPosition)
    fiducialIndex = fiducialList.GetNumberOfFiducials()-1
    fiducialList.SetNthFiducialLabel(fiducialIndex, landmarkName)
    fiducialList.SetNthFiducialSelected(fiducialIndex, False)
    fiducialList.SetNthMarkupLocked(fiducialIndex, False)
    return landmarkName

  def collectAssociatedFiducials(self,volumeNodes):
    """Look at each fiducial list in scene and find any fiducials associated
    with one of our volumes but not in in one of our lists.
    Add the fiducial as a landmark and delete it from the other list.
    Return the name of the last added landmark if it exists.
    """
    state = self.registrationState()
    addedLandmark = None
    volumeNodeIDs = []
    for volumeNode in volumeNodes:
      volumeNodeIDs.append(volumeNode.GetID())
    landmarksByName = self.landmarksForVolumes(volumeNodes)
    fiducialListsInScene = slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode')
    landmarkFiducialLists = []
    for landmarkName in landmarksByName.keys():
      for fiducialList,index in landmarksByName[landmarkName]:
        if fiducialList not in landmarkFiducialLists:
          landmarkFiducialLists.append(fiducialList)
    listIndexToRemove = [] # remove back to front after identifying them
    for fiducialList in fiducialListsInScene:
      if fiducialList not in landmarkFiducialLists:
        # this is not one of our fiducial lists, so look for fiducials
        # associated with one of our volumes
        fiducialSize = fiducialList.GetNumberOfMarkups()
        for fiducialIndex in range(fiducialSize):
          associatedID = fiducialList.GetNthMarkupAssociatedNodeID(fiducialIndex)
          if associatedID in volumeNodeIDs:
            # found one, so add it as a landmark
            landmarkPosition = fiducialList.GetMarkupPointVector(fiducialIndex,0)
            volumeNode = slicer.mrmlScene.GetNodeByID(associatedID)
            # if new fiducial is associated with moving volume,
            # then map the position back to where it would have been
            # if it were not transformed, if not, then calculate where
            # the point would be on the moving volume
            movingPosition = [0.,]*3
            volumeTransformNode = state.transformed.GetParentTransformNode()
            volumeTransform = vtk.vtkGeneralTransform()
            if volumeTransformNode:
              if volumeNode == state.moving:
                # in this case, moving stays and other point moves
                volumeTransformNode.GetTransformToWorld(volumeTransform)
                movingPosition[:] = landmarkPosition
                volumeTransform.TransformPoint(movingPosition,landmarkPosition)
              else:
                # in this case, landmark stays and moving point moves
                volumeTransformNode.GetTransformFromWorld(volumeTransform)
                volumeTransform.TransformPoint(landmarkPosition,movingPosition)
            addedLandmark = self.addLandmark(volumeNodes,landmarkPosition,movingPosition)
            listIndexToRemove.insert(0,(fiducialList,fiducialIndex))
    for fiducialList,fiducialIndex in listIndexToRemove:
      fiducialList.RemoveMarkup(fiducialIndex)
    return addedLandmark

  def landmarksFromFiducials(self,volumeNodes):
    """Look through all fiducials in the scene and make sure they
    are in a fiducial list that is associated with the same
    volume node.  If they are in the wrong list fix the node id, and make a new
    duplicate fiducial in the correct list.
    This can be used when responding to new fiducials added to the scene.
    Returns the most recently added landmark (or None).
    """
    slicer.mrmlScene.StartState(slicer.mrmlScene.BatchProcessState)
    addedLandmark = None
    for volumeNode in volumeNodes:
      fiducialList = self.volumeFiducialList(volumeNode)
      if not fiducialList:
        print("no fiducialList for volume %s" % volumeNode.GetName())
        continue
      fiducialSize = fiducialList.GetNumberOfMarkups()
      for fiducialIndex in range(fiducialSize):
        fiducialAssociatedVolumeID = fiducialList.GetNthMarkupAssociatedNodeID(fiducialIndex)
        landmarkName = fiducialList.GetNthFiducialLabel(fiducialIndex)
        landmarkPosition = fiducialList.GetMarkupPointVector(fiducialIndex,0)
        if fiducialAssociatedVolumeID != volumeNode.GetID():
          # fiducial was placed on a viewer associated with the non-active list, so change it
          fiducialList.SetNthMarkupAssociatedNodeID(fiducialIndex,volumeNode.GetID())
        # now make sure all other lists have a corresponding fiducial (same name)
        for otherVolumeNode in volumeNodes:
          if otherVolumeNode != volumeNode:
            addedFiducial = self.ensureFiducialInListForVolume(otherVolumeNode,landmarkName,landmarkPosition)
            if addedFiducial:
              addedLandmark = addedFiducial
    slicer.mrmlScene.EndState(slicer.mrmlScene.BatchProcessState)
    return addedLandmark

  def vtkPointsForVolumes(self, volumeNodes, fiducialNodes):
    """Return dictionary of vtkPoints instances containing the fiducial points
    associated with current landmarks, indexed by volume"""
    points = {}
    for volumeNode in volumeNodes:
      points[volumeNode] = vtk.vtkPoints()
    sameNumberOfNodes = len(volumeNodes) == len(fiducialNodes)
    noNoneNodes = None not in volumeNodes and None not in fiducialNodes
    if sameNumberOfNodes and noNoneNodes:
      fiducialCount = fiducialNodes[0].GetNumberOfFiducials()
      for fiducialNode in fiducialNodes:
        if fiducialCount != fiducialNode.GetNumberOfFiducials():
          raise Exception("Fiducial counts don't match {0}".format(fiducialCount))
      point = [0,]*3
      indices = range(fiducialCount)
      for fiducials,volumeNode in zip(fiducialNodes,volumeNodes):
        for index in indices:
          fiducials.GetNthFiducialPosition(index,point)
          points[volumeNode].InsertNextPoint(point)
    return points




class LandmarkRegistrationTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  """

  def moveMouse(self,widget,start=(10,10),end=(10,40),steps=20,modifiers=[]):
    """Send synthetic mouse events to the specified widget (qMRMLSliceWidget or qMRMLThreeDView)
    start, end : window coordinates for action
    steps : number of steps to move in
    modifiers : list containing zero or more of "Shift" or "Control"
    """
    style = widget.interactorStyle()
    interator = style.GetInteractor()
    if 'Shift' in modifiers:
      interator.SetShiftKey(1)
    if 'Control' in modifiers:
      interator.SetControlKey(1)
    interator.SetEventPosition(*start)
    for step in range(steps):
      frac = float(step+1)/steps
      x = int(start[0] + frac*(end[0]-start[0]))
      y = int(start[1] + frac*(end[1]-start[1]))
      interator.SetEventPosition(x,y)
      style.OnMouseMove()
    interator.SetShiftKey(0)
    interator.SetControlKey(0)

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)

  def runTest(self,scenario=None):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    if scenario == "Basic":
      self.test_LandmarkRegistrationBasic()
    elif scenario == "Affine":
      self.test_LandmarkRegistrationAffine()
    elif scenario == "ThinPlate":
      self.test_LandmarkRegistrationThinPlate()
    elif scenario == "VTKv6Picking":
      self.test_LandmarkRegistrationVTKv6Picking()
    elif scenario == "ManyLandmarks":
      self.test_LandmarkRegistrationManyLandmarks()
    else:
      self.test_LandmarkRegistrationBasic()
      self.test_LandmarkRegistrationAffine()
      self.test_LandmarkRegistrationThinPlate()
      self.test_LandmarkRegistrationVTKv6Picking()
      self.test_LandmarkRegistrationManyLandmarks()

  def test_LandmarkRegistrationBasic(self):
    """
    This tests basic landmarking with two volumes
    """

    self.delayDisplay("Starting test_LandmarkRegistrationBasic")
    #
    # first, get some data
    #
    from SampleData import SampleDataLogic
    mrHead = SampleDataLogic().downloadMRHead()
    dtiBrain = SampleDataLogic().downloadDTIBrain()
    self.delayDisplay('Two data sets loaded')

    mainWindow = slicer.util.mainWindow()
    mainWindow.moduleSelector().selectModule('LandmarkRegistration')

    w = slicer.modules.LandmarkRegistrationWidget
    w.volumeSelectors["Fixed"].setCurrentNode(dtiBrain)
    w.volumeSelectors["Moving"].setCurrentNode(mrHead)

    logic = LandmarkRegistrationLogic()

    for name,point in (
      ('middle-of-right-eye', [35.115070343017578, 74.803565979003906, -21.032917022705078]),
      ('tip-of-nose', [0.50825262069702148, 128.85432434082031, -48.434154510498047]),
      ('right-ear', [80.0, -26.329217910766602, -15.292181015014648]),
      ):
      logic.addFiducial(name, position=point,associatedNode=mrHead)

    for name,point in (
      ('middle-of-right-eye', [28.432207107543945, 71.112533569335938, -41.938472747802734]),
      ('tip-of-nose', [0.9863210916519165, 94.6998291015625, -49.877540588378906]),
      ('right-ear', [79.28509521484375, -12.95069694519043, 5.3944296836853027]),
      ):
      logic.addFiducial(name, position=point,associatedNode=dtiBrain)

    w.onVolumeNodeSelect()
    w.onLayout()
    w.onLandmarkPicked('tip-of-nose')

    self.delayDisplay('test_LandmarkRegistrationBasic passed!')

  def test_LandmarkRegistrationAffine(self):
    """
    This tests basic linear registration with two
    volumes (pre- post-surgery)
    """

    self.delayDisplay("Starting test_LandmarkRegistrationAffine")
    #
    # first, get some data
    #
    from SampleData import SampleDataLogic
    pre,post = SampleDataLogic().downloadDentalSurgery()
    self.delayDisplay('Two data sets loaded')

    mainWindow = slicer.util.mainWindow()
    mainWindow.moduleSelector().selectModule('LandmarkRegistration')

    w = slicer.modules.LandmarkRegistrationWidget
    w.setupDialog()
    w.volumeDialogSelectors["Fixed"].setCurrentNode(post)
    w.volumeDialogSelectors["Moving"].setCurrentNode(pre)
    w.onVolumeDialogApply()

    # initiate linear registration
    w.registrationTypeButtons["Affine"].checked = True
    w.registrationTypeButtons["Affine"].clicked()

    w.onLayout(layoutMode="Axi/Sag/Cor")

    self.delayDisplay('test_LandmarkRegistrationAffine passed!')

  def test_LandmarkRegistrationThinPlate(self):
    """Test the thin plate spline transform"""
    self.test_LandmarkRegistrationAffine()

    self.delayDisplay('starting test_LandmarkRegistrationThinPlate')

    mainWindow = slicer.util.mainWindow()
    mainWindow.moduleSelector().selectModule('LandmarkRegistration')

    w = slicer.modules.LandmarkRegistrationWidget
    pre = w.volumeSelectors["Fixed"].currentNode()
    post = w.volumeSelectors["Moving"].currentNode()

    for name,point in (
      ('L-0', [-91.81303405761719, -36.81013488769531, 76.78043365478516]),
      ('L-1', [-91.81303405761719, -41.065155029296875, 19.57413101196289]),
      ('L-2', [-89.75, -121.12535858154297, 33.5537223815918]),
      ('L-3', [-91.29727935791016, -148.6207275390625, 54.980953216552734]),
      ('L-4', [-89.75, -40.17485046386719, 153.87451171875]),
      ('L-5', [-144.15321350097656, -128.45083618164062, 69.85309600830078]),
      ('L-6', [-40.16628646850586, -128.70603942871094, 71.85968017578125]),):
        w.logic.addFiducial(name, position=point,associatedNode=post)

    for name,point in (
      ('L-0', [-89.75, -48.97413635253906, 70.87068939208984]),
      ('L-1', [-91.81303405761719, -47.7024040222168, 14.120864868164062]),
      ('L-2', [-89.75, -130.1315155029297, 31.712587356567383]),
      ('L-3', [-90.78448486328125, -160.6336212158203, 52.85344696044922]),
      ('L-4', [-85.08663940429688, -47.26158905029297, 143.84193420410156]),
      ('L-5', [-144.1186065673828, -138.91270446777344, 68.24700927734375]),
      ('L-6', [-40.27879333496094, -141.29898071289062, 67.36009216308594]),):
        w.logic.addFiducial(name, position=point,associatedNode=pre)


    # initiate linear registration
    w.registrationTypeButtons["ThinPlate"].checked = True
    w.registrationTypeButtons["ThinPlate"].clicked()

    w.landmarksWidget.pickLandmark('L-4')
    w.onRegistrationType("ThinPlate")

    self.delayDisplay('Applying transform')
    w.currentRegistrationInterface.onThinPlateApply()

    self.delayDisplay('Exporting as a grid node')
    w.currentRegistrationInterface.onExportGrid()

    self.delayDisplay('test_LandmarkRegistrationThinPlate passed!')


  def test_LandmarkRegistrationVTKv6Picking(self):
    """Test the picking situation on VTKv6"""

    self.delayDisplay('starting test_LandmarkRegistrationVTKv6Picking')

    mainWindow = slicer.util.mainWindow()
    mainWindow.moduleSelector().selectModule('LandmarkRegistration')


    #
    # first, get some data
    #
    from SampleData import SampleDataSource, SampleDataLogic

    dataSource = SampleDataSource(sampleName='fixed', uris='http://slicer.kitware.com/midas3/download/item/157188/small-mr-eye-fixed.nrrd', fileNames='fixed.nrrd', nodeNames='fixed')
    fixed = SampleDataLogic().downloadFromSource(dataSource)[0]

    dataSource = SampleDataSource(sampleName='moving', uris='http://slicer.kitware.com/midas3/download/item/157189/small-mr-eye-moving.nrrd', fileNames='moving.nrrd', nodeNames='moving')
    moving = SampleDataLogic().downloadFromSource(dataSource)[0]

    self.delayDisplay('Two data sets loaded')

    w = slicer.modules.LandmarkRegistrationWidget
    w.setupDialog()
    w.volumeDialogSelectors["Fixed"].setCurrentNode(fixed)
    w.volumeDialogSelectors["Moving"].setCurrentNode(moving)
    w.onVolumeDialogApply()

    # to help debug picking manager, set some variables that
    # can be accessed via the python console.
    self.delayDisplay('setting widget variables')
    w.lm = slicer.app.layoutManager()
    w.fa = w.lm.sliceWidget('fixed-Axial')
    w.fav = w.fa.sliceView()
    w.favrw = w.fav.renderWindow()
    w.favi = w.fav.interactor()
    w.favpm = w.favi.GetPickingManager()
    w.rens = w.favrw.GetRenderers()
    w.ren = w.rens.GetItemAsObject(0)
    w.cam = w.ren.GetActiveCamera()
    print(w.favpm)

    logic = LandmarkRegistrationLogic()

    # initiate registration
    w.registrationTypeButtons["ThinPlate"].checked = True
    w.registrationTypeButtons["ThinPlate"].clicked()

    # enter picking mode
    w.landmarksWidget.addLandmark()

    # move the mouse to the middle of the widget so that the first
    # mouse move event will be exactly over the fiducial to simplify
    # breakpoints in mouse move callbacks.
    layoutManager = slicer.app.layoutManager()
    fixedAxialView = layoutManager.sliceWidget('fixed-Axial').sliceView()
    center = (int(fixedAxialView.width/2), int(fixedAxialView.height/2))
    offset = [element+100 for element in center]
    logic.clickAndDrag(fixedAxialView,start=center,end=center, steps=0)
    self.delayDisplay('Added a landmark, translate to drag at %s to %s' % (center,offset), 200)

    logic.clickAndDrag(fixedAxialView,button='Middle', start=center,end=offset,steps=10)
    self.delayDisplay('dragged to translate', 200)
    logic.clickAndDrag(fixedAxialView,button='Middle', start=offset,end=center,steps=10)
    self.delayDisplay('translate back', 200)


    globalPoint = fixedAxialView.mapToGlobal(qt.QPoint(*center))
    qt.QCursor().setPos(globalPoint)
    self.delayDisplay('moved to %s' % globalPoint, 200 )

    offset = [element+10 for element in center]
    globalPoint = fixedAxialView.mapToGlobal(qt.QPoint(*offset))
    if False:
      # move the cursor
      qt.QCursor().setPos(globalPoint)
    else:
      # generate the event
      try:
        # Qt5 expects localPos as QPointF
        mouseEvent = qt.QMouseEvent(qt.QEvent.MouseMove,qt.QPointF(globalPoint),0,0,0)
      except ValueError:
        # Qt4 expects localPos as QPoint
        mouseEvent = qt.QMouseEvent(qt.QEvent.MouseMove,globalPoint,0,0,0)
      fixedAxialView.VTKWidget().mouseMoveEvent(mouseEvent)

    self.delayDisplay('moved to %s' % globalPoint, 200 )

    self.delayDisplay('test_LandmarkRegistrationVTKv6Picking passed!')

  def test_LandmarkRegistrationManyLandmarks(self):
    """
    This tests basic landmarking with two volumes
    """

    self.delayDisplay("Starting test_LandmarkRegistrationManyLandmarks")
    #
    # first, get some data
    #
    from SampleData import SampleDataLogic
    mrHead = SampleDataLogic().downloadMRHead()
    dtiBrain = SampleDataLogic().downloadDTIBrain()
    self.delayDisplay('Two data sets loaded')

    mainWindow = slicer.util.mainWindow()
    mainWindow.moduleSelector().selectModule('LandmarkRegistration')

    w = slicer.modules.LandmarkRegistrationWidget
    w.setupDialog()
    w.volumeDialogSelectors["Fixed"].setCurrentNode(dtiBrain)
    w.volumeDialogSelectors["Moving"].setCurrentNode(mrHead)
    w.onVolumeDialogApply()

    self.delayDisplay('Volumes set up',100)

    logic = LandmarkRegistrationLogic()


    # move the mouse to the middle of the widget so that the first
    # mouse move event will be exactly over the fiducial to simplify
    # breakpoints in mouse move callbacks.
    layoutManager = slicer.app.layoutManager()
    fixedAxialView = layoutManager.sliceWidget('MRHead-Axial').sliceView()
    center = (int(fixedAxialView.width/2), int(fixedAxialView.height/2))
    offset = [element+5 for element in center]
    # enter picking mode
    w.landmarksWidget.addLandmark()
    logic.clickAndDrag(fixedAxialView,start=center,end=offset, steps=10)
    self.delayDisplay('Added a landmark, translate to drag at %s to %s' % (center,offset), 200)

    import time, math
    times = []
    startTime = time.time()
    for row in range(5):
      for column in range(5):
        pointTime = time.time()
        flip = int(math.pow(-1, row))
        clickPoint = (int(fixedAxialView.width/2)+5*row*flip, int(fixedAxialView.height/2)+5*column*flip)
        offset = [element+5 for element in clickPoint]
        # enter picking mode
        w.landmarksWidget.addLandmark()
        logic.clickAndDrag(fixedAxialView,start=clickPoint,end=offset, steps=10)
        pointElapsed = str(time.time() - pointTime)
        self.delayDisplay('Clicked at ' + str(clickPoint) + ' ' + pointElapsed)
        times.append((pointElapsed, clickPoint))
    self.delayDisplay('Total time ' + str(time.time() - startTime))
    self.delayDisplay(str(times))


    self.delayDisplay('test_LandmarkRegistrationManyLandmarks passed!')
