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


def registerPlugin(destpackage, consumer, name, globals, provider, suffix='Plugin', verbose=True):
  """Add plugin identified by ``name`` to the dictionary of available
  ``consumer`` plugins.

  :param destpackage:
    Name of the package that will host the plugin dictionary. E.g ``slicer.modules``.
  :type destpackage:
    :class:`basestring`

  :param consumer:
    Name of the plugin familly. E.g `DICOM`, `Editor` or `Registration`.
  :type consumer:
    :class:`basestring`

  :param name:
    Name of the plugin to register. can represent either a `modulename` or
    a `classname`:
      * `modulename`: This corresponds to the usual :class:`basestring` passed to the
      python ``import`` statement. e.g. ``[<pkgname1>.[<pkgname2>.[...]]]<modulename>``.

      * `classname`: A :class:`basestring` identifying the plugin `class`
      available in the caller scope identified by ``globals``.
  :type name:
    :class:`basestring`

  :param globals:
    Dictionary representing the scope in which a module classname should be
    looked up if it couldn't be imported.
  :type globals:
    :class:`dict`

  :param provider:
    Name of the module registering the plugin.
  :type provider:
    :class:`basestring`

  :param suffix:
    Represent the string that should be removed from the plugin ``name`` when
    adding an entry in the plugin dictionary.
  :type suffix:
    :class:`basestring`

  Registered plugins are added into a dictionary named `<consumer>Plugins`
  available as ``<destpackage>.<consumer>Plugins``.
  e.g ``slicer.modules.registrationPlugins``.

  .. 'note' The dictionary name is created using lower cased ``consumer`` name.
  .. 'note' The dictionary is added to ``<destpackage>`` if needed.

  The function will first attempt to lookup for `classname` is the ``globals``
  dictionnary. If it fails, the function will import ``name`` and look for a
  `classname` named `modulename` in the imported module. Finally, if both fail
  a warning message will be logged.
  """

  className = name.split('.')[-1]
  pluginName = className.replace(suffix, '')
  consumer = consumer.lower()
  pluginDictName = "%sPlugins" % consumer
  provider = provider if provider else owner

  # Since the plugin may be registered before the ``consumer`` module is
  # instantiated, create the list if it doesn't already exist.
  if not hasattr(destpackage, pluginDictName):
    setattr(destpackage, pluginDictName, {})
  plugins = getattr(destpackage, pluginDictName)

  if pluginName in plugins:
    if verbose:
      logging.info("%s: %s plugin '%s' already registered" % (provider, consumer, name))
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
    logging.warning("%s: Failed to load '%s' %s plugin: %s" % (provider, name, consumer, details))


def registerRegistrationPlugin(name, globals=None, provider="LandmarkRegistration", verbose=True):
  """Add plugin identified by ``name`` to the dictionary of available
  registration plugins ``slicer.modules.registrationPlugins``.

  .. seealso:: :func:`slicer.util.registerPlugin`
  """
  registerPlugin(slicer.modules, "Registration", name, globals, provider=provider, verbose=verbose)
