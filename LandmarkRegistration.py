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
  def __init__(self, parent = None):
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

    # Layout within the dummy collapsible button
    parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)

    #
    # moving volume selector
    #
    self.movingSelector = slicer.qMRMLNodeComboBox()
    self.movingSelector.nodeTypes = ( ("vtkMRMLScalarVolumeNode"), "" )
    self.movingSelector.addAttribute( "vtkMRMLScalarVolumeNode", "LabelMap", 0 )
    self.movingSelector.selectNodeUponCreation = False
    self.movingSelector.addEnabled = False
    self.movingSelector.removeEnabled = True
    self.movingSelector.noneEnabled = False
    self.movingSelector.showHidden = False
    self.movingSelector.showChildNodeTypes = True
    self.movingSelector.setMRMLScene( slicer.mrmlScene )
    self.movingSelector.setToolTip( "Pick the moving volume." )
    parametersFormLayout.addRow("Moving Volume: ", self.movingSelector)

    #
    # fixed volume selector
    #
    self.fixedSelector = slicer.qMRMLNodeComboBox()
    self.fixedSelector.nodeTypes = ( ("vtkMRMLScalarVolumeNode"), "" )
    self.fixedSelector.addAttribute( "vtkMRMLScalarVolumeNode", "LabelMap", 0 )
    self.fixedSelector.selectNodeUponCreation = True
    self.fixedSelector.addEnabled = False
    self.fixedSelector.removeEnabled = True
    self.fixedSelector.noneEnabled = False
    self.fixedSelector.showHidden = False
    self.fixedSelector.showChildNodeTypes = True
    self.fixedSelector.setMRMLScene( slicer.mrmlScene )
    self.fixedSelector.setToolTip( "Pick the fixed volume." )
    parametersFormLayout.addRow("Fixed Volume: ", self.fixedSelector)

    #
    # warped volume selector
    #
    self.warpedSelector = slicer.qMRMLNodeComboBox()
    self.warpedSelector.nodeTypes = ( ("vtkMRMLScalarVolumeNode"), "" )
    self.warpedSelector.addAttribute( "vtkMRMLScalarVolumeNode", "LabelMap", 0 )
    self.warpedSelector.selectNodeUponCreation = False
    self.warpedSelector.addEnabled = True
    self.warpedSelector.removeEnabled = True
    self.warpedSelector.noneEnabled = True
    self.warpedSelector.showHidden = False
    self.warpedSelector.showChildNodeTypes = True
    self.warpedSelector.setMRMLScene( slicer.mrmlScene )
    self.warpedSelector.setToolTip( "Pick the warped volume, which is the target for the registration." )
    parametersFormLayout.addRow("Warped Volume: ", self.warpedSelector)

    #
    # layout options
    #
    layout = qt.QHBoxLayout()
    self.layoutComboBox = qt.QComboBox()
    self.layoutComboBox.addItem('Axial')
    self.layoutComboBox.addItem('Sagittal')
    self.layoutComboBox.addItem('Coronal')
    #self.layoutComboBox.addItem('Axial/Sagittal/Coronal')
    #self.layoutComboBox.addItem('Ax/Sag/Cor/3D')
    layout.addWidget(self.layoutComboBox)
    self.layoutButton = qt.QPushButton('Layout')
    self.layoutButton.connect('clicked()', self.onLayout)
    layout.addWidget(self.layoutButton)
    parametersFormLayout.addRow("Layout Mode: ", layout)

    #
    # Landmark Widget
    #
    self.landmarks = Landmarks()
    parametersFormLayout.addRow(self.landmarks.widget)

    #
    # Apply Button
    #
    self.applyButton = qt.QPushButton("Run Registration")
    self.applyButton.toolTip = "Run the registration algorithm."
    self.applyButton.enabled = False
    parametersFormLayout.addRow(self.applyButton)

    # connections
    self.applyButton.connect('clicked(bool)', self.onApplyButton)
    self.fixedSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)
    self.movingSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)

    # Add vertical spacer
    self.layout.addStretch(1)

  def onSelect(self):
    self.applyButton.enabled = self.fixedSelector.currentNode() and self.movingSelector.currentNode()

  def onLayout(self):
    volumeNodes = []
    viewNames = []
    volumeViews = ( ('Moving', self.movingSelector),
                    ('Fixed', self.fixedSelector),
                    ('Warped', self.warpedSelector) )
    for name, selector in volumeViews:
      volumeNode = selector.currentNode()
      if volumeNode:
        volumeNodes.append(volumeNode)
        viewNames.append(name)
    mode = self.layoutComboBox.currentText
    import CompareVolumes
    logic = CompareVolumes.CompareVolumesLogic()
    oneViewModes = ('Axial', 'Sagittal', 'Coronal',)
    if mode in oneViewModes:
      logic.viewerPerVolume(volumeNodes,viewNames=viewNames,orientation=mode)

  def onApplyButton(self):
    logic = LandmarkRegistrationLogic()
    print("Run the algorithm")
    logic.run(self.fixedSelector.currentNode(), self.movingSelector.currentNode())

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


