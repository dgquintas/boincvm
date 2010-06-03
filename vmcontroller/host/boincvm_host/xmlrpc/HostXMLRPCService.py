from boincvm_common import support, Exceptions
from boincvm_host.controllers import ControllerFactory

from twisted.web import xmlrpc, server, resource
from twisted.internet import reactor, defer

import logging
import uuid
import inspect
import ConfigParser
 
def _fail(failure):
  HostXMLRPCService.logger.info("Exception on XMLRPC deferred:\n %s" % (failure.getBriefTraceback(),) )
  raise xmlrpc.Fault(-1, str(failure.value))
def _success(results):
  return results

class HostXMLRPCService(xmlrpc.XMLRPC, object):

  logger = logging.getLogger( support.discoverCaller() )
  
  def __init__(self, config):
    xmlrpc.XMLRPC.__init__(self)
    self._config = config
    self._hvController = ControllerFactory.createController(config)
    self._createHVControllerMethods()
    self._initializeIdsToNamesMapping() #sets self._idToNames
    self._initializeNamesToIdsMapping() #sets self._namesToIds

  #from xmlrpc.XMLRPC
  def _getFunction(self, functionPath):
    f = super(HostXMLRPCService, self)._getFunction(functionPath)
    # f is an xmlrpc_ method

    def wrapWithCallbacks(*args, **kw):
      return defer.maybeDeferred(f, *args, **kw).addCallbacks(_success, _fail)
    return wrapWithCallbacks 


  @defer.inlineCallbacks
  def _initializeIdsToNamesMapping(self):
    idsToNamesMap = yield self._hvController.getIdsToNamesMapping()
    self.logger.debug("Ids -> Names table initialized: %s" % idsToNamesMap)
    self._idsToNames = idsToNamesMap
  @defer.inlineCallbacks
  def _initializeNamesToIdsMapping(self):
    namesToIds = yield self._hvController.getNamesToIdsMapping()
    self.logger.debug("Names -> Ids table initialized: %s" % namesToIds)
    self._namesToIds = namesToIds
 
  def _getNameForId(self, vmId):
    name = self._idsToNames.get(vmId)
    if not name:
      raise Exceptions.NoSuchVirtualMachine(str(vmId))
    else:
      return name
  def _getIdForName(self, vmName):
    id = self._namesToIds.get(vmName)
    if not id:
      raise Exceptions.NoSuchVirtualMachine(str(vmName))
    else:
      return id 

  def makeEngineAccesible(self, engine):
    self._engine = engine #it refers to the HostStompEngine
    siteRoot = resource.Resource()
    siteRoot.putChild('RPC2', self)
    port = int(self._config.get('Host', 'xmlrpc_port'))
    listen_on = self._config.get('Host', 'xmlrpc_listen_on')
    reactor.listenTCP(port, server.Site(siteRoot), interface=listen_on) 
  
  
  ###########################
  ## Operation on the VMs  ##
  ###########################
  def xmlrpc_listRegisteredVMs(self):
    registeredVMIds = self._engine.getRegisteredVMs()
    return map( self._getNameForId, registeredVMIds )

  def xmlrpc_runCmd(self, toVmName, cmd, args=(), env={}, path=None, fileForStdin=''):
    vmId = self._getIdForName(toVmName)
    cmdId = str(uuid.uuid4())
    return self._engine.requestCmdExecution(vmId, cmdId, cmd, args, env, path, fileForStdin)
    return cmdId

  def xmlrpc_ping(self, toVmName, timeout_secs=5.0): #FIXME: magic number of seconds
    vmId = self._getIdForName(toVmName)
    return self._engine.ping(vmId,timeout_secs)

  def xmlrpc_listFinishedCmds(self):
    return self._engine.listFinishedCmds()

  def xmlrpc_getCmdResults(self, cmdId):
    return self._engine.popCmdResults(cmdId)

  def xmlrpc_getCmdDetails(self, cmdId): 
    return self._engine.getCmdDetails(cmdId)

  def xmlrpc_cpFileToVM(self, vmName, pathToLocalFileName, pathToRemoteFileName = None ):
    vmId = self._getIdForName(vmName)
    return self._engine.cpFileToVM(vmId, pathToLocalFileName, pathToRemoteFileName )

  def xmlrpc_cpFileFromVM(self, vmName, pathToRemoteFileName, pathToLocalFileName = None):
    vmId = self._getIdForName(vmName)
    return self._engine.cpFileFromVM(vmId, pathToRemoteFileName, pathToLocalFileName )


  ################################################
  ## Hypervisor controller dependent operations ##
  ################################################
  def _inspectHVControllerMethods(self):
    allMethods = inspect.getmembers(self._hvController, inspect.isfunction)
    publicMethods = filter( lambda method: method[0][0] != '_', allMethods )
    return publicMethods


  def _addMethod(self, method):
    name = 'xmlrpc_' + method.func_name
    setattr(self, name, method)

  def _createHVControllerMethods(self):
    self.hvControllerMethods = self._inspectHVControllerMethods()
    for method in self.hvControllerMethods:
      self._addMethod( method[1] )
      self.logger.debug("Controler method %s dynamically added" % method[0])

  def xmlrpc_help(self, methodName=None):
    if not methodName:
      allMethods = inspect.getmembers(self)
      xmlrpcMethods = filter( lambda method: method[0].startswith('xmlrpc_'), allMethods )
      methodNames = map( lambda m: m[0][len('xmlrpc_'):], xmlrpcMethods )
      resList = map( lambda mName: "%s" % self.xmlrpc_help(mName), methodNames )
      res = '\n\n'.join(resList)

    else:
      f = getattr(self, 'xmlrpc_' + methodName, None)
      if not f:
        raise ValueError('No such method: %s' % methodName)
      else:
        signature = _getPrintableFunctionSignature(f)
        res = '%s%s:\n%s' % (methodName, signature, f.__doc__ or '<No Docstring>',)

    return res

  
#########################################
## Helper functions
#########################################
def _getPrintableFunctionSignature(f):
  argSpec = inspect.getargspec(f)

  args = argSpec[0]
  if not args:
    args = ()
  else:
    if args[0] == 'self':
      del(args[0])

  defs = argSpec[3]
  if not defs:
    defs = ()

  argsWithDefs = reversed(map( lambda a,d: d and ( '%s=%s' % (a,d) ) or str(a), \
      reversed(args), reversed(defs) ) )

  return '(%s)' % (', '.join(argsWithDefs))


