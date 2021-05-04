import qt
import slicer


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

class RegistrationPlugin:
  """ Base class for Registration plugins
  """

  #
  # generic settings that can (should) be overridden by the subclass
  #

  # displayed for the user to select the registration
  name = "Generic Registration"
  tooltip = "No additional information available"

  # can be true or false
  # - True: landmarks are displayed and managed by LandmarkRegistration
  # - False: landmarks are hidden
  usesLandmarks = True

  # can be any non-negative number
  # - widget will be disabled until landmarks are defined
  landmarksNeededToEnable = 1

  # is this a registration plugin or a refinement plugin
  type = "Registration"

  # used for reloading - every concrete class should include this
  sourceFile = __file__

  def __init__(self,parent=None):

    #
    # state variables for all plugins and subclasses
    #
    self.parent = parent
    self.observerTags = []
    self.widgets = []


  def create(self,registrationState):
    """Call this method from your subclass to manage dynamic layout
    and widget deleting
    - registrationState is a callable object that will give you an instance
    of a RegistrationState object that you can use to determine the current
    state of the fixed, moving, and other parameters of the parent gui.
    """
    self.registrationState = registrationState
    if not self.parent:
      self.parent = slicer.qMRMLWidget()
      self.parent.setLayout(qt.QVBoxLayout())
      self.parent.setMRMLScene(slicer.mrmlScene)
      self.parent.show()
    self.frame = qt.QFrame(self.parent)
    self.frame.objectName = 'EditOptionsFrame'
    self.frame.setLayout(qt.QVBoxLayout())
    self.parent.layout().addWidget(self.frame)
    self.widgets.append(self.frame)

  def destroy(self):
    """Call this method from your subclass to manage dynamic layout
    and widget deleting"""
    for w in self.widgets:
      if w.isWidgetType():
        self.parent.layout().removeWidget(w)
      w.deleteLater()
      w.setParent(None)
    self.widgets = []

  def onLandmarkMoved(self,state):
    """Called when the user changes a landmark"""
    pass

  def onLandmarkEndMoving(self,state):
    """Called when the user changes a landmark"""
    pass
