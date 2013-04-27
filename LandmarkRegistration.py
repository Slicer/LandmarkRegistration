import os
import unittest
from __main__ import vtk, qt, ctk, slicer

#
# LandmarkRegistration
#

class LandmarkRegistration:
  def __init__(self, parent):
    parent.title = "Landmark Registration"
    parent.categories = ["Registration"]
    parent.dependencies = []
    parent.contributors = ["Steve Pieper (Isomics)"] # replace with "Firstname Lastname (Org)"
    parent.helpText = """
    This module organizes a fixed and moving volume along with a set of corresponding
    landmarks (paired fiducials) to assist in manual registration.
    """
    parent.acknowledgementText = """
    This file was developed by Steve Pieper, Isomics, Inc.
    It was partially funded by NIH grant 3P41RR013218-12S1
    and this work is part of the National Alliance for Medical Image
    Computing (NAMIC), funded by the National Institutes of Health
    through the NIH Roadmap for Medical Research, Grant U54 EB005149.
    Information on the National Centers for Biomedical Computing
    can be obtained from http://nihroadmap.nih.gov/bioinformatics.
    """ # replace with organization, grant and thanks.
    self.parent = parent

    # Add this test to the SelfTest module's list for discovery when the module
    # is created.  Since this module may be discovered before SelfTests itself,
    # create the list if it doesn't already exist.
    try:
      slicer.selfTests
    except AttributeError:
      slicer.selfTests = {}
    slicer.selfTests['LandmarkRegistration'] = self.runTest

  def runTest(self):
    tester = LandmarkRegistrationTest()
    tester.runTest()

#
# qLandmarkRegistrationWidget
#

