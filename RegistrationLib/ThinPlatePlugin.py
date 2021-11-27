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

class ThinPlatePlugin(RegistrationPlugin):
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
    super().__init__(parent)

    self.thinPlateTransform = None

  def create(self,registrationState):
    """Make the plugin-specific user interface"""
    super().create(registrationState)
    #
    # Thin Plate Spline Registration Pane
    #
    thinPlateCollapsibleButton = ctk.ctkCollapsibleButton()
    thinPlateCollapsibleButton.text = "Thin Plate Spline Registration"
    thinPlateFormLayout = qt.QFormLayout()
    thinPlateCollapsibleButton.setLayout(thinPlateFormLayout)
    self.widgets.append(thinPlateCollapsibleButton)

    self.hotUpdateButton = qt.QCheckBox("Hot Update")
    thinPlateFormLayout.addWidget(self.hotUpdateButton)
    self.widgets.append(self.hotUpdateButton)

    exportGridButton = qt.QPushButton("Export to Grid Transform")
    exportGridButton.toolTip = "To save this transform or use it in other Slicer modules you can export the current Thin Plate transform to a Grid Transform."
    thinPlateFormLayout.addWidget(exportGridButton)
    exportGridButton.connect("clicked()",self.onExportGrid)
    self.widgets.append(exportGridButton)

    self.parent.layout().addWidget(thinPlateCollapsibleButton)

  def destroy(self):
    """Clean up"""
    super().destroy()

  def onExportGrid(self):
    """Converts the current thin plate transform to a grid"""
    state = self.registrationState()

    # since the transform is ras-to-ras, we find the extreme points
    # in ras space of the fixed (target) volume and fix the unoriented
    # box around it.  Sample the grid transform at the resolution of
    # the fixed volume, which may be a bit overkill but it should aways
    # work without too much loss.
    rasBounds = [0,]*6
    state.fixed.GetRASBounds(rasBounds)
    from math import floor, ceil
    origin = list(map(int,map(floor,rasBounds[::2])))
    maxes = list(map(int,map(ceil,rasBounds[1::2])))
    boundSize = [m - o for m,o in zip(maxes,origin) ]
    spacing = state.fixed.GetSpacing()
    spacing = [max(spacing)*5]*3
    samples = [ceil(int(b / s)) for b,s in zip(boundSize,spacing)]
    extent = [0,]*6
    extent[::2] = [0,]*3
    extent[1::2] = samples
    extent = list(map(int,extent))

    toGrid = vtk.vtkTransformToGrid()
    toGrid.SetGridOrigin(origin)
    toGrid.SetGridSpacing(spacing)
    toGrid.SetGridExtent(extent)
    toGrid.SetInput(state.transform.GetTransformFromParent())
    toGrid.Update()

    gridTransform = slicer.vtkOrientedGridTransform()
    gridTransform.SetDisplacementGridData(toGrid.GetOutput())
    gridNode = slicer.vtkMRMLGridTransformNode()
    gridNode.SetAndObserveTransformFromParent(gridTransform)
    gridNode.SetName(state.transform.GetName()+"-grid")
    slicer.mrmlScene.AddNode(gridNode)

  def onLandmarkMoved(self,state):
    """Called when the user changes a landmark"""
    if self.hotUpdateButton.checked:
      self.onThinPlateApply()

  def onLandmarkEndMoving(self,state):
    """Called when the user changes a landmark"""
    self.onThinPlateApply()

  def onThinPlateApply(self):
    """Call this whenever thin plate needs to be calculated"""
    state = self.registrationState()

    if state.fixed and state.moving and state.transformed:
      landmarks = state.logic.landmarksForVolumes((state.fixed, state.moving))
      self.performThinPlateRegistration(state, landmarks)

  def performThinPlateRegistration(self, state, landmarks):
    """Perform the thin plate transform using the vtkThinPlateSplineTransform class"""

    volumeNodes = (state.fixed, state.moving)
    pointListNodes = (state.fixedPoints,state.movingPoints)
    points = state.logic.vtkPointsForVolumes( volumeNodes, pointListNodes )

    # since this is a resample transform, source is the fixed (resampling target) space
    # and moving is the target space
    if not self.thinPlateTransform:
      self.thinPlateTransform = vtk.vtkThinPlateSplineTransform()
    self.thinPlateTransform.SetBasisToR() # for 3D transform
    self.thinPlateTransform.SetSourceLandmarks(points[state.moving])
    self.thinPlateTransform.SetTargetLandmarks(points[state.fixed])
    self.thinPlateTransform.Update()

    if points[state.moving].GetNumberOfPoints() != points[state.fixed].GetNumberOfPoints():
      raise hell

    state.transform.SetAndObserveTransformToParent(self.thinPlateTransform)


# Add this plugin to the dictionary of available registrations.
# Since this module may be discovered before the Editor itself,
# create the list if it doesn't already exist.
try:
  slicer.modules.registrationPlugins
except AttributeError:
  slicer.modules.registrationPlugins = {}
slicer.modules.registrationPlugins['ThinPlate'] = ThinPlatePlugin
