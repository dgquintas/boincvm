from boincvm_common.stomp import BaseStompEngine 
from boincvm_common.stomp.protocol import words, MsgInterpreter, destinations
from boincvm_common import support, Exceptions 
from boincvm_host.controllers import ControllerFactory 

from twisted.internet import utils, defer, reactor
from twisted.internet.task import LoopingCall
from twisted.web import resource

import stomper
import logging
import time
from os.path import join, basename

class HostStompEngine(BaseStompEngine.BaseStompEngine):
  """ This basically models a client (ie, VM instance)"""
  
  logger = logging.getLogger(support.discoverCaller())

  def __init__(self, config):
    msgInterpreter = MsgInterpreter.MsgInterpreter(self)
    BaseStompEngine.BaseStompEngine.__init__(self, msgInterpreter)

    self._hvController = ControllerFactory.createController(config)

    self._vms = {}
    self._pings = {}

    self._cmdReqsSent = {} #cmdId: dict with keys (timestamp, to, cmd, args, env, path)
    self._cmdReqsRetired = {} #finished cmdReqsSent
    self._cmdReqsRcvd = {}

    self._chirpPath = config.get('Host', 'chirp_path')
    grace = int(config.get('Host', 'vm_gc_grace'))

    self._vmsChecker = LoopingCall( self._performVMsGC, grace)
    self._vmsChecker.start( grace, now=False)

    #FIXME: make it return stuff, instead of having side effects
    self._initializeIdsToNamesMapping()  #sets self._idsToNames


  def connected(self, msg):
    res = []
    #once connected, subscribe
    res.append(stomper.subscribe(destinations.CONN_DESTINATION))
    res.append(stomper.subscribe(destinations.CMD_RES_DESTINATION))

    return tuple(res)


  #####################################

  @defer.inlineCallbacks
  def _initializeIdsToNamesMapping(self):
    idsToNamesMap = yield self._hvController.getIdsToNamesMapping()
    self.logger.debug("Ids -> Names table initialized: %s" % idsToNamesMap)
    self._idsToNames = idsToNamesMap

  def _getNameForId(self, vmId):
    name = self._idsToNames.get(vmId)
    if not name:
      self.logger.error("Unable to match VM ID '%s' to any registered VM (is the VM controller really running from within a VM?", str(vmId))
      raise Exceptions.NoSuchVirtualMachine(str(vmId))
    else:
      return name

  def requestCmdExecution(self, to, cmdId, cmd, args=(), env={}, path=None, fileForStdin=''):
    if to not in self._vms:
      name = self._getNameForId(to)
      msg = "'%s' is not a registered VM." % name
      self.logger.error(msg)
      raise ValueError(msg)

    self.protocol.sendStompMessage( words.CMD_RUN().howToSay(self, to, cmdId, cmd, args, env, path, fileForStdin ) )
    requestKeys = ('timestamp', 'to', 'cmd', 'args', 'env', 'path', 'fileForStdin')
    requestValues = (time.time(), to, cmd, args, env, path, fileForStdin )
    self._cmdReqsSent[cmdId] = dict( zip( requestKeys, requestValues) )
    self.logger.info("Requested execution of command '%s' with cmd-id '%s'" % (cmd, cmdId))

  def ping(self, to, timeout_secs):
    def _timeout(timestamp):
      d = self._pings.pop(timestamp, None)
      if d:
        name = self._getNameForId(to)
        d.errback(RuntimeError('PING timeout (for %s)' % name))

    timestamp = str(time.time())
    d = defer.Deferred()
    self._pings[timestamp] = d
    self.protocol.sendStompMessage( words.PING().howToSay(self, to, timestamp) )
    reactor.callLater(timeout_secs, _timeout, timestamp) 
    return d

  def processPong(self, msg):
    timestamp = msg['headers']['timestamp']
    d = self._pings.pop(timestamp, None)
    assert d
    vmId = msg['headers']['from']
    vmName = self._getNameForId(vmId)
    d.callback('PONG from %s' % vmName)


  def addVM(self, vmId, vmIp):
    """ Adds a new VM to the party """
    vmName = self._getNameForId(vmId) 
    self._vms[vmId] = HostStompEngine.VMRef(vmId, vmIp, vmName) 
    self.logger.info("VM '%s' has joined the party" % self._vms[vmId].name )

  def removeVM(self, vm): 
    """ Removes a VM from the party """
    vmRef = self._vms.pop(vm)
    self.logger.info("VM '%s' has left the party" % vmRef.name )

  def getRegisteredVMs(self):
    """ Returns a list of the registered VMs """
    return self._vms.keys()

  def keepVMForNow(self, vmId, vmIp):
    """ Keep a VM from being GC'd for now.
    
        ie, a beacon for that VM has been received recently.
    """
    if vmId not in self._vms:
      self.logger.warn("VM '%s' isn't registered with the host! Adding it now" % vmId )
      self.addVM(vmId, vmIp)
    else:
      now = time.time()
      vm = self._vms[vmId]
      vm.beacon = now
      self.logger.info("Beacon received for VM '%s' at '%s'" % (vm.name, time.ctime(now)) )

  def _performVMsGC(self, grace):
    self.logger.debug("Performing VM GC")
    now = time.time()
    hardGrace = 1.5*grace #FIXME: magic number
    offendingVms = filter( lambda vm: now - vm.beacon > grace, self._vms.itervalues() )
    deadVms = filter( lambda vm:  now - vm.beacon > hardGrace , offendingVms )
    vmsToWarn = ( vm.id for vm in offendingVms if vm not in deadVms )
    map( lambda vm: self.logger.warn("Aliveness warning for VM '%s'" % vm), vmsToWarn)
    #remove the dead ones
    map( lambda vm: self.removeVM(vm.id), deadVms )


  def processCmdResult(self, resultsMsg):
    serializedResults = resultsMsg['body'].split(None, 1)[1]
    #serializeded data: dict with keys (cmd-id, out, err, finished?, code/signal, resources)
    results = support.deserialize(serializedResults)
    self.logger.debug("Deserialized results: %s" % results)
    cmdId = results.pop('cmd-id')
    #this comes from a word.CMD_RESULT.listenAndAct
    #note down for which cmd we are getting the result back
    assert cmdId in self._cmdReqsSent
    self._cmdReqsRcvd[cmdId] = results
    self._cmdReqsRetired[cmdId] = self._cmdReqsSent.pop(cmdId)
    self.logger.info("Received command results for cmd-id '%s'", cmdId )

  def popCmdResults(self, cmdId):
    # for invalid cmdIds, returning None could
    # result in problems with xml-rpc. Thus we
    # resource to an empty string, which likewise
    # fails a boolean test
    return self._cmdReqsRcvd.pop(cmdId, "") 


  def listFinishedCmds(self):
    return self._cmdReqsRcvd.keys()

  def getCmdDetails(self, cmdId):
    details = self._cmdReqsSent.get(cmdId)
    if not details:
      details = self._cmdReqsRetired.get(cmdId)
    return support.serialize(details)


  def cpFileToVM(self, vmId, pathToLocalFileName, pathToRemoteFileName = None ):
    """
    @param pathToRemoteFileName where to store the file, relative to the root of the server.
    If None, the basename of the source will be stored in the / of the server.
    """
    #this returns a deferred whose callbacks take care of returning the result
    if vmId not in self._vms:
      msg = 'Unregistered VM: %s' % self._getNameForId(vmId)
      self.logger.error(msg)
      dres = defer.fail(msg)
    else:
      vmIp = self._vms[vmId].ip
      if not pathToRemoteFileName:
        pathToRemoteFileName = basename(pathToLocalFileName)
      #chirp_put [options] <local-file> <hostname[:port]> <remote-file>
      args = ('-t 10', pathToLocalFileName, vmIp, pathToRemoteFileName) #FIXME: magic numbers
      chirp_cmd = join( self._chirpPath, 'chirp_put')
      dres = utils.getProcessOutputAndValue(chirp_cmd, args)

    return dres
    

  def cpFileFromVM(self, vmId, pathToRemoteFileName, pathToLocalFileName = None):
    #this returns a deferred whose callbacks take care of returning the result
    if vmId not in self._vms:
      msg = 'Unregistered VM: %s' % self._getNameForId(vmId)
      self.logger.error(msg)
      dres = defer.fail(msg)
    else:
      vmIp = self._vms[vmId].ip
      if not pathToLocalFileName:
        pathToLocalFileName = pathToRemoteFileName
      #chirp_get [options] <hostname[:port]> <remote-file> <local-file>
      args = ('-t 10', vmIp, pathToRemoteFileName, pathToLocalFileName)  #FIXME: magic numbers
      chirp_cmd = join( self._chirpPath, 'chirp_get')
      dres = utils.getProcessOutputAndValue(chirp_cmd, args)
    return dres

  class VMRef(object):
    """ Decorator in order to keep track of the latest received beacons (for GC purposes) """

    def __init__(self, vmId, vmIp, vmName):
      self._vmId = vmId
      self._vmIp = vmIp
      self._vmName = vmName
      self._setBeacon(time.time()) #implicit beacon upon construction

    def _setBeacon(self, when):
      self._beacon = when

    def _getBeacon(self):
      return self._beacon

    beacon = property(_getBeacon, _setBeacon)

    @property
    def ip(self):
      return self._vmIp
   
    @property
    def id(self):
      return self._vmId

    @property
    def name(self):
      return self._vmName

    def __repr__(self):
      return "%s/%s" % (self.id, self.ip)

    def hash(self):
      return hash(self._vmId)



    
