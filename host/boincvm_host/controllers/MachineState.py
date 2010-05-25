class MachineState(object):
  def __init__(self, name):
    self.name = name

  def __str__(self):
    return self.name

  def __repr__(self):
    return "<MachineState: %s>" % self.name


_states = ('Unknown', 'PoweredOff', 'Saved', 'Aborted', 'Running', 
      'Paused', 'Stuck', 'Starting', 'Stopping', 'Saving', 
      'Restoring', 'Discarding' )

for state in _states:
  setattr(MachineState, state, MachineState(state))

