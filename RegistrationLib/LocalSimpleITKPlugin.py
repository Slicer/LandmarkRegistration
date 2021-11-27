import time
import qt, ctk, slicer
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

class LocalSimpleITKPlugin(RegistrationPlugin):
  """ Plugin to perform local refinement of a single landmark
  """

  #
  # generic settings that can (should) be overridden by the subclass
  #

  # displayed for the user to select the registration
  name = "Local SimpleITK"
  tooltip = "Refines a single landmark locally using SimpleITK"

  # can be true or false
  # - True: landmarks are displayed and managed by LandmarkRegistration
  # - False: landmarks are hidden
  usesLandmarks = True

  # can be any non-negative number
  # - widget will be disabled until landmarks are defined
  landmarksNeededToEnable = 1

  # is this a registration plugin or a refinement plugin
  type = "Refinement"

  # used for reloading - every concrete class should include this
  sourceFile = __file__

  # To avoid the overhead of importing SimpleITK during application
  # startup, the import of SimpleITK is delayed until it is needed.
  sitk = None
  sitkUtils = None

  def __init__(self,parent=None):
    super().__init__(parent)

  def create(self,registrationState):
    """Make the plugin-specific user interface"""
    super().create(registrationState)

    # To avoid the overhead of importing SimpleITK during application
    # startup, the import of SimpleITK is delayed until it is needed.
    global sitk
    import SimpleITK as sitk
    global sitkUtils
    import sitkUtils
    print("LocalSimpleITKPlugin.create")

    self.LocalSimpleITKMode = "Small"
    self.VerboseMode = "Quiet"

    #
    # Local Refinment Pane - initially hidden
    # - interface options for linear registration
    #
    localSimpleITKCollapsibleButton = ctk.ctkCollapsibleButton()
    localSimpleITKCollapsibleButton.text = "Local SimpleITK"
    localSimpleITKFormLayout = qt.QFormLayout()
    localSimpleITKCollapsibleButton.setLayout(localSimpleITKFormLayout)
    self.widgets.append(localSimpleITKCollapsibleButton)

    buttonGroup = qt.QButtonGroup()
    self.widgets.append(buttonGroup)
    buttonLayout = qt.QVBoxLayout()
    localSimpleITKModeButtons = {}
    self.LocalSimpleITKModes = ("Small", "Large")
    for mode in self.LocalSimpleITKModes:
      localSimpleITKModeButtons[mode] = qt.QRadioButton()
      localSimpleITKModeButtons[mode].text = mode
      localSimpleITKModeButtons[mode].setToolTip( "Run the refinement in a %s local region." % mode.lower() )
      buttonLayout.addWidget(localSimpleITKModeButtons[mode])
      buttonGroup.addButton(localSimpleITKModeButtons[mode])
      self.widgets.append(localSimpleITKModeButtons[mode])
      localSimpleITKModeButtons[mode].connect('clicked()', lambda m=mode : self.onLocalSimpleITKMode(m))
    localSimpleITKModeButtons[self.LocalSimpleITKMode].checked = True
    localSimpleITKFormLayout.addRow("Local SimpleITK Mode ", buttonLayout)

    buttonGroup = qt.QButtonGroup()
    self.widgets.append(buttonGroup)
    buttonLayout = qt.QVBoxLayout()
    verboseModeButtons = {}
    self.VerboseModes = ("Quiet", "Verbose", "Full Verbose")
    for mode in self.VerboseModes:
      verboseModeButtons[mode] = qt.QRadioButton()
      verboseModeButtons[mode].text = mode
      verboseModeButtons[mode].setToolTip( "Run the refinement in %s mode." % mode.lower() )
      buttonLayout.addWidget(verboseModeButtons[mode])
      buttonGroup.addButton(verboseModeButtons[mode])
      self.widgets.append(verboseModeButtons[mode])
      verboseModeButtons[mode].connect('clicked()', lambda m=mode : self.onVerboseMode(m))
    verboseModeButtons[self.VerboseMode].checked = True
    localSimpleITKFormLayout.addRow("Verbose Mode ", buttonLayout)

    self.parent.layout().addWidget(localSimpleITKCollapsibleButton)


  def destroy(self):
    """Clean up"""
    super().destroy()

  def onLocalSimpleITKMode(self,mode):
    self.LocalSimpleITKMode = mode

  def onVerboseMode(self,mode):
    self.VerboseMode = mode

  def refineLandmark(self, state):
    """Refine the specified landmark"""
    # Refine landmark, or if none, do nothing
    #     Crop images around the point
    #     Affine registration of the cropped images
    #     Transform the point using the transformation
    #
    # No need to take into account the current transformation because landmarks are in World RAS
    timing = False
    if self.VerboseMode == "Verbose":
      timing = True

    if state.fixed == None or state.moving == None or state.fixedPoints == None or  state.movingPoints == None or state.currentLandmarkName == None:
      print("Cannot refine landmarks. Images or landmarks not selected.")
      return

    print(("Refining landmark " + state.currentLandmarkName) + " using " + self.name)

    start = time.time()
    if timing: loadStart = start

    volumes = (state.fixed, state.moving)
    (fixedVolume, movingVolume) = volumes

    fixedImage = sitk.ReadImage(sitkUtils.GetSlicerITKReadWriteAddress(fixedVolume.GetName()) )
    movingImage = sitk.ReadImage(sitkUtils.GetSlicerITKReadWriteAddress(movingVolume.GetName()) )

    if timing: print('Time for loading was ' + str(time.time() - loadStart) + ' seconds')

    landmarks = state.logic.landmarksForVolumes(volumes)

    (fixedPoint, movingPoint) = landmarks[state.currentLandmarkName]

    (fixedList,fixedIndex) = fixedPoint
    (movingList, movingIndex) = movingPoint

    fixedPoint = fixedList.GetNthControlPointPosition(fixedIndex)
    movingPoint = movingList.GetNthControlPointPosition(movingIndex)

    # HACK transform from RAS to LPS
    fixedPoint = [-fixedPoint[0], -fixedPoint[1], fixedPoint[2]]
    movingPoint = [-movingPoint[0], -movingPoint[1], movingPoint[2]]

    # NOTE: SimpleITK index always starts at 0
    import numpy as np

    # Minimal image size required by the RecursiveGaussianImageFilter which is used by
    # the registration framework.
    minimalROISize = 4

    # define an roi for the fixed point, intersect the ROI defined by the fixedRadius (centered on the fixedPoint)
    # and the image.
    if timing: roiStart = time.time()
    fixedRadius = 30
    fixedPointIndex = np.array(fixedImage.TransformPhysicalPointToIndex(fixedPoint))
    fixedMinIndexes = np.maximum(fixedPointIndex-fixedRadius, [0]*fixedImage.GetDimension())
    fixedMaxIndexes = np.minimum(fixedPointIndex+fixedRadius, fixedImage.GetSize())
    fixedROISize = fixedMaxIndexes - fixedMinIndexes
    # minimal acceptable ROI size required by registration framework.
    if not all(fixedROISize > minimalROISize):
        import sys
        sys.stderr.write(f"Fixed landmark {state.currentLandmarkName} is too close to the image border, cannot register!\n")
        return
    if self.VerboseMode == "Full Verbose":  print("Fixed ROI: ",fixedMinIndexes.tolist(), fixedROISize.tolist())
    if timing: roiEnd = time.time()

    # crop the fixed
    if timing: cropStart = time.time()
    croppedFixedImage = sitk.RegionOfInterest( fixedImage, fixedROISize.tolist(), fixedMinIndexes.tolist())
    croppedFixedImage = sitk.Cast(croppedFixedImage, sitk.sitkFloat32)
    if timing: cropEnd = time.time()

    # define an roi for the moving point, intersect the ROI defined by the movingRadius (centered on the movingPoint)
    # and the image.
    if timing: roi2Start = time.time()
    if self.LocalSimpleITKMode == "Small":
      movingRadius = 45
    else:
      movingRadius = 60
    movingPointIndex = np.array(movingImage.TransformPhysicalPointToIndex(movingPoint))
    movingMinIndexes = np.maximum(movingPointIndex-movingRadius, [0]*movingImage.GetDimension())
    movingMaxIndexes = np.minimum(movingPointIndex+movingRadius, movingImage.GetSize())
    movingROISize = movingMaxIndexes - movingMinIndexes
    # minimal acceptable ROI size required by registration framework.
    if not all(movingROISize > minimalROISize):
        import sys
        sys.stderr.write(f"Moving landmark {state.currentLandmarkName} is too close to the image border, cannot register!\n")
        return
    if self.VerboseMode == "Full Verbose": print("Moving ROI: ",movingMinIndexes.tolist(), movingROISize.tolist())
    if timing: roi2End = time.time()

    if timing: crop2Start = time.time()
    croppedMovingImage = sitk.RegionOfInterest( movingImage, movingROISize.tolist(), movingMinIndexes.tolist())
    croppedMovingImage = sitk.Cast(croppedMovingImage, sitk.sitkFloat32)
    if timing: crop2End = time.time()

    if timing: print('Time to set up fixed ROI was ' + str(roiEnd - roiStart) + ' seconds')
    if timing: print('Time to set up moving ROI was ' + str(roi2End - roi2Start) + ' seconds')
    if timing: print('Time to crop fixed volume ' + str(cropEnd - cropStart) + ' seconds')
    if timing: print('Time to crop moving volume ' + str(crop2End - crop2Start) + ' seconds')

    # initialize the registration
    if timing: initTransformStart = time.time()
    tx = sitk.VersorRigid3DTransform()
    tx.SetCenter(fixedPoint)
    tx.SetTranslation(np.array(movingPoint) - np.array(fixedPoint))
    if timing: initTransformEnd = time.time()
    if timing: print('Time to initialize transformation was ' + str(initTransformEnd - initTransformStart) + ' seconds')

    # define the registration
    R = sitk.ImageRegistrationMethod()
    R.SetMetricAsMattesMutualInformation(numberOfHistogramBins=50)
    R.SetMetricSamplingPercentage(0.2)
    R.SetMetricSamplingStrategy(sitk.ImageRegistrationMethod.RANDOM)
    R.SetOptimizerAsRegularStepGradientDescent(learningRate=1,
                                               minStep=0.1,
                                               relaxationFactor=0.5,
                                               numberOfIterations=250)
    R.SetOptimizerScalesFromJacobian() # Use this for versor based transforms
    R.SetShrinkFactorsPerLevel([1])
    R.SetSmoothingSigmasPerLevel([1])
    R.SetInitialTransform(tx)
    R.SetInterpolator(sitk.sitkLinear)
    #R.SetNumberOfThreads(1)

    # setup an observer
    def command_iteration(method) :
      print("{:3} = {:10.5f} : {}".format(method.GetOptimizerIteration(),
                                          method.GetMetricValue(),
                                          method.GetOptimizerPosition()))
    if self.VerboseMode == "Full Verbose":
      R.AddCommand( sitk.sitkIterationEvent, lambda: command_iteration(R) )


    # run the registration
    if timing: regStart = time.time()

    outTx = R.Execute(croppedFixedImage, croppedMovingImage)

    if self.VerboseMode == "Full Verbose":
      print("-------")
      print(outTx)
      print(f"Optimizer stop condition: {R.GetOptimizerStopConditionDescription()}")
      print(f" Iteration: {R.GetOptimizerIteration()}")
      print(f" Metric value: {R.GetMetricValue()}")


    if timing: regEnd = time.time()
    if timing: print('Time for local registration was ' + str(regEnd - regStart) + ' seconds')

    # apply the local transform to the landmark
    #print transform

    if timing: resultStart = time.time()
    #outTx.SetInverse()
    updatedPoint = outTx.TransformPoint(fixedPoint)

    # HACK transform from LPS to RAS
    updatedPoint = [-updatedPoint[0], -updatedPoint[1], updatedPoint[2]]
    movingList.SetNthControlPointPosition(movingIndex, updatedPoint[0], updatedPoint[1], updatedPoint[2])
    if timing: resultEnd = time.time()
    if timing: print('Time for transforming landmark was ' + str(resultEnd - resultStart) + ' seconds')

    end = time.time()
    print('Refined landmark ' + state.currentLandmarkName + ' in ' + str(end - start) + ' seconds')



# Add this plugin to the dictionary of available registrations.
# Since this module may be discovered before the Editor itself,
# create the list if it doesn't already exist.
try:
  slicer.modules.registrationPlugins
except AttributeError:
  slicer.modules.registrationPlugins = {}
slicer.modules.registrationPlugins['LocalSimpleITK'] = LocalSimpleITKPlugin