class LandmarkRegistrationWidget:
  """The module GUI widget"""
  def __init__(self, parent = None):
    self.logic = LandmarkRegistrationLogic()
    self.sliceNodesByViewName = {}
    self.sliceNodesByVolumeID = {}

    if not parent:
      self.parent = slicer.qMRMLWidget()
      self.parent.setLayout(qt.QVBoxLayout())
      self.parent.setMRMLScene(slicer.mrmlScene)
    else:
      self.parent = parent
    self.layout = self.parent.layout()
    if not parent:
      self.setup()
      self.parent.show()

  def setup(self):
    # Instantiate and connect widgets ...

    #
    # Reload and Test area
    #
    reloadCollapsibleButton = ctk.ctkCollapsibleButton()
    reloadCollapsibleButton.text = "Reload && Test"
    self.layout.addWidget(reloadCollapsibleButton)
    reloadFormLayout = qt.QFormLayout(reloadCollapsibleButton)

    # reload button
    # (use this during development, but remove it when delivering
    #  your module to users)
    self.reloadButton = qt.QPushButton("Reload")
    self.reloadButton.toolTip = "Reload this module."
    self.reloadButton.name = "LandmarkRegistration Reload"
    reloadFormLayout.addWidget(self.reloadButton)
    self.reloadButton.connect('clicked()', self.onReload)

    # reload and test button
    # (use this during development, but remove it when delivering
    #  your module to users)
    self.reloadAndTestButton = qt.QPushButton("Reload and Test")
    self.reloadAndTestButton.toolTip = "Reload this module and then run the self tests."
    reloadFormLayout.addWidget(self.reloadAndTestButton)
    self.reloadAndTestButton.connect('clicked()', self.onReloadAndTest)

    #
    # Parameters Area
    #
    parametersCollapsibleButton = ctk.ctkCollapsibleButton()
    parametersCollapsibleButton.text = "Parameters"
    self.layout.addWidget(parametersCollapsibleButton)
    parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)

    self.volumeSelectors = {}
    self.viewNames = ("Moving", "Fixed", "Transformed")
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
      parametersFormLayout.addRow("%s Volume: " % viewName, self.volumeSelectors[viewName])

    self.volumeSelectors["Transformed"].addEnabled = True
    self.volumeSelectors["Transformed"].selectNodeUponCreation = True
    self.volumeSelectors["Transformed"].setToolTip( "Pick the transformed volume, which is the target for the registration." )

    #
    # layout options
    #
    layout = qt.QHBoxLayout()
    self.layoutComboBox = qt.QComboBox()
    if True:
      # combo box version
      self.layoutComboBox.addItem('Axial')
      self.layoutComboBox.addItem('Sagittal')
      self.layoutComboBox.addItem('Coronal')
      self.layoutComboBox.addItem('Axi/Sag/Cor')
      #self.layoutComboBox.addItem('Ax/Sag/Cor/3D')
      layout.addWidget(self.layoutComboBox)
      self.layoutButton = qt.QPushButton('Layout')
      self.layoutButton.connect('clicked()', self.onLayout)
      layout.addWidget(self.layoutButton)
    else:
      modes = ( ('Ax', 'Axial'), ('Sg', 'Sagittal'), ('Cr', 'Coronal'),)
      for label,mode in modes:
        button = qt.QPushButton(label)
        button.connect('clicked()',lambda m=mode: self.onLayout(mode))
        layout.addWidget(button)
    parametersFormLayout.addRow("Orientation: ", layout)

    #
    # Landmark Widget
    # - manages landmarks
    #
    self.landmarks = Landmarks(self.logic)
    self.landmarks.connect("LandmarkPicked(landmarkName)", self.onLandmarkPicked)
    parametersFormLayout.addRow(self.landmarks.widget)

    #
    # registration type selection
    # - allows selection of the active registration type to display
    #
    self.registrationTypeBox = qt.QGroupBox("Registration Type")
    self.registrationTypeBox.setLayout(qt.QFormLayout())
    self.registrationTypeButtons = {}
    self.registrationTypes = ("Linear", "Hybrid B-Spline")
    for registrationType in self.registrationTypes:
      self.registrationTypeButtons[registrationType] = qt.QRadioButton()
      self.registrationTypeButtons[registrationType].text = registrationType
      self.registrationTypeButtons[registrationType].setToolTip("Pick the type of registration")
      self.registrationTypeButtons[registrationType].connect("clicked()",
                                      lambda t=registrationType: self.onRegistrationType(t))
      self.registrationTypeBox.layout().addWidget(self.registrationTypeButtons[registrationType])
    self.layout.addWidget(self.registrationTypeBox)

    #
    # Linear Registration Pane - initially hidden
    # - interface options for linear registration
    # - TODO: move registration code into separate plugins
    #
    self.linearCollapsibleButton = ctk.ctkCollapsibleButton()
    self.linearCollapsibleButton.text = "Linear Registration"
    linearFormLayout = qt.QFormLayout()
    self.linearCollapsibleButton.setLayout(linearFormLayout)
    self.layout.addWidget(self.linearCollapsibleButton)

    self.linearRegistrationActive = qt.QCheckBox()
    self.linearRegistrationActive.checked = False
    self.linearRegistrationActive.connect("toggled(bool)", self.onLinearActive)
    linearFormLayout.addRow("Registration Active: ", self.linearRegistrationActive)

    buttonLayout = qt.QVBoxLayout()
    self.linearModeButtons = {}
    self.linearModes = ("Rigid", "Similarity", "Affine")
    for mode in self.linearModes:
      self.linearModeButtons[mode] = qt.QRadioButton()
      self.linearModeButtons[mode].text = mode
      self.linearModeButtons[mode].setToolTip( "Run the registration in %s mode." % mode )
      buttonLayout.addWidget(self.linearModeButtons[mode])
      self.linearModeButtons[mode].connect('clicked(bool)', self.onLinearTransform)
    self.linearModeButtons["Affine"].checked = True
    linearFormLayout.addRow("Registration Mode: ", buttonLayout)

    self.linearTransformSelector = slicer.qMRMLNodeComboBox()
    self.linearTransformSelector.nodeTypes = ( ("vtkMRMLLinearTransformNode"), "" )
    self.linearTransformSelector.selectNodeUponCreation = True
    self.linearTransformSelector.addEnabled = True
    self.linearTransformSelector.removeEnabled = True
    self.linearTransformSelector.noneEnabled = True
    self.linearTransformSelector.showHidden = False
    self.linearTransformSelector.showChildNodeTypes = False
    self.linearTransformSelector.setMRMLScene( slicer.mrmlScene )
    self.linearTransformSelector.setToolTip( "Pick the transform for linear registration" )
    linearFormLayout.addRow("Target Linear Transform: ", self.linearTransformSelector)

    #
    # Hybrid B-Spline Registration Pane - initially hidden
    #
    self.hybridCollapsibleButton = ctk.ctkCollapsibleButton()
    self.hybridCollapsibleButton.text = "Hybrid B-Spline Registration"
    hybridFormLayout = qt.QFormLayout()
    self.hybridCollapsibleButton.setLayout(hybridFormLayout)
    self.layout.addWidget(self.hybridCollapsibleButton)

    self.hybridTransformSelector = slicer.qMRMLNodeComboBox()
    self.hybridTransformSelector.nodeTypes = ( ("vtkMRMLBSplineTransformNode"), "" )
    self.hybridTransformSelector.selectNodeUponCreation = True
    self.hybridTransformSelector.addEnabled = True
    self.hybridTransformSelector.removeEnabled = True
    self.hybridTransformSelector.noneEnabled = True
    self.hybridTransformSelector.showHidden = False
    self.hybridTransformSelector.showChildNodeTypes = False
    self.hybridTransformSelector.setMRMLScene( slicer.mrmlScene )
    self.hybridTransformSelector.setToolTip( "Pick the transform for Hybrid B-Spline registration" )
    hybridFormLayout.addRow("Target B-Spline Transform: ", self.hybridTransformSelector)

    self.registrationTypeInterfaces = {}
    self.registrationTypeInterfaces['Linear'] = self.linearCollapsibleButton
    self.registrationTypeInterfaces['Hybrid B-Spline'] = self.hybridCollapsibleButton

    for registrationType in self.registrationTypes:
      self.registrationTypeInterfaces[registrationType].enabled = False
      self.registrationTypeInterfaces[registrationType].hide()


    #
    # Apply Button
    #
    self.applyButton = qt.QPushButton("Run Registration")
    self.applyButton.toolTip = "Run the registration algorithm."
    self.applyButton.enabled = False
    parametersFormLayout.addRow(self.applyButton)

    # connections
    self.applyButton.connect('clicked(bool)', self.onApplyButton)
    for selector in self.volumeSelectors.values():
      selector.connect("currentNodeChanged(vtkMRMLNode*)", self.onVolumeNodeSelect)

    # Add vertical spacer
    self.layout.addStretch(1)

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
    self.landmarks.setVolumeNodes(volumeNodes)
    fixed = self.volumeSelectors['Fixed'].currentNode()
    moving = self.volumeSelectors['Moving'].currentNode()
    for registrationType in self.registrationTypes:
      self.registrationTypeInterfaces[registrationType].enabled = bool(fixed and moving)

  def onLayout(self, layoutMode=None):
    volumeNodes = []
    activeViewNames = []
    for viewName in self.viewNames:
      volumeNode = self.volumeSelectors[viewName].currentNode()
      if volumeNode:
        volumeNodes.append(volumeNode)
        activeViewNames.append(viewName)
    if not layoutMode:
      layoutMode = self.layoutComboBox.currentText
    import CompareVolumes
    compareLogic = CompareVolumes.CompareVolumesLogic()
    oneViewModes = ('Axial', 'Sagittal', 'Coronal',)
    if layoutMode in oneViewModes:
      self.sliceNodesByViewName = compareLogic.viewerPerVolume(volumeNodes,viewNames=activeViewNames,orientation=layoutMode)
    elif layoutMode == 'Axi/Sag/Cor':
      self.sliceNodesByViewName = compareLogic.viewersPerVolume(volumeNodes)
    self.updateSliceNodesByVolumeID()
    self.onLandmarkPicked(self.landmarks.selectedLandmark)

  def onRegistrationType(self,pickedRegistrationType):
    """Pick which registration type to display"""
    for registrationType in self.registrationTypes:
      self.registrationTypeInterfaces[registrationType].hide()
    self.registrationTypeInterfaces[pickedRegistrationType].show()

  def onLinearActive(self,active):
    """Turn on linear mode if possible"""
    if not self.linearRegistrationActive.checked:
      self.logic.disableLinearRegistration()
    else:
      # ensure we have fixed and moving
      fixed = self.volumeSelectors['Fixed'].currentNode()
      moving = self.volumeSelectors['Moving'].currentNode()
      if not (fixed and moving):
        self.linearRegistrationActive.checked = False
      else:
        # create transform and transformed if needed
        transform = self.linearTransformSelector.currentNode()
        if not transform:
          self.linearTransformSelector.addNode()
          transform = self.linearTransformSelector.currentNode()
        transformed = self.volumeSelectors['Transformed'].currentNode()
        if not transformed:
          volumesLogic = slicer.modules.volumes.logic()
          transformedName = "%s-transformed" % moving.GetName()
          transformed = volumesLogic.CloneVolume(slicer.mrmlScene, moving, transformedName)
          self.volumeSelectors['Transformed'].setCurrentNode(transformed)
        landmarks = self.logic.landmarksForVolumes((fixed,moving))
        self.logic.enableLinearRegistration(fixed,moving,landmarks,transform,transformed)

  def onLinearTransform(self):
    """Call this whenever linear transform needs to be updated"""
    for mode in self.linearModes:
      if self.linearModeButtons[mode].checked:
        self.logic.linearMode = mode
        break

  def onHybridTransform(self):
    """Call this whenever linear transform needs to be updated"""
    pass

  def updateSliceNodesByVolumeID(self):
    """Build a mapping to a list of slice nodes
    node that are currently displaying a given volumeID"""
    compositeNodes = slicer.util.getNodes('vtkMRMLSliceCompositeNode*')
    self.sliceNodesByVolumeID = {}
    if self.sliceNodesByViewName:
      for sliceNode in self.sliceNodesByViewName.values():
        for compositeNode in compositeNodes.values():
          if compositeNode.GetLayoutName() == sliceNode.GetLayoutName():
            volumeID = compositeNode.GetBackgroundVolumeID()
            if self.sliceNodesByVolumeID.has_key(volumeID):
              self.sliceNodesByVolumeID[volumeID].append(sliceNode)
            else:
              self.sliceNodesByVolumeID[volumeID] = [sliceNode,]

  def restrictLandmarksToViews(self):
    """Set fiducials so they only show up in the view
    for the volume on which they were defined"""
    volumeNodes = self.currentVolumeNodes()
    if self.sliceNodesByViewName:
      landmarks = self.logic.landmarksForVolumes(volumeNodes)
      for fidList in landmarks.values():
        for fid in fidList:
          displayNode = fid.GetDisplayNode()
          displayNode.RemoveAllViewNodeIDs()
          volumeNodeID = fid.GetAttribute("AssociatedNodeID")
          if volumeNodeID:
            if self.sliceNodesByVolumeID.has_key(volumeNodeID):
              for sliceNode in self.sliceNodesByVolumeID[volumeNodeID]:
                displayNode.AddViewNodeID(sliceNode.GetID())

  def onLandmarkPicked(self,landmarkName):
    """Jump all slice views such that the selected landmark
    is visible"""
    self.restrictLandmarksToViews()
    self.updateSliceNodesByVolumeID()
    volumeNodes = self.currentVolumeNodes()
    fiducialsByName = self.logic.landmarksForVolumes(volumeNodes)
    if fiducialsByName.has_key(landmarkName):
      landmarksFiducials = fiducialsByName[landmarkName]
      for fid in landmarksFiducials:
        volumeNodeID = fid.GetAttribute("AssociatedNodeID")
        if self.sliceNodesByVolumeID.has_key(volumeNodeID):
          point = [0,]*3
          fid.GetFiducialCoordinates(point)
          for sliceNode in self.sliceNodesByVolumeID[volumeNodeID]:
            sliceNode.JumpSliceByCentering(*point)

  def onApplyButton(self):
    print("Run the algorithm")
    #self.logic.run(self.fixedSelector.currentNode(), self.movingSelector.currentNode())

  def onReload(self,moduleName="LandmarkRegistration"):
    """Generic reload method for any scripted module.
    ModuleWizard will subsitute correct default moduleName.
    """
    import imp, sys, os, slicer

    widgetName = moduleName + "Widget"

    # reload the source code
    # - set source file path
    # - load the module to the global space
    filePath = eval('slicer.modules.%s.path' % moduleName.lower())
    p = os.path.dirname(filePath)
    if not sys.path.__contains__(p):
      sys.path.insert(0,p)
    fp = open(filePath, "r")
    globals()[moduleName] = imp.load_module(
        moduleName, fp, filePath, ('.py', 'r', imp.PY_SOURCE))
    fp.close()

    # rebuild the widget
    # - find and hide the existing widget
    # - create a new widget in the existing parent
    parent = slicer.util.findChildren(name='%s Reload' % moduleName)[0].parent().parent()
    for child in parent.children():
      try:
        child.hide()
      except AttributeError:
        pass
    # Remove spacer items
    item = parent.layout().itemAt(0)
    while item:
      parent.layout().removeItem(item)
      item = parent.layout().itemAt(0)
    # create new widget inside existing parent
    globals()[widgetName.lower()] = eval(
        'globals()["%s"].%s(parent)' % (moduleName, widgetName))
    globals()[widgetName.lower()].setup()

  def onReloadAndTest(self,moduleName="LandmarkRegistration"):
    try:
      self.onReload()
      evalString = 'globals()["%s"].%sTest()' % (moduleName, moduleName)
      tester = eval(evalString)
      tester.runTest()
    except Exception, e:
      import traceback
      traceback.print_exc()
      qt.QMessageBox.warning(slicer.util.mainWindow(),
          "Reload and Test", 'Exception!\n\n' + str(e) + "\n\nSee Python Console for Stack Trace")


