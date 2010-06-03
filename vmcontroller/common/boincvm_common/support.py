import pdb
try:
  import json
except ImportError:
  import simplejson as json

import inspect

def serialize(data):
  """ 
  Serialize the information given in C{data}. 

  @param data: the data to serialize.
  @rtype str
  @return a string containing the serialized version of data.
  """
  return json.dumps(data)

def deserialize(data):
  """ 
  Deserialize the information given in C{data}, back to its original pythonic form.

  @param data: the data to deserialize.
  @return the python object contained in the serialized data.
  """
  return json.loads(data)

#def which(program):
#  import os
#  res = []
#  def is_exe(fpath):
#      return os.path.exists(fpath) and os.access(fpath, os.X_OK)
#
#  fpath, fname = os.path.split(program)
#  if fpath:
#    if is_exe(program):
#        res.append(program)
#  else:
#    for path in os.environ["PATH"].split(os.pathsep):
#      exe_file = os.path.join(path, program)
#      if is_exe(exe_file):
#        res.append(exe_file)
#
#  return res

def discoverCaller():
  """
  Returns the name of the innermost frame when invoked.

  For instance, invoked from within a function g(), it'd return 
  'g'. Also works for classes:

  >>> class C:
  ...   name = discoverCaller()
  >>> print C.name
  C
  """
  caller = inspect.getouterframes(inspect.currentframe())[1][3]
  return caller


#def getClass( clazz ):
#    parts = clazz.split('.')
#    module = ".".join(parts[:-1])
#    m = __import__( module )
#    for comp in parts[1:]:
#        m = getattr(m, comp)            
#    return m

try:
  import ast
except ImportError: #sigh...
  _eval_func = eval
else:
  _eval_func = ast.literal_eval
def safe_eval( expr ):
  """ 
  Safely evaluates the given expression, if possible. 
  If the necessary modules aren't available (Python <= 2.5), falls
  back to an insecure evaluation.
  What it means to be safe in this context is that:
  "The string or node provided may only consist of the following
  Python literal structures: strings, numbers, tuples, lists, dicts, booleans,
  and None."
  """
  return _eval_func( expr )

#import subprocess
#def _getPIDFromPS(procName):
#  cmd = 'ps cx -o comm=,pid='
#  p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
#  cmdOutput = p.communicate()[0]
#  outputLines = cmdOutput.splitlines()
#  splittedOutputLines = map( lambda l: l.split(), outputLines )
#  vboxwebsrvPids = [ line[1] for line in splittedOutputLines \
#      if line[0] == procName ]
#  pids = map(int, vboxwebsrvPids)
#  return pids
#
#
#def pidof(procName):
#  """ Returns a list with the PID(s) of the 'procName' process, or None """
#  import os, platform
#  res = None
#  sysName = platform.system()
#  if sysName == 'Windows':
#    #raise NotImplementedError
#    return None #TODO
#  else: # sysName == 'Darwin' || 'Linux'
#    return _getPIDFromPS(procName)
##  else:
##    procEntries = os.listdir('/proc')
##    pids = filter( str.isdigit , procEntries ) 
##    for pid in pids:
##      f = file(os.path.join('/proc', pid, 'cmdline'), 'r')
##      cmdline = f.read()
##      f.close()
##      cmd = os.path.basename(cmdline).split('\x00')[0]
##      if cmd == procName:
##        res = int(pid)
##        break
#
#  return res

def reverseDict(d):
  """ Reverses a dictionary.

  If a key isn't unique (replicated value in the original dict), only 
  the "last" (iteration order dependent) is kept as a key in the
  result

  @type d: dictionary
  @param d: the dictionary to reverse
  """
  return dict( (v,k) for k,v in d.iteritems() )

class UninitializedPlaceholder(object):
  """ Raises L{NotImplementedError} upon any access attempt. 
  
      Meant to be used as a placeholder for uninitialized objects.
  """

  def __init__(self, msg=None):
    """ 
        @param msg: An optional message to pass to the exception raised
    """
    if not msg:
      msg = "This is just an uninitialized placeholder!"
    self._msg = msg

  def __getattr__(self, attr):
    raise NotImplementedError(self._msg)




