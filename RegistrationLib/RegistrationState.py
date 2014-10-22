
#
# RegistrationState
#

class RegistrationState(object):
  """ Holds parameters of registration.
  An instance of this class is passed to virtual methods
  """

  # MRML volume nodes
  fixed = None
  moving = None
  transformed = None

  # MRML Markup Fiducial Nodes
  fixedFiducials = None
  movingFiducials = None
  transformedFiducials = None

  # MRML Linear Transform Node
  transform = None