class Landmarks:
  """
  A "QWidget"-like class that manages a set of landmarks
  that are pairs of fiducials
  """

  def __init__(self,logic):
    self.logic = logic
    self.volumeNodes = []
    self.selectedLandmark = None # a landmark name
    self.landmarkGroupBox = None # a QGroupBox
    self.buttons = {} # the current buttons in the group box
    self.connections = {} # list of slots per signal

    self.widget = qt.QWidget()
    self.layout = qt.QFormLayout(self.widget)
    self.landmarkArrayHolder = qt.QWidget()
    self.landmarkArrayHolder.setLayout(qt.QVBoxLayout())
    self.layout.addRow(self.landmarkArrayHolder)
    self.updateLandmarkArray()

  def connect(self,signal,slot):
    """pseudo-connect - signal is arbitrary string and slot if callable"""
    if not self.connections.has_key(signal):
      self.connections[signal] = []
    self.connections[signal].append(slot)

  def emit(self,signal,args):
    """pseudo-emit - calls any slots connected to signal"""
    if self.connections.has_key(signal):
      for slot in self.connections[signal]:
        slot(args)

  def setVolumeNodes(self,volumeNodes):
    """Set up the widget to reflect the currently selected
    volume nodes.  This triggers an update of the landmarks"""
    self.volumeNodes = volumeNodes
    self.updateLandmarkArray()

  def updateLandmarkArray(self):
    """Rebuild the list of buttons based on current landmarks"""
    # reset the widget
    if self.landmarkGroupBox:
      self.landmarkGroupBox.setParent(None)
    self.landmarkGroupBox = qt.QGroupBox("Landmarks")
    self.landmarkGroupBox.setLayout(qt.QFormLayout())
    # add the action buttons at the top
    actionButtons = qt.QHBoxLayout()
    self.syncButton = qt.QPushButton("Sync")
    self.syncButton.connect('clicked()', self.syncLandmarks)
    actionButtons.addWidget(self.syncButton)
    self.addButton = qt.QPushButton("Add")
    self.addButton.connect('clicked()', self.addLandmark)
    actionButtons.addWidget(self.addButton)
    self.removeButton = qt.QPushButton("Remove")
    self.removeButton.connect('clicked()', self.removeLandmark)
    self.removeButton.enabled = False
    actionButtons.addWidget(self.removeButton)
    self.renameButton = qt.QPushButton("Rename")
    self.renameButton.connect('clicked()', self.renameLandmark)
    self.renameButton.enabled = False
    actionButtons.addWidget(self.renameButton)
    self.landmarkGroupBox.layout().addRow(actionButtons)
    self.buttons = {}

    # make a button for each current landmark
    landmarks = self.logic.landmarksForVolumes(self.volumeNodes)
    for landmarkName in landmarks.keys():
      button = qt.QPushButton(landmarkName)
      button.connect('clicked()', lambda l=landmarkName: self.pickLandmark(l))
      self.landmarkGroupBox.layout().addRow( button )
      self.buttons[landmarkName] = button
    self.landmarkArrayHolder.layout().addWidget(self.landmarkGroupBox)

  def pickLandmark(self,landmarkName):
    """Hightlight the named landmark button and emit
    a 'signal'"""
    for key in self.buttons.keys():
      self.buttons[key].text = key
    self.buttons[landmarkName].text = '*' + landmarkName
    self.selectedLandmark = landmarkName
    self.renameButton.enabled = True
    self.removeButton.enabled = True
    self.emit("LandmarkPicked(landmarkName)", landmarkName)

  def syncLandmarks(self):
    self.logic.syncLandmarks(self.volumeNodes)
    self.updateLandmarkArray()

  def addLandmark(self):
    landmarks = self.logic.landmarksForVolumes(self.volumeNodes)
    index = 0
    while True:
      landmarkName = 'L-%d' % index
      if not landmarkName in landmarks.keys():
        break
      index += 1
    for volumeNode in self.volumeNodes:
      fiducial = self.logic.addFiducial(landmarkName, position=(0, 0, 0),associatedNode=volumeNode)
    self.updateLandmarkArray()
    self.pickLandmark(landmarkName)

  def removeLandmark(self):
    self.logic.removeLandmarkForVolumes(self.selectedLandmark, self.volumeNodes)
    self.selectedLandmark = None
    self.updateLandmarkArray()

  def renameLandmark(self):
    landmarks = self.logic.landmarksForVolumes(self.volumeNodes)
    if landmarks.has_key(self.selectedLandmark):
      newName = qt.QInputDialog.getText(
          slicer.util.mainWindow(), "Rename Landmark",
          "New name for landmark '%s'?" % self.selectedLandmark)
      if newName != "":
        for fiducial in landmarks[self.selectedLandmark]:
          fiducial.SetName(newName)
        self.selectedLandmark = newName
        self.updateLandmarkArray()
        self.pickLandmark(newName)


