from pqWidget import *
from Visualization import *
from Landmarks import *
from RegistrationState import *
from RegistrationPlugin import *

for plugin in [
  'Affine',
  'ThinPlate',
  'LocalBRAINSFit',
  'LocalSimpleITK'
  ]:
  registerRegistrationPlugin('RegistrationLib.%sPlugin' % plugin)
