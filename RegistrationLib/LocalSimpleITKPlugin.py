import os
import time
from contextlib import contextmanager
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

class LocalSimpleITKPlugin(RegistrationLib.RegistrationPlugin):
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
    super(LocalSimpleITKPlugin,self).__init__(parent)

  def create(self,registationState):
    """Make the plugin-specific user interface"""
    super(LocalSimpleITKPlugin,self).create(registationState)

    # To avoid the overhead of importing SimpleITK during application
    # startup, the import of SimpleITK is delayed until it is needed.
    global sitk
    import SimpleITK as sitk
    global sitkUtils
    import sitkUtils

    self.LocalSimpleITKMode = "Small"
    self.VerboseMode = "Quiet"

    #
    # Local Refinment Pane - initially hidden
    # - interface options for linear registration
    #
    self.LocalSimpleITKCollapsibleButton = ctk.ctkCollapsibleButton()
    self.LocalSimpleITKCollapsibleButton.text = "Local SimpleITK"
    LocalSimpleITKFormLayout = qt.QFormLayout()
    self.LocalSimpleITKCollapsibleButton.setLayout(LocalSimpleITKFormLayout)
    self.widgets.append(self.LocalSimpleITKCollapsibleButton)

    buttonLayout = qt.QVBoxLayout()
    self.LocalSimpleITKModeButtons = {}
    self.LocalSimpleITKModes = ("Small", "Large")
    for mode in self.LocalSimpleITKModes:
      self.LocalSimpleITKModeButtons[mode] = qt.QRadioButton()
      self.LocalSimpleITKModeButtons[mode].text = mode
      self.LocalSimpleITKModeButtons[mode].setToolTip( "Run the refinement in a %s local region." % mode.lower() )
      buttonLayout.addWidget(self.LocalSimpleITKModeButtons[mode])
      self.widgets.append(self.LocalSimpleITKModeButtons[mode])
      self.LocalSimpleITKModeButtons[mode].connect('clicked()', lambda m=mode : self.onLocalSimpleITKMode(m))
    self.LocalSimpleITKModeButtons[self.LocalSimpleITKMode].checked = True
    LocalSimpleITKFormLayout.addRow("Local SimpleITK Mode ", buttonLayout)

    buttonLayout = qt.QVBoxLayout()
    self.VerboseModeButtons = {}
    self.VerboseModes = ("Quiet", "Verbose", "Full Verbose")
    for mode in self.VerboseModes:
      self.VerboseModeButtons[mode] = qt.QRadioButton()
      self.VerboseModeButtons[mode].text = mode
      self.VerboseModeButtons[mode].setToolTip( "Run the refinement in %s mode." % mode.lower() )
      buttonLayout.addWidget(self.VerboseModeButtons[mode])
      self.widgets.append(self.VerboseModeButtons[mode])
      self.VerboseModeButtons[mode].connect('clicked()', lambda m=mode : self.onVerboseMode(m))
    self.VerboseModeButtons[self.VerboseMode].checked = True
    LocalSimpleITKFormLayout.addRow("Verbose Mode ", buttonLayout)

    self.parent.layout().addWidget(self.LocalSimpleITKCollapsibleButton)


  def destroy(self):
    """Clean up"""
    super(LocalSimpleITKPlugin,self).destroy()

  def onLocalSimpleITKMode(self,mode):
    self.LocalSimpleITKMode = mode

  def onVerboseMode(self,mode):
    self.VerboseMode = mode

  def refineLandmark(self, state):
    """Refine the specified landmark"""
    # Refine landmark, or if none, do nothing
    #     Crop images around the fiducial
    #     Affine registration of the cropped images
    #     Transform the fiducial using the transformation
    #
    # No need to take into account the current transformation because landmarks are in World RAS
    timing = False
    if self.VerboseMode == "Verbose":
      timing = True

    if state.fixed == None or state.moving == None or state.fixedFiducials == None or  state.movingFiducials == None or state.currentLandmarkName == None:
      print "Cannot refine landmarks. Images or landmarks not selected."
      return

    print ("Refining landmark " + state.currentLandmarkName) + " using " + self.name

    start = time.time()
    if timing: loadStart = start

    volumes = (state.fixed, state.moving)
    (fixedVolume, movingVolume) = volumes

    fixedImage = sitk.ReadImage(sitkUtils.GetSlicerITKReadWriteAddress(fixedVolume.GetName()) )
    movingImage = sitk.ReadImage(sitkUtils.GetSlicerITKReadWriteAddress(movingVolume.GetName()) )

    if timing: print 'Time for loading was ' + str(time.time() - loadStart) + ' seconds'

    landmarks = state.logic.landmarksForVolumes(volumes)

    (fixedFiducial, movingFiducial) = landmarks[state.currentLandmarkName]

    (fixedList,fixedIndex) = fixedFiducial
    (movingList, movingIndex) = movingFiducial

    fixedPoint = [0,]*3
    movingPoint = [0,]*3

    fixedList.GetNthFiducialPosition(fixedIndex,fixedPoint)
    movingList.GetNthFiducialPosition(movingIndex,movingPoint)

    # HACK transform from RAS to LPS
    fixedPoint = [-fixedPoint[0], -fixedPoint[1], fixedPoint[2]]
    movingPoint = [-movingPoint[0], -movingPoint[1], movingPoint[2]]

    # NOTE: SimpleITK index always starts at 0

    # define an roi for the fixed
    if timing: roiStart = time.time()
    fixedRadius = 30
    fixedROISize = [0,]*3
    fixedROIIndex = [0,]*3
    fixedROIIndex = list(fixedImage.TransformPhysicalPointToIndex(fixedPoint))
    for i in range(3):
      if fixedROIIndex[i] < 0 or fixedROIIndex[i] > fixedImage.GetSize()[i]-1:
        import sys
        sys.stderr.write("Fixed landmark {0} in not with in fixed image!\n".format(landmarkName))
        return
      radius = min(fixedRadius, fixedROIIndex[i], fixedImage.GetSize()[i]-fixedROIIndex[i]-1)
      fixedROISize[i] = radius*2+1
      fixedROIIndex[i] -= radius
    if self.VerboseMode == "Full Verbose":  print "Fixed ROI: ",fixedROIIndex, fixedROISize
    if timing: roiEnd = time.time()

    # crop the fixed
    if timing: cropStart = time.time()
    croppedFixedImage = sitk.RegionOfInterest( fixedImage, fixedROISize, fixedROIIndex)
    croppedFixedImage = sitk.Cast(croppedFixedImage, sitk.sitkFloat32)
    if timing: cropEnd = time.time()

    # define an roi for the moving
    if timing: roi2Start = time.time()
    if self.LocalSimpleITKMode == "Small":
      movingRadius = 45
    else:
      movingRadius = 60
    movingROISize = [0,]*3
    movingROIIndex = [0,]*3
    movingROIIndex = list(movingImage.TransformPhysicalPointToIndex(movingPoint))
    for i in range(3):
      if movingROIIndex[i] < 0 or movingROIIndex[i] > movingImage.GetSize()[i]-1:
        import sys
        sys.stderr.write("Moving landmark {0} in not with in moving image!\n".format(landmarkName))
        return
      radius = min(movingRadius, movingROIIndex[i], movingImage.GetSize()[i]-movingROIIndex[i]-1)
      movingROISize[i] = radius*2+1
      movingROIIndex[i] -= radius
    if self.VerboseMode == "Full Verbose": print "Moving ROI: ",movingROIIndex, movingROISize
    if timing: roi2End = time.time()

    if timing: crop2Start = time.time()
    croppedMovingImage = sitk.RegionOfInterest( movingImage, movingROISize, movingROIIndex)
    croppedMovingImage = sitk.Cast(croppedMovingImage, sitk.sitkFloat32)
    if timing: crop2End = time.time()

    if timing: print 'Time to set up fixed ROI was ' + str(roiEnd - roiStart) + ' seconds'
    if timing: print 'Time to set up moving ROI was ' + str(roi2End - roi2Start) + ' seconds'
    if timing: print 'Time to crop fixed volume ' + str(cropEnd - cropStart) + ' seconds'
    if timing: print 'Time to crop moving volume ' + str(crop2End - crop2Start) + ' seconds'

    # initialize the registration
    if timing: initTransformStart = time.time()
    tx = sitk.CenteredTransformInitializer(croppedFixedImage, croppedMovingImage, sitk.VersorRigid3DTransform(), sitk.CenteredTransformInitializerFilter.GEOMETRY)
    if timing: initTransformEnd = time.time()
    if timing: print 'Time to initialize transformation was ' + str(initTransformEnd - initTransformStart) + ' seconds'

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
      print("{0:3} = {1:10.5f} : {2}".format(method.GetOptimizerIteration(),
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
      print("Optimizer stop condition: {0}".format(R.GetOptimizerStopConditionDescription()))
      print(" Iteration: {0}".format(R.GetOptimizerIteration()))
      print(" Metric value: {0}".format(R.GetMetricValue()))


    if timing: regEnd = time.time()
    if timing: print 'Time for local registration was ' + str(regEnd - regStart) + ' seconds'

    # apply the local transform to the landmark
    #print transform

    if timing: resultStart = time.time()
    #outTx.SetInverse()
    updatedPoint = outTx.TransformPoint(fixedPoint)

    # HACK transform from LPS to RAS
    updatedPoint = [-updatedPoint[0], -updatedPoint[1], updatedPoint[2]]
    movingList.SetNthFiducialPosition(movingIndex, updatedPoint[0], updatedPoint[1], updatedPoint[2])
    if timing: resultEnd = time.time()
    if timing: print 'Time for transforming landmark was ' + str(resultEnd - resultStart) + ' seconds'

    end = time.time()
    print 'Refined landmark ' + state.currentLandmarkName + ' in ' + str(end - start) + ' seconds'



# Add this plugin to the dictionary of available registrations.
# Since this module may be discovered before the Editor itself,
# create the list if it doesn't already exist.
try:
  slicer.modules.registrationPlugins
except AttributeError:
  slicer.modules.registrationPlugins = {}
slicer.modules.registrationPlugins['LocalSimpleITK'] = LocalSimpleITKPlugin

