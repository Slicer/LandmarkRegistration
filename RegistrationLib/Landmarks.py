import qt, slicer
from . import pqWidget

class LandmarksWidget(pqWidget):
  """
  A "QWidget"-like class that manages a set of landmarks
  that are pairs of fiducials
  """

  def __init__(self,logic):
    super(LandmarksWidget,self).__init__()
    self.logic = logic
    self.volumeNodes = []
    self.selectedLandmark = None # a landmark name
    self.landmarkGroupBox = None # a QGroupBox
    self.buttons = {} # the current buttons in the group box
    self.pendingUpdate = False # update on new scene nodes
    self.updatingFiducials = False # don't update while update in process
    self.observerTags = [] # for monitoring fiducial changes
    self.movingView = None # layoutName of slice node where fiducial is being moved

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

    # for now, hide these
    #self.addButton.hide()
    self.removeButton.hide()
    self.renameButton.hide()

    # make a button for each current landmark
    self.buttons = {}
    landmarks = self.logic.landmarksForVolumes(self.volumeNodes)
    keys = landmarks.keys()
    keys.sort()
    for landmarkName in keys:
      button = qt.QPushButton(landmarkName)
      button.connect('clicked()', lambda l=landmarkName: self.pickLandmark(l))
      self.landmarkGroupBox.layout().addRow( button )
      self.buttons[landmarkName] = button
    self.landmarkArrayHolder.layout().addWidget(self.landmarkGroupBox)

    # observe manipulation of the landmarks
    self.addLandmarkObservers()

  def addLandmarkObservers(self):
    """Add observers to all fiducialLists in scene
    so we will know when new markups are added
    """
    self.removeLandmarkObservers()
    for fiducialList in slicer.util.getNodes('vtkMRMLMarkupsFiducialNode*').values():
      tag = fiducialList.AddObserver(
              fiducialList.PointModifiedEvent, lambda caller,event: self.onFiducialMoved(caller))
      self.observerTags.append( (fiducialList,tag) )
      tag = fiducialList.AddObserver(
              fiducialList.PointEndInteractionEvent, lambda caller,event: self.onFiducialEndMoving(caller))
      self.observerTags.append( (fiducialList,tag) )
      tag = fiducialList.AddObserver(
              fiducialList.MarkupAddedEvent, self.requestNodeAddedUpdate)
      self.observerTags.append( (fiducialList,tag) )
      tag = fiducialList.AddObserver(
              fiducialList.MarkupRemovedEvent, self.requestNodeAddedUpdate)
      self.observerTags.append( (fiducialList,tag) )

  def onFiducialMoved(self,fiducialList):
    """Callback when fiducialList's point has been changed.
    Check the Markups.State attribute to see if it is being
    actively moved and if so, skip the picked method."""
    self.movingView = fiducialList.GetAttribute('Markups.MovingInSliceView')
    movingIndexAttribute = fiducialList.GetAttribute('Markups.MovingMarkupIndex')
    if self.movingView and movingIndexAttribute:
      movingIndex = int(movingIndexAttribute)
      landmarkName = fiducialList.GetNthMarkupLabel(movingIndex)
      self.pickLandmark(landmarkName,clearMovingView=False)
      self.emit("landmarkMoved(landmarkName)", (landmarkName,))

  def onFiducialEndMoving(self,fiducialList):
    """Callback when fiducialList's point is done moving."""
    movingIndexAttribute = fiducialList.GetAttribute('Markups.MovingMarkupIndex')
    if movingIndexAttribute:
      movingIndex = int(movingIndexAttribute)
      landmarkName = fiducialList.GetNthMarkupLabel(movingIndex)
      self.pickLandmark(landmarkName,clearMovingView=False)
      self.emit("landmarkEndMoving(landmarkName)", (landmarkName,))

  def removeLandmarkObservers(self):
    """Remove any existing observers"""
    for obj,tag in self.observerTags:
      obj.RemoveObserver(tag)
    self.observerTags = []

  def pickLandmark(self,landmarkName,clearMovingView=True):
    """Hightlight the named landmark button and emit
    a 'signal'"""
    for key in self.buttons.keys():
      self.buttons[key].text = key
    try:
      self.buttons[landmarkName].text = '*' + landmarkName
    except KeyError:
      pass
    self.selectedLandmark = landmarkName
    self.renameButton.enabled = True
    self.removeButton.enabled = True
    if clearMovingView:
      self.movingView = None
    self.emit("landmarkPicked(landmarkName)", (landmarkName,))

  def addLandmark(self):
    """Enable markup place mode so fiducial can be added.
    When the node is added it will be incorporated into the
    registration system as a landmark.
    """
    applicationLogic = slicer.app.applicationLogic()
    selectionNode = applicationLogic.GetSelectionNode()

    selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
    interactionNode = applicationLogic.GetInteractionNode()
    interactionNode.SwitchToSinglePlaceMode()

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
        for fiducialList,index in landmarks[self.selectedLandmark]:
          fiducialList.SetNthFiducialLabel(newName)
        self.selectedLandmark = newName
        self.updateLandmarkArray()
        self.pickLandmark(newName)

  def requestNodeAddedUpdate(self,caller,event):
    """Start a SingleShot timer that will check the fiducials
    in the scene and turn them into landmarks if needed"""
    if not self.pendingUpdate:
      qt.QTimer.singleShot(0, self.wrappedNodeAddedUpdate)
      self.pendingUpdate = True

  def wrappedNodeAddedUpdate(self):
    try:
      self.nodeAddedUpdate()
    except Exception, e:
      import traceback
      traceback.print_exc()
      qt.QMessageBox.warning(slicer.util.mainWindow(),
          "Node Added", 'Exception!\n\n' + str(e) + "\n\nSee Python Console for Stack Trace")

  def nodeAddedUpdate(self):
    """Perform the update of any new fiducials.
    First collect from any fiducial lists not associated with one of our
    volumes (like when the process first gets started) and then check for
    new fiducials added to one of our lists.
    End result should be one fiducial per list with identical names and
    correctly assigned associated node ids.
    Most recently created new fiducial is picked as active landmark.
    """
    if self.updatingFiducials:
      return
    slicer.mrmlScene.StartState(slicer.mrmlScene.BatchProcessState)
    self.updatingFiducials = True
    addedAssociatedLandmark = self.logic.collectAssociatedFiducials(self.volumeNodes)
    addedLandmark = self.logic.landmarksFromFiducials(self.volumeNodes)
    if not addedLandmark:
      addedLandmark = addedAssociatedLandmark
    if addedLandmark:
      self.pickLandmark(addedLandmark)
    self.addLandmarkObservers()
    self.updateLandmarkArray()
    self.pendingUpdate = False
    self.updatingFiducials = False
    slicer.mrmlScene.EndState(slicer.mrmlScene.BatchProcessState)

