class NoSuchVirtualMachine(Exception):
  def __init__(self, msg):
    self._msg = msg
  def __str__(self):
    return "No VM by the name/id %s found" % self._msg

class ConfigError(Exception):
  def __init__(self, msg):
    self._msg = msg

  def __str__(self):
    return "Configuration error: %s" % self._msg
