import os
from __main__ import vtk, qt, ctk, slicer
import RegistrationLib


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

class ThinPlatePlugin(RegistrationLib.RegistrationPlugin):
  """ Plugin for thin plat spline using vtk
  """

  #
  # generic settings that can (should) be overridden by the subclass
  #

  # displayed for the user to select the registration
  name = "ThinPlate Registration"
  tooltip = "Uses landmarks to define nonlinear warp transform"

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
    super(ThinPlatePlugin,self).__init__(parent)

  def create(self,registationState):
    """Make the plugin-specific user interface"""
    super(ThinPlatePlugin,self).create(registationState)
    #
    # Thin Plate Spline Registration Pane
    #
    self.thinPlateCollapsibleButton = ctk.ctkCollapsibleButton()
    self.thinPlateCollapsibleButton.text = "Thin Plate Spline Registration"
    thinPlateFormLayout = qt.QFormLayout()
    self.thinPlateCollapsibleButton.setLayout(thinPlateFormLayout)
    self.widgets.append(self.thinPlateCollapsibleButton)

    self.thinPlateApply = qt.QPushButton("Apply")
    self.thinPlateApply.connect('clicked(bool)', self.onThinPlateApply)
    thinPlateFormLayout.addWidget(self.thinPlateApply)
    self.widgets.append(self.thinPlateApply)

    self.parent.layout().addWidget(self.thinPlateCollapsibleButton)


  def destroy(self):
    """Clean up"""
    super(ThinPlatePlugin,self).destroy()

  def onLandmarkMoved(self,state):
    """Called when the user changes a landmark"""
    pass

  def onLandmarkEndMoving(self,state):
    """Called when the user changes a landmark"""
    self.onThinPlateApply()

  def onThinPlateApply(self):
    """Call this whenever thin plate needs to be calculated"""
    state = self.registationState()

    if state.fixed and state.moving and state.transformed:
      landmarks = state.logic.landmarksForVolumes((state.fixed, state.moving))
      self.performThinPlateRegistration(state, landmarks)

  def performThinPlateRegistration(self, state, landmarks):
    """Perform the thin plate transform using the vtkThinPlateSplineTransform class"""

    print('performing thin plate registration')
    state.transformed.SetAndObserveTransformNodeID(None)

    volumeNodes = (state.fixed, state.moving)
    fiducialNodes = (state.fixedFiducials,state.movingFiducials)
    points = state.logic.vtkPointsForVolumes( volumeNodes, fiducialNodes )

    # since this is a resample transform, source is the fixed (resampling target) space
    # and moving is the target space
    self.thinPlateTransform = vtk.vtkThinPlateSplineTransform()
    self.thinPlateTransform.SetBasisToR() # for 3D transform
    self.thinPlateTransform.SetSourceLandmarks(points[state.fixed])
    self.thinPlateTransform.SetTargetLandmarks(points[state.moving])
    self.thinPlateTransform.Update()
    state.logic.resliceThroughTransform(state.moving, self.thinPlateTransform, state.fixed, state.transformed)


# Add this plugin to the dictionary of available registrations.
# Since this module may be discovered before the Editor itself,
# create the list if it doesn't already exist.
try:
  slicer.modules.registrationPlugins
except AttributeError:
  slicer.modules.registrationPlugins = {}
slicer.modules.registrationPlugins['ThinPlate'] = ThinPlatePlugin
