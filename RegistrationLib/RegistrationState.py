#
# RegistrationState
#

class RegistrationState:
  """ Holds parameters of registration.
  An instance of this class is passed to virtual methods
  """

  # MRML volume nodes
  fixed = None
  moving = None
  transformed = None

  # MRML Markup Point List Nodes
  fixedPoints = None
  movingPoints = None
  transformedPoints = None

  # MRML Linear Transform Node
  transform = None

