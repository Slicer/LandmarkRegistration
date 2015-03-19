import os
import time
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

class LocalBRAINSFitPlugin(RegistrationLib.RegistrationPlugin):
  """ Plugin to perform local refinement of a single landmark
  """

  #
  # generic settings that can (should) be overridden by the subclass
  #

  # displayed for the user to select the registration
  name = "Local BRAINSFit"
  tooltip = "Refines a single landmark locally using BRAINSFit"

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

  def __init__(self,parent=None):
    super(LocalBRAINSFitPlugin,self).__init__(parent)

  def create(self,registationState):
    """Make the plugin-specific user interface"""
    super(LocalBRAINSFitPlugin,self).create(registationState)


    self.LocalBRAINSFitMode = "Small"
    self.VerboseMode = "Quiet"

    #
    # Local Refinment Pane - initially hidden
    # - interface options for linear registration
    #
    self.LocalBRAINSFitCollapsibleButton = ctk.ctkCollapsibleButton()
    self.LocalBRAINSFitCollapsibleButton.text = "Local BRAINSFit"
    LocalBRAINSFitFormLayout = qt.QFormLayout()
    self.LocalBRAINSFitCollapsibleButton.setLayout(LocalBRAINSFitFormLayout)
    self.widgets.append(self.LocalBRAINSFitCollapsibleButton)

    buttonLayout = qt.QVBoxLayout()
    self.LocalBRAINSFitModeButtons = {}
    self.LocalBRAINSFitModes = ("Small", "Large")
    for mode in self.LocalBRAINSFitModes:
      self.LocalBRAINSFitModeButtons[mode] = qt.QRadioButton()
      self.LocalBRAINSFitModeButtons[mode].text = mode
      self.LocalBRAINSFitModeButtons[mode].setToolTip( "Run the refinement in a %s local region." % mode.lower() )
      buttonLayout.addWidget(self.LocalBRAINSFitModeButtons[mode])
      self.widgets.append(self.LocalBRAINSFitModeButtons[mode])
      self.LocalBRAINSFitModeButtons[mode].connect('clicked()', lambda m=mode : self.onLocalBRAINSFitMode(m))
    self.LocalBRAINSFitModeButtons[self.LocalBRAINSFitMode].checked = True
    LocalBRAINSFitFormLayout.addRow("Local BRAINSFit Mode ", buttonLayout)

    buttonLayout = qt.QVBoxLayout()
    self.VerboseModeButtons = {}
    self.VerboseModes = ("Quiet", "Verbose")
    for mode in self.VerboseModes:
      self.VerboseModeButtons[mode] = qt.QRadioButton()
      self.VerboseModeButtons[mode].text = mode
      self.VerboseModeButtons[mode].setToolTip( "Run the refinement in %s mode." % mode.lower() )
      buttonLayout.addWidget(self.VerboseModeButtons[mode])
      self.widgets.append(self.VerboseModeButtons[mode])
      self.VerboseModeButtons[mode].connect('clicked()', lambda m=mode : self.onVerboseMode(m))
    self.VerboseModeButtons[self.VerboseMode].checked = True
    LocalBRAINSFitFormLayout.addRow("Verbose Mode ", buttonLayout)


    self.parent.layout().addWidget(self.LocalBRAINSFitCollapsibleButton)


  def destroy(self):
    """Clean up"""
    super(LocalBRAINSFitPlugin,self).destroy()


  def onLocalBRAINSFitMode(self,mode):
    self.LocalBRAINSFitMode = mode

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

    volumes = (state.fixed, state.moving)
    (fixedVolume, movingVolume) = volumes

    slicer.mrmlScene.StartState(slicer.mrmlScene.BatchProcessState)
    landmarks = state.logic.landmarksForVolumes(volumes)

    cvpn = slicer.vtkMRMLCropVolumeParametersNode()
    cvpn.SetInterpolationMode(1)
    cvpn.SetVoxelBased(1)
    fixedPoint = [0,]*3
    movingPoint = [0,]*3

    (fixedFiducial, movingFiducial) = landmarks[state.currentLandmarkName]

    (fixedList,fixedIndex) = fixedFiducial
    (movingList, movingIndex) = movingFiducial

    # define an roi for the fixed
    if timing: roiStart = time.time()
    roiFixed = slicer.vtkMRMLAnnotationROINode()
    slicer.mrmlScene.AddNode(roiFixed)

    fixedList.GetNthFiducialPosition(fixedIndex,fixedPoint)
    roiFixed.SetDisplayVisibility(0)
    roiFixed.SelectableOff()
    roiFixed.SetXYZ(fixedPoint)
    roiFixed.SetRadiusXYZ(30, 30, 30)

    # crop the fixed. note we hide the display node temporarily to avoid the automated
    # window level calculation on temporary nodes created by cloning
    cvpn.SetROINodeID( roiFixed.GetID() )
    cvpn.SetInputVolumeNodeID( fixedVolume.GetID() )
    fixedDisplayNode = fixedVolume.GetDisplayNode()
    fixedVolume.SetAndObserveDisplayNodeID('This is not a valid DisplayNode ID')
    if timing: roiEnd = time.time()
    if timing: cropStart = time.time()
    state.logic.cropLogic.Apply( cvpn )
    if timing: cropEnd = time.time()
    croppedFixedVolume = slicer.mrmlScene.GetNodeByID( cvpn.GetOutputVolumeNodeID() )
    fixedVolume.SetAndObserveDisplayNodeID(fixedDisplayNode.GetID())

    # define an roi for the moving
    if timing: roi2Start = time.time()
    roiMoving = slicer.vtkMRMLAnnotationROINode()
    slicer.mrmlScene.AddNode(roiMoving)

    movingList.GetNthFiducialPosition(movingIndex,movingPoint)
    roiMoving.SetDisplayVisibility(0)
    roiMoving.SelectableOff()
    roiMoving.SetXYZ(movingPoint)
    if self.LocalBRAINSFitMode == "Small":
      roiMoving.SetRadiusXYZ(45, 45, 45)
    else:
      roiMoving.SetRadiusXYZ(60, 60, 60)

    # crop the moving. note we hide the display node temporarily to avoid the automated
    # window level calculation on temporary nodes created by cloning
    cvpn.SetROINodeID( roiMoving.GetID() )
    cvpn.SetInputVolumeNodeID( movingVolume.GetID() )
    movingDisplayNode = movingVolume.GetDisplayNode()
    movingVolume.SetAndObserveDisplayNodeID('This is not a valid DisplayNode ID')
    if timing: roi2End = time.time()
    if timing: crop2Start = time.time()
    state.logic.cropLogic.Apply( cvpn )
    if timing: crop2End = time.time()
    croppedMovingVolume = slicer.mrmlScene.GetNodeByID( cvpn.GetOutputVolumeNodeID() )
    movingVolume.SetAndObserveDisplayNodeID(movingDisplayNode.GetID())

    if timing: print 'Time to set up fixed ROI was ' + str(roiEnd - roiStart) + ' seconds'
    if timing: print 'Time to set up moving ROI was ' + str(roi2End - roi2Start) + ' seconds'
    if timing: print 'Time to crop fixed volume ' + str(cropEnd - cropStart) + ' seconds'
    if timing: print 'Time to crop moving volume ' + str(crop2End - crop2Start) + ' seconds'

    #
    transform = slicer.vtkMRMLLinearTransformNode()
    slicer.mrmlScene.AddNode(transform)
    matrix = vtk.vtkMatrix4x4()

    # define the registration parameters
    minPixelSpacing = min(croppedFixedVolume.GetSpacing())
    parameters = {}
    parameters['fixedVolume'] = croppedFixedVolume.GetID()
    parameters['movingVolume'] = croppedMovingVolume.GetID()
    parameters['linearTransform'] = transform.GetID()
    parameters['useRigid'] = True
    parameters['initializeTransformMode'] = 'useGeometryAlign';
    parameters['samplingPercentage'] = 0.2
    parameters['minimumStepLength'] = 0.1 * minPixelSpacing
    parameters['maximumStepLength'] = minPixelSpacing

    # run the registration
    if timing: regStart = time.time()
    slicer.cli.run(slicer.modules.brainsfit, None, parameters, wait_for_completion=True)
    if timing: regEnd = time.time()
    if timing: print 'Time for local registration ' + str(regEnd - regStart) + ' seconds'

    # apply the local transform to the landmark
    #print transform
    if timing: resultStart = time.time()
    transform.GetMatrixTransformToWorld(matrix)
    matrix.Invert()
    tp = [0,]*4
    tp = matrix.MultiplyPoint(fixedPoint + [1,])
    #print fixedPoint, movingPoint, tp[:3]

    movingList.SetNthFiducialPosition(movingIndex, tp[0], tp[1], tp[2])
    if timing: resultEnd = time.time()
    if timing: print 'Time for transforming landmark was ' + str(resultEnd - resultStart) + ' seconds'

    # clean up cropped volmes, need to reset the foreground/background display before we delete it
    if timing: cleanUpStart = time.time()
    slicer.mrmlScene.RemoveNode(croppedFixedVolume)
    slicer.mrmlScene.RemoveNode(croppedMovingVolume)
    slicer.mrmlScene.RemoveNode(roiFixed)
    slicer.mrmlScene.RemoveNode(roiMoving)
    slicer.mrmlScene.RemoveNode(transform)
    roiFixed = None
    roiMoving = None
    transform = None
    matrix = None
    if timing: cleanUpEnd = time.time()
    if timing: print 'Cleanup took ' + str(cleanUpEnd - cleanUpStart) + ' seconds'

    end = time.time()
    print 'Refined landmark ' + state.currentLandmarkName + ' in ' + str(end - start) + ' seconds'

    slicer.mrmlScene.EndState(slicer.mrmlScene.BatchProcessState)



# Add this plugin to the dictionary of available registrations.
# Since this module may be discovered before the Editor itself,
# create the list if it doesn't already exist.
try:
  slicer.modules.registrationPlugins
except AttributeError:
  slicer.modules.registrationPlugins = {}
slicer.modules.registrationPlugins['LocalBRAINSFit'] = LocalBRAINSFitPlugin

