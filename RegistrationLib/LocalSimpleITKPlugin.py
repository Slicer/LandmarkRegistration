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

  def __init__(self,parent=None):
    super(LocalSimpleITKPlugin,self).__init__(parent)

  def create(self,registationState):
    """Make the plugin-specific user interface"""
    super(LocalSimpleITKPlugin,self).create(registationState)


    self.LocalSimpleITKMode = "Small"

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

    self.parent.layout().addWidget(self.LocalSimpleITKCollapsibleButton)


  def destroy(self):
    """Clean up"""
    super(LocalSimpleITKPlugin,self).destroy()

  def onLocalSimpleITKMode(self,mode):
    state = self.registationState()
    self.LocalSimpleITKMode = mode
    self.onLandmarkMoved(state)



# Add this plugin to the dictionary of available registrations.
# Since this module may be discovered before the Editor itself,
# create the list if it doesn't already exist.
try:
  slicer.modules.registrationPlugins
except AttributeError:
  slicer.modules.registrationPlugins = {}
slicer.modules.registrationPlugins['LocalSimpleITK'] = LocalSimpleITKPlugin

