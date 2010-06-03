import boincvm_common.support as support

from twisted.internet import protocol, defer, error, reactor, utils

from operator import sub
import logging
try:
  import resource 
except:
  #ignore, as it's unavailable under windows
  #but that doesn't matter: no commands get
  #executed under windows -the host-
  pass 

def diff_rusage( second, first ):
  return resource.struct_rusage(map( sub , second, first ))

def rusage_to_dict( r ):
  #this is safe to hardcode because it ultimately depends
  #on getrusage(2), which is standard
  fields= ('ru_utime', 	'ru_stime',	  'ru_maxrss',  'ru_ixrss',
           'ru_idrss',	'ru_isrss',	  'ru_minflt',  'ru_majflt',
           'ru_nswap',	'ru_inblock', 'ru_oublock', 'ru_msgsnd', 
           'ru_msgrcv', 'ru_nsignals','ru_nvcsw',	  'ru_nivcsw' )
  res = {}
  for (i,f) in enumerate(fields):
    res[f] = r[i]
  return res


class StdinEnabledCommandProtocol(protocol.ProcessProtocol):
  def __init__(self, fileToInput):
    self._stdout = ''
    self._stderr = ''
    self._fileToInput = fileToInput
    self._deferred = defer.Deferred()

  @property
  def deferred(self):
    return self._deferred 

  def connectionMade(self):
    if self._fileToInput:
      readStuff = self._fileToInput.read()
      while readStuff:
        self.transport.write( readStuff )
        readStuff = self._fileToInput.read()
    self.transport.closeStdin()

  def outReceived(self, data):
    self._stdout += data
  def errReceived(self, data):
    self._stderr += data

  def processEnded(self, reason):
    exitCode =  reason.value.exitCode
    if reason.type is error.ProcessDone:
      self._deferred.callback( (self._stdout, self._stderr, exitCode) )
    else: # rason.type == ProcessError
      self._deferred.errback( (self._stdout, self._stderr, exitCode) )



class CommandExecuter(object):

  logger = logging.getLogger(support.discoverCaller())

  def __init__(self, cmdId, parameters):
    #parameters is a dict
    self._cmdId = cmdId
    self._parameters = parameters

  def executeCommand(self):
    """ 
    Executes (or tries to) cmd.

    Runs cmd, returning a tuple (stdout, stderr) with the
    contents of the execution
    """
    res = None
    cmd = self._parameters.pop('cmd')
    fileForStdin = self._parameters.pop('fileForStdin')
    try:
      if fileForStdin:
        fileForStdin = file(fileForStdin, 'r')
    except Exception, e:
      res = defer.fail( ('', str(e), -1) ) #mimic process output
      self._execResUsage = resource.getrusage( resource.RUSAGE_CHILDREN )
    else:
      for (k,v) in self._parameters.iteritems():
        self._parameters[k] = support.safe_eval(v)
      
      args = list(self._parameters.pop('args'))
      args.insert(0, cmd)
      self.logger.info("Requested execution of command %s (%s) with id %s" % ( cmd, self._parameters, self._cmdId) )
      self._execResUsage = resource.getrusage( resource.RUSAGE_CHILDREN )
      pp = StdinEnabledCommandProtocol( fileForStdin )
      reactor.spawnProcess( pp, cmd, args, **self._parameters ) 
      #return utils.getProcessOutputAndValue(cmd, **self._parameters)
      res = pp.deferred

    return res

  def getExecutionResults(self, results):
    execResUsageEnd = resource.getrusage( resource.RUSAGE_CHILDREN )
    execResUsageNet = diff_rusage( execResUsageEnd, self._execResUsage )
    execResUsageNet = rusage_to_dict( execResUsageNet )
    
    out, err, code = results
    self.logger.info("Command %s (cmd-id: %s) finished with code %d" % (self._parameters, self._cmdId, code))
    return (self._cmdId, out, err, True, code, execResUsageNet)

  def errorHandler(self, results): 
    execResUsageEnd = resource.getrusage( resource.RUSAGE_CHILDREN )
    execResUsageNet = diff_rusage( execResUsageEnd, self._execResUsage )
    execResUsageNet = rusage_to_dict( execResUsageNet )
    
    out, err, signal = results.value #results is a Failure instance
    self.logger.error("Command %s (cmd-id: %s) interrupted by signal %d" % (self._parameters, self._cmdId, signal))
    return (self._cmdId, out, err, False, signal, execResUsageNet)

    
