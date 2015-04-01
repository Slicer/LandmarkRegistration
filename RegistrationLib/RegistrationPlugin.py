import importlib
import logging
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

class RegistrationPlugin(object):
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


  def create(self,registationState):
    """Call this method from your subclass to manage dynamic layout
    and widget deleting
    - registationState is a callable object that will give you an instance
    of a RegistrationState object that you can use to determine the current
    state of the fixed, moving, and other parameters of the parent gui.
    """
    self.registationState = registationState
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


def registerPlugin(destpackage, owner, name, globals, suffix='Plugin', verbose=True):
  """Add plugin identified by ``name`` to the dictionary of available
  ``owner`` plugins.

  Registered plugins are added into a dictionnary named `<owner>Plugins`
  available as ``slicer.modules.<owner>Plugins``.
  e.g ``slicer.modules.registrationPlugins``.

  .. 'note' The dictionnary name is created using lower cased ``owner`` name.
  .. 'note' The dictionnary is added to ``slicer.modules`` if needed.

  Plugin ``name`` can represent either a `modulename` or a `classname`:

  * `modulename`: This corresponds to the usual :class:`str` passed to the
  python ``import`` statement. e.g. ``[<pkgname1>.[<pkgname2>.[...]]]<modulename>``.

  * `classname`: A :class:`str` identifying the plugin `class` available in the
  caller scope.

  The function will first attempt to import ``name`` and look for a `classname`
  named `modulename` in the imported module. If it fails, the function will
  lookup for `classname` in the current `globals()`. Finally, if both fail a
  warning message will be logged.
  """

  className = name.split('.')[-1]
  pluginName = className.replace(suffix, '')
  pluginDictName = "%sPlugins" % owner.lower()

  # Since the plugin may be registered before the ``owner`` module is
  # instantiated, create the list if it doesn't already exist.
  if not hasattr(destpackage, pluginDictName):
    setattr(destpackage, pluginDictName, {})
  plugins = getattr(destpackage, pluginDictName)

  if pluginName in plugins:
    if verbose:
      logging.info("%s plugin '%s' already registered" % (owner, name))
    return

  # Try to lookup className
  new_module = globals
  try:
    plugins[pluginName] = new_module[className]
    return
  except (AttributeError, TypeError):
    pass

  # Try to import plugin and lookup className
  try:
    new_module = importlib.import_module(name)
    plugins[pluginName] = getattr(new_module, className)
  except (ImportError, AttributeError), details:
    logging.warning("%s: Failed to load '%s' plugin: %s" % (owner, name, details))


def registerRegistrationPlugin(name, globals=None, verbose=True):
  """Add plugin identified by ``name`` to the dictionary of available
  registration plugins ``slicer.modules.registrationPlugins``.

  .. seealso:: :func:`slicer.util.registerPlugin`
  """
  registerPlugin(slicer.modules, "Registration", name, globals, verbose=verbose)
