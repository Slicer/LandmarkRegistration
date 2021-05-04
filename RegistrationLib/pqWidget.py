class pqWidget:
  """
  A "QWidget"-like widget class that manages provides some
  helper functionality (signals, slots...)
  """
  def __init__(self):
    self.connections = {} # list of slots per signal

  def connect(self,signal,slot):
    """pseudo-connect - signal is arbitrary string and slot if callable"""
    if signal not in self.connections:
      self.connections[signal] = []
    self.connections[signal].append(slot)

  def disconnect(self,signal,slot):
    """pseudo-disconnect - remove the connection if it exists"""
    if signal in self.connections:
      if slot in self.connections[signal]:
        self.connections[signal].remove(slot)

  def emit(self,signal,args):
    """pseudo-emit - calls any slots connected to signal"""
    if signal in self.connections:
      for slot in self.connections[signal]:
        slot(*args)