#
# LandmarkRegistrationLogic
#

class LandmarkRegistrationLogic:
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget
  """
  def __init__(self):
    self.linearMode = 'Affine'

  def addFiducial(self,name,position=(0,0,0),associatedNode=None):
    """Add an instance of a fiducial to the scene for a given
    volume node"""

    annoLogic = slicer.modules.annotations.logic()
    slicer.mrmlScene.StartState(slicer.mrmlScene.BatchProcessState)

    # make the fiducial list if required
    listName = associatedNode.GetName() + "-landmarks"
    fidListHierarchyNode = slicer.util.getNode(listName)
    if not fidListHierarchyNode:
      fidListHierarchyNode = slicer.vtkMRMLAnnotationHierarchyNode()
      fidListHierarchyNode.HideFromEditorsOff()
      fidListHierarchyNode.SetName(listName)
      slicer.mrmlScene.AddNode(fidListHierarchyNode)
      # make it a child of the top level node
      fidListHierarchyNode.SetParentNodeID(annoLogic.GetTopLevelHierarchyNodeID())
    # make this active so that the fids will be added to it
    annoLogic.SetActiveHierarchyNodeID(fidListHierarchyNode.GetID())

    fiducialNode = slicer.vtkMRMLAnnotationFiducialNode()
    if associatedNode:
      fiducialNode.SetAttribute("AssociatedNodeID", associatedNode.GetID())
    fiducialNode.SetName(name)
    fiducialNode.AddControlPoint(position, True, True)
    fiducialNode.SetSelected(False)
    fiducialNode.SetLocked(False)
    slicer.mrmlScene.AddNode(fiducialNode)

    fiducialNode.CreateAnnotationTextDisplayNode()
    fiducialNode.CreateAnnotationPointDisplayNode()
    # TODO: pick appropriate defaults
    # 135,135,84
    fiducialNode.SetTextScale(2.)
    fiducialNode.GetAnnotationPointDisplayNode().SetGlyphScale(2)
    fiducialNode.GetAnnotationPointDisplayNode().SetGlyphTypeFromString('StarBurst2D')
    fiducialNode.SetDisplayVisibility(True)

    slicer.mrmlScene.EndState(slicer.mrmlScene.BatchProcessState)

  def removeLandmarkForVolumes(self,landmark,volumeNodes):
    """Remove the fiducial nodes from all the volumes.
    TODO: remove lingering hierarchy nodes"""
    slicer.mrmlScene.StartState(slicer.mrmlScene.BatchProcessState)
    landmarks = self.landmarksForVolumes(volumeNodes)
    if landmarks.has_key(landmark):
      for fid in landmarks[landmark]:
        slicer.mrmlScene.RemoveNode(fid)
    slicer.mrmlScene.EndState(slicer.mrmlScene.BatchProcessState)

  def volumeFiducialsByName(self,volumeNode):
    """return a dictionary of annotation nodes that are
    children of the list associated with the given
    volume node, where the keys are fiducial names
    and the values are fiducial nodes"""
    fiducialsByName = {}
    listName = volumeNode.GetName() + "-landmarks"
    fidListHierarchyNode = slicer.util.getNode(listName)
    if fidListHierarchyNode:
      childCollection = vtk.vtkCollection()
      fidListHierarchyNode.GetAllChildren(childCollection)
      for childIndex in range(childCollection.GetNumberOfItems()):
        fiducialNode = childCollection.GetItemAsObject(childIndex)
        fiducialsByName[fiducialNode.GetName()] = fiducialNode
    return fiducialsByName

  def volumeFiducialsAsList(self,volumeNode):
    """return a list of annotation nodes that are
    children of the list associated with the given
    volume node"""
    children = []
    listName = volumeNode.GetName() + "-landmarks"
    fidListHierarchyNode = slicer.util.getNode(listName)
    if fidListHierarchyNode:
      childCollection = vtk.vtkCollection()
      fidListHierarchyNode.GetAllChildren(childCollection)
      for childIndex in range(childCollection.GetNumberOfItems()):
        children.append(childCollection.GetItemAsObject(childIndex))
    return children

  def landmarksForVolumes(self,volumeNodes):
    """Return a dictionary of fiducial node lists, where each element
    is a list of the ids of fiducials with matching names in
    the landmark lists for each of the given volumes.
    Only fiducials that exist for all volumes are returned."""
    fiducialsByName = {}
    for volumeNode in volumeNodes:
      children = self.volumeFiducialsAsList(volumeNode)
      for child in children:
        if fiducialsByName.has_key(child.GetName()):
          fiducialsByName[child.GetName()].append(child)
        else:
          fiducialsByName[child.GetName()] = [child,]
    for childName in fiducialsByName.keys():
      if len(fiducialsByName[childName]) != len(volumeNodes):
        fiducialsByName.__delitem__(childName)
    return fiducialsByName

  def syncLandmarks(self,volumeNodes):
    """Ensure that all volume nodes have a complete set
    of matching landmarks - that is, make a set of landmarks
    that is the union of all unique fiducial names for all volumes
    and then make sure that each volume node has one
    of each of those fiducials.  Map these through the
    transform if needed.
    """
    # build the union of all names as a map
    # of fiducial names to a fiducial with that name
    allNamedFiducials = {}
    for volumeNode in volumeNodes:
      children = self.volumeFiducialsAsList(volumeNode)
      for child in children:
        if not allNamedFiducials.has_key(child.GetName()):
          allNamedFiducials[child.GetName()] = child
    # now add the missing ones
    for volumeNode in volumeNodes:
      fiducialsByName = self.volumeFiducialsByName(volumeNode)
      for fiducialName in allNamedFiducials:
        if not fiducialsByName.has_key(fiducialName):
          point = [0,]*3
          fiducialsByName[fiducialName].GetFiducialCoordinates(point)
          self.addFiducial(fiducialName, position=point,associatedNode=volumeNode)

  def enableLinearRegistration(self,fixed,moving,landmarks,transform,transformed):
    print("enable")
    self.performLinearRegistration(fixed,moving,landmarks,transform,transformed)
    # TODO: set up observers on fixed and moving fiducial
    pass

  def performLinearRegistration(self,fixed,moving,landmarks,transform,transformed):
    transformed.SetAndObserveTransformNodeID(transform.GetID())
    landmarkTransform = vtk.vtkLandmarkTransform()
    if self.linearMode == 'Rigid':
      landmarkTransform.SetModeToRigidBody()
    if self.linearMode == 'Similarity':
      landmarkTransform.SetModeToSimilarity()
    if self.linearMode == 'Affine':
      landmarkTransform.SetModeToAffine()

    points = {}
    point = [0,]*3
    for volumeNode in (fixed,moving):
      points[volumeNode] = vtk.vtkPoints()
    for fiducials in landmarks.values():
      for volumeNode,fid in zip((fixed,moving),fiducials):
        fid.GetFiducialCoordinates(point)
        points[volumeNode].InsertNextPoint(point)
        print("%s: %s" % (volumeNode.GetName(), str(point)))
    landmarkTransform.SetSourceLandmarks(points[moving])
    landmarkTransform.SetTargetLandmarks(points[fixed])
    landmarkTransform.Update()
    transform.SetAndObserveMatrixTransformToParent(landmarkTransform.GetMatrix())

  def disableLinearRegistration(self):
    print("disable")
    pass


  def run(self,inputVolume,outputVolume):
    """
    Run the actual algorithm
    """
    return True


class LandmarkRegistrationTest(unittest.TestCase):
  """
  This is the test case for your scripted module.
  """

  def delayDisplay(self,message,msec=1000):
    """This utility method displays a small dialog and waits.
    This does two things: 1) it lets the event loop catch up
    to the state of the test so that rendering and widget updates
    have all taken place before the test continues and 2) it
    shows the user/developer/tester the state of the test
    so that we'll know when it breaks.
    """
    print(message)
    self.info = qt.QDialog()
    self.infoLayout = qt.QVBoxLayout()
    self.info.setLayout(self.infoLayout)
    self.label = qt.QLabel(message,self.info)
    self.infoLayout.addWidget(self.label)
    qt.QTimer.singleShot(msec, self.info.close)
    self.info.exec_()

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_LandmarkRegistration1()

  def test_LandmarkRegistration1(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests sould exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

    self.delayDisplay("Starting the test")
    #
    # first, get some data
    #
    import SampleData
    sampleDataLogic = SampleData.SampleDataLogic()
    mrHead = sampleDataLogic.downloadMRHead()
    dtiBrain = sampleDataLogic.downloadDTIBrain()
    self.delayDisplay('Two data sets loaded')

    w = LandmarkRegistrationWidget()
    w.volumeSelectors["Fixed"].setCurrentNode(dtiBrain)
    w.volumeSelectors["Moving"].setCurrentNode(mrHead)

    logic = LandmarkRegistrationLogic()
    
    for name,point in (
      ('tip-of-nose', [35.115070343017578, 74.803565979003906, -21.032917022705078]),
      ('middle-of-left-eye', [0.50825262069702148, 128.85432434082031, -48.434154510498047]),
      ('left-ear', [80.0, -26.329217910766602, -15.292181015014648]),
      ):
      logic.addFiducial(name, position=point,associatedNode=mrHead)

    for name,point in (
      ('tip-of-nose', [28.432207107543945, 71.112533569335938, -41.938472747802734]),
      ('middle-of-left-eye', [0.9863210916519165, 94.6998291015625, -49.877540588378906]),
      ('left-ear', [79.28509521484375, -12.95069694519043, 5.3944296836853027]),
      ):
      logic.addFiducial(name, position=point,associatedNode=dtiBrain)

    w.onVolumeNodeSelect()
    w.onLayout()
    w.onLandmarkPicked('tip-of-nose')

    self.delayDisplay('Test passed!')
