import vtk, qt, ctk, slicer
from . import RegistrationPlugin


#########################################################
#
#
comment = """

  RegistrationPlugin is a superclass for code that plugs into the
  slicer LandmarkRegistration module.

  These classes are Abstract.

# TODO :
"""
#
#########################################################



#
# RegistrationPlugin
#

class AffinePlugin(RegistrationPlugin):
  """ Base class for Registration plugins
  """

  #
  # generic settings that can (should) be overridden by the subclass
  #

  # displayed for the user to select the registration
  name = "Affine Registration"
  tooltip = "Uses landmarks to define linear transform matrices"

  # can be true or false
  # - True: landmarks are displayed and managed by LandmarkRegistration
  # - False: landmarks are hidden
  usesLandmarks = True

  # can be any non-negative number
  # - widget will be disabled until landmarks are defined
  landmarksNeededToEnable = 1

  # used for reloading - every concrete class should include this
  sourceFile = __file__

  def __init__(self,parent=None):
    super().__init__(parent)

  def create(self,registrationState):
    """Make the plugin-specific user interface"""
    super().create(registrationState)

    self.linearMode = "Rigid"

    #
    # Linear Registration Pane - initially hidden
    # - interface options for linear registration
    # - TODO: move registration code into separate plugins
    #
    linearCollapsibleButton = ctk.ctkCollapsibleButton()
    linearCollapsibleButton.text = "Linear Registration"
    linearFormLayout = qt.QFormLayout()
    linearCollapsibleButton.setLayout(linearFormLayout)
    self.widgets.append(linearCollapsibleButton)

    buttonLayout = qt.QVBoxLayout()
    linearModeButtons = {}
    self.linearModes = ("Rigid", "Similarity", "Affine")
    for mode in self.linearModes:
      linearModeButtons[mode] = qt.QRadioButton()
      linearModeButtons[mode].text = mode
      linearModeButtons[mode].setToolTip( "Run the registration in %s mode." % mode )
      buttonLayout.addWidget(linearModeButtons[mode])
      self.widgets.append(linearModeButtons[mode])
      linearModeButtons[mode].connect('clicked()', lambda m=mode : self.onLinearTransform(m))
    linearModeButtons[self.linearMode].checked = True
    linearFormLayout.addRow("Registration Mode ", buttonLayout)

    self.parent.layout().addWidget(linearCollapsibleButton)


  def destroy(self):
    """Clean up"""
    super().destroy()

  def onLandmarkMoved(self,state):
    """Perform the linear transform using the vtkLandmarkTransform class"""
    if state.transformed:
      if state.transformed.GetTransformNodeID() != state.transform.GetID():
        state.transformed.SetAndObserveTransformNodeID(state.transform.GetID())

    if not state.fixedPoints or not state.movingPoints:
      return

    # try to use user selection, but fall back if not enough points are available
    landmarkTransform = vtk.vtkLandmarkTransform()
    if self.linearMode == 'Rigid':
      landmarkTransform.SetModeToRigidBody()
    if self.linearMode == 'Similarity':
      landmarkTransform.SetModeToSimilarity()
    if self.linearMode == 'Affine':
      landmarkTransform.SetModeToAffine()
    if state.fixedPoints.GetNumberOfControlPoints() < 3:
      landmarkTransform.SetModeToRigidBody()

    volumeNodes = (state.fixed, state.moving)
    pointListNodes = (state.fixedPoints,state.movingPoints)
    points = state.logic.vtkPointsForVolumes( volumeNodes, pointListNodes )
    landmarkTransform.SetSourceLandmarks(points[state.moving])
    landmarkTransform.SetTargetLandmarks(points[state.fixed])
    landmarkTransform.Update()
    state.transform.SetAndObserveTransformToParent(landmarkTransform)

  def onLinearTransform(self,mode):
    state = self.registrationState()
    self.linearMode = mode
    self.onLandmarkMoved(state)



# Add this plugin to the dictionary of available registrations.
# Since this module may be discovered before the Editor itself,
# create the list if it doesn't already exist.
try:
  slicer.modules.registrationPlugins
except AttributeError:
  slicer.modules.registrationPlugins = {}
slicer.modules.registrationPlugins['Affine'] = AffinePlugin

