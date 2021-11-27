import qt, slicer, os
from . import pqWidget

class LandmarksWidget(pqWidget):
  """
  A "QWidget"-like class that manages a set of landmarks
  that are pairs of points
  """

  def __init__(self,logic):
    super().__init__()
    self.logic = logic
    self.volumeNodes = []
    self.selectedLandmark = None # a landmark name
    self.landmarkGroupBox = None # a QGroupBox
    self.labels = {} # the current buttons in the group box
    self.pendingUpdate = False # update on new scene nodes
    self.updatingPoints = False # don't update while update in process
    self.observerTags = [] # for monitoring point changes
    self.movingView = None # layoutName of slice node where point is being moved

    self.widget = qt.QWidget()
    self.layout = qt.QFormLayout(self.widget)
    self.landmarkArrayHolder = qt.QWidget()
    self.landmarkArrayHolder.setLayout(qt.QVBoxLayout())
    self.layout.addRow(self.landmarkArrayHolder)
    self.updateLandmarkArray()

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
    # add button - http://www.clipartbest.com/clipart-jTxpEM8Bc
    self.addButton = qt.QPushButton("Add")
    self.addButton.setIcon(qt.QIcon(os.path.join(os.path.dirname(slicer.modules.landmarkregistration.path), 'Resources/Icons/', "icon_Add.png")))
    self.addButton.connect('clicked()', self.addLandmark)
    actionButtons.addWidget(self.addButton)
    self.renameButton = qt.QPushButton("Rename")
    self.renameButton.connect('clicked()', self.renameLandmark)
    self.renameButton.enabled = False
    actionButtons.addWidget(self.renameButton)
    self.landmarkGroupBox.layout().addRow(actionButtons)

    # for now, hide
    self.renameButton.hide()

    # make a button for each current landmark
    self.labels = {}
    landmarks = self.logic.landmarksForVolumes(self.volumeNodes)
    keys = sorted(landmarks.keys())
    for landmarkName in keys:
      row = qt.QWidget()
      rowLayout = qt.QHBoxLayout()
      rowLayout.setMargin(0)

      label = qt.QLabel(landmarkName)
      rowLayout.addWidget(label, 8)

      # active button - https://thenounproject.com/term/crosshair/4434/
      activeButton = qt.QPushButton()
      activeButton.setIcon(qt.QIcon(os.path.join(os.path.dirname(slicer.modules.landmarkregistration.path), 'Resources/Icons/', "icon_Active.png")))
      activeButton.connect('clicked()', lambda l=landmarkName: self.pickLandmark(l))
      rowLayout.addWidget(activeButton, 1)

      if landmarkName == self.selectedLandmark:
        label.setStyleSheet("QWidget{font-weight: bold;}")
        activeButton.setEnabled(False)

      # remove button - http://findicons.com/icon/158288/trash_recyclebin_empty_closed_w
      removeButton = qt.QPushButton()
      removeButton.setIcon(qt.QIcon(os.path.join(os.path.dirname(slicer.modules.landmarkregistration.path), 'Resources/Icons/', "icon_Trash.png")))
      removeButton.connect('clicked()', lambda l=landmarkName: self.removeLandmark(l))
      rowLayout.addWidget(removeButton, 1)

      row.setLayout(rowLayout)

      self.landmarkGroupBox.layout().addRow( row )
      self.labels[landmarkName] = [label, activeButton]
    self.landmarkArrayHolder.layout().addWidget(self.landmarkGroupBox)

    # observe manipulation of the landmarks
    self.addLandmarkObservers()

  def addLandmarkObservers(self):
    """Add observers to all pointLists in scene
    so we will know when new markups are added
    """
    self.removeLandmarkObservers()
    for pointList in slicer.util.getNodes('vtkMRMLMarkupsFiducialNode*').values():
      tag = pointList.AddObserver(
              pointList.PointModifiedEvent, lambda caller,event: self.onPointMoved(caller))
      self.observerTags.append( (pointList,tag) )
      tag = pointList.AddObserver(
              pointList.PointEndInteractionEvent, lambda caller,event: self.onPointEndMoving(caller))
      self.observerTags.append( (pointList,tag) )
      tag = pointList.AddObserver(
              pointList.PointPositionDefinedEvent, self.requestNodeAddedUpdate)
      self.observerTags.append( (pointList,tag) )
      tag = pointList.AddObserver(
              pointList.PointPositionUndefinedEvent, self.requestNodeAddedUpdate)
      self.observerTags.append( (pointList,tag) )

  def onPointMoved(self,pointList):
    """Callback when pointList's point has been changed.
    Check the Markups.State attribute to see if it is being
    actively moved and if so, skip the picked method."""
    self.movingView = pointList.GetAttribute('Markups.MovingInSliceView')
    movingIndexAttribute = pointList.GetAttribute('Markups.MovingMarkupIndex')
    if self.movingView and movingIndexAttribute:
      movingIndex = int(movingIndexAttribute)
      if movingIndex < pointList.GetNumberOfDefinedControlPoints():
        landmarkName = pointList.GetNthControlPointLabel(movingIndex)
        self.pickLandmark(landmarkName,clearMovingView=False)
        self.emit("landmarkMoved(landmarkName)", (landmarkName,))

  def onPointEndMoving(self,pointList):
    """Callback when pointList's point is done moving."""
    movingIndexAttribute = pointList.GetAttribute('Markups.MovingMarkupIndex')
    if movingIndexAttribute:
      movingIndex = int(movingIndexAttribute)
      landmarkName = pointList.GetNthControlPointLabel(movingIndex)
      self.pickLandmark(landmarkName,clearMovingView=False)
      self.emit("landmarkEndMoving(landmarkName)", (landmarkName,))

  def removeLandmarkObservers(self):
    """Remove any existing observers"""
    for obj,tag in self.observerTags:
      obj.RemoveObserver(tag)
    self.observerTags = []

  def pickLandmark(self,landmarkName,clearMovingView=True):
    """Hightlight the named landmark button and emit a 'signal'"""
    for key in self.labels.keys():
      self.labels[key][0].setStyleSheet("QWidget{font-weight: normal;}")
      self.labels[key][1].setEnabled(True)
    try:
      self.labels[landmarkName][0].setStyleSheet("QWidget{font-weight: bold;}")
      self.labels[landmarkName][1].setEnabled(False)
    except KeyError:
      pass
    self.selectedLandmark = landmarkName
    self.renameButton.enabled = True
    if clearMovingView:
      self.movingView = None
    self.emit("landmarkPicked(landmarkName)", (landmarkName,))

  def addLandmark(self):
    """Enable markup place mode so point can be added.
    When the node is added it will be incorporated into the
    registration system as a landmark.
    """
    applicationLogic = slicer.app.applicationLogic()
    selectionNode = applicationLogic.GetSelectionNode()

    selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
    interactionNode = applicationLogic.GetInteractionNode()
    interactionNode.SwitchToSinglePlaceMode()

  def removeLandmark(self, landmarkName):
    self.logic.removeLandmarkForVolumes(landmarkName, self.volumeNodes)
    if landmarkName == self.selectedLandmark:
      self.selectedLandmark = None
    self.updateLandmarkArray()

  def renameLandmark(self):
    landmarks = self.logic.landmarksForVolumes(self.volumeNodes)
    if self.selectedLandmark in landmarks:
      newName = qt.QInputDialog.getText(
          slicer.util.mainWindow(), "Rename Landmark",
          "New name for landmark '%s'?" % self.selectedLandmark)
      if newName != "":
        for pointList,index in landmarks[self.selectedLandmark]:
          pointList.SetNthControlPointLabel(newName)
        self.selectedLandmark = newName
        self.updateLandmarkArray()
        self.pickLandmark(newName)

  def requestNodeAddedUpdate(self,caller,event):
    """Start a SingleShot timer that will check the points
    in the scene and turn them into landmarks if needed"""
    if not self.pendingUpdate:
      qt.QTimer.singleShot(0, self.wrappedNodeAddedUpdate)
      self.pendingUpdate = True

  def wrappedNodeAddedUpdate(self):
    try:
      self.nodeAddedUpdate()
    except Exception as e:
      import traceback
      traceback.print_exc()
      qt.QMessageBox.warning(slicer.util.mainWindow(),
          "Node Added", 'Exception!\n\n' + str(e) + "\n\nSee Python Console for Stack Trace")

  def nodeAddedUpdate(self):
    """Perform the update of any new points.
    First collect from any point lists not associated with one of our
    volumes (like when the process first gets started) and then check for
    new points added to one of our lists.
    End result should be one point per list with identical names and
    correctly assigned associated node ids.
    Most recently created new point is picked as active landmark.
    """
    if self.updatingPoints:
      return
    slicer.mrmlScene.StartState(slicer.mrmlScene.BatchProcessState)
    self.updatingPoints = True
    addedAssociatedLandmark = self.logic.collectAssociatedPoints(self.volumeNodes)
    addedLandmark = self.logic.landmarksFromPoints(self.volumeNodes)
    if not addedLandmark:
      addedLandmark = addedAssociatedLandmark
    if addedLandmark:
      self.pickLandmark(addedLandmark)
    self.addLandmarkObservers()
    self.updateLandmarkArray()
    self.pendingUpdate = False
    self.updatingPoints = False
    slicer.mrmlScene.EndState(slicer.mrmlScene.BatchProcessState)

