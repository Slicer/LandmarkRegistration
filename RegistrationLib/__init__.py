from .pqWidget import *
from .Visualization import *
from .Landmarks import *
from .RegistrationState import *
from .RegistrationPlugin import *

for plugin in [
  'Affine',
  'ThinPlate',
  'LocalBRAINSFit',
  'LocalSimpleITK'
  ]:
  try:
    __import__('RegistrationLib.%sPlugin' % plugin)
  except ImportError as details:
    import logging
    logging.warning(f"Registration: Failed to import '{plugin}' plugin: {details}")