class Landmark:
  """
  A convenience class for keeping track of landmarks, which
  are multiple related fiducials.
  """

  def __init__(self):
    self.name = "Landmark"
    self.fixedFiducialID = None
    self.movingFiducialID = None
    self.warpedFiducialID = None
    self.steeringFiducialID = None
    self.weight = 1.0


class Landmarks:
  """
  A "QWidget"-like class that manages a set of landmarks
  that are pairs of fiducials
  """

  def __init__(self):
    self.landmarks = [] # list of mrml scene annotation node IDs
    self.selectedLandmark = None # a node ID
    self.landmarkGroupBox = None # a QGroupBox
    self.buttons = {} # the current buttons in the group box

    self.widget = qt.QWidget()
    self.layout = qt.QFormLayout(self.widget)
    self.landmarkArrayHolder = qt.QWidget()
    self.landmarkArrayHolder.setLayout(qt.QVBoxLayout())
    self.layout.addRow(self.landmarkArrayHolder)
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
    for landmark in self.landmarks:
      button = qt.QPushButton(landmark)
      button.connect('clicked()', lambda l=landmark: self.pickLandmark(l))
      self.landmarkGroupBox.layout().addRow( button )
      self.buttons[landmark] = button
    self.landmarkArrayHolder.layout().addWidget(self.landmarkGroupBox)

  def pickLandmark(self,landmark):
    for key in self.buttons.keys():
      self.buttons[key].text = key
    self.buttons[landmark].text = '*' + landmark
    self.selectedLandmark = landmark
    self.renameButton.enabled = True
    self.removeButton.enabled = True

  def addLandmark(self):
    import time
    newLandmark = 'new' + str(time.time())
    self.landmarks.append(newLandmark)
    self.updateLandmarkArray()
    self.pickLandmark(newLandmark)

  def removeLandmark(self):
    self.landmarks.remove(self.selectedLandmark)
    self.selectedLandmark = None
    self.updateLandmarkArray()

  def renameLandmark(self):
    newName = qt.QInputDialog.getText(
        slicer.util.mainWindow(), "Rename Landmark",
        "New name for landmark '%s'?" % self.selectedLandmark)
    if newName != "":
      self.landmarks[self.landmarks.index(self.selectedLandmark)] = newName
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
    pass

  def hasImageData(self,volumeNode):
    """This is a dummy logic method that
    returns true if the passed in volume
    node has valid image data
    """
    if not volumeNode:
      print('no volume node')
      return False
    if volumeNode.GetImageData() == None:
      print('no image data')
      return False
    return True

  def addLandmark(self,position=(0,0,0),associatedNode=None):
    """Add an instance of a landmark to the scene"""

    annoLogic = slicer.modules.annotations.logic()
    slicer.mrmlScene.StartState(slicer.mrmlScene.BatchProcessState)

    # make the fiducial list if required
    if True:
      listName = associatedNode.GetName() + "-landmarks"
      fidListHierarchyNode = slicer.vtkMRMLAnnotationHierarchyNode()
      fidListHierarchyNode.HideFromEditorsOff()
      fidListHierarchyNode.SetName(listName)
      slicer.mrmlScene.AddNode(fidListHierarchyNode)
      # make it a child of the top level node
      fidListHierarchyNode.SetParentNodeID(annoLogic.GetTopLevelHierarchyNodeID())
      # and make it active so that the fids will be added to it
      annoLogic.SetActiveHierarchyNodeID(fidListHierarchyNode.GetID())

    fiducialNode = slicer.vtkMRMLAnnotationFiducialNode()
    fiducialNode.SetName("New Anno")
    fiducialNode.AddControlPoint(position, True, True)
    slicer.mrmlScene.AddNode(fiducialNode)

    C = """
  // now iterate through the list and make fiducials
  int numFids = node->GetNumberOfFiducials();
  double *color = node->GetColor();
  double *selColor = node->GetSelectedColor();
  double symbolScale = node->GetSymbolScale();
  double textScale = node->GetTextScale();
  int locked = node->GetLocked();
  int glyphType = node->GetGlyphType();
  for (int n = 0; n < numFids; n++)
    {
    float *xyz = node->GetNthFiducialXYZ(n);
    int sel = node->GetNthFiducialSelected(n);
    int vis = node->GetNthFiducialVisibility(n);
    const char *labelText = node->GetNthFiducialLabelText(n);

    // now make an annotation
    vtkMRMLAnnotationFiducialNode * fnode = vtkMRMLAnnotationFiducialNode::New();
    fnode->SetName(labelText);
    double coord[3] = {(double)xyz[0], (double)xyz[1], (double)xyz[2]};
    fnode->AddControlPoint(coord, sel, vis);
    fnode->SetSelected(sel);
    fnode->SetLocked(locked);

    this->GetMRMLScene()->AddNode(fnode);
    if (n != 0)
      {
      idList += std::string(",");
      }
    idList += std::string(fnode->GetID());
    fnode->CreateAnnotationTextDisplayNode();
    fnode->CreateAnnotationPointDisplayNode();
    fnode->SetTextScale(textScale);
    fnode->GetAnnotationPointDisplayNode()->SetGlyphScale(symbolScale);
    fnode->GetAnnotationPointDisplayNode()->SetGlyphType(glyphType);
    fnode->GetAnnotationPointDisplayNode()->SetColor(color);
    fnode->GetAnnotationPointDisplayNode()->SetSelectedColor(selColor);
    fnode->GetAnnotationTextDisplayNode()->SetColor(color);
    fnode->GetAnnotationTextDisplayNode()->SetSelectedColor(selColor);
    fnode->SetDisplayVisibility(vis);
    fnode->Delete();
    }
  // clean up
  fidListHierarchyNode->Delete();
  // remove the legacy node
  this->GetMRMLScene()->RemoveNode(node->GetStorageNode());
  this->GetMRMLScene()->RemoveNode(node);

  // turn off batch processing
  this->GetMRMLScene()->EndState(vtkMRMLScene::BatchProcessState);

  if (idList.length())
    {
    nodeID = (char *)malloc(sizeof(char) * (idList.length() + 1));
    strcpy(nodeID, idList.c_str());
    }
  return nodeID;
  """


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
    w.fixedSelector.setCurrentNode(mrHead)
    w.movingSelector.setCurrentNode(dtiBrain)

    logic = LandmarkRegistrationLogic()
    landmark = logic.addLandmark(position=(10, 0, -.5),associatedNode=mrHead)

    self.delayDisplay('Test passed!')
