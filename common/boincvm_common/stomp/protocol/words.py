import CommandExecuter
import destinations 
import boincvm_common.support as support

import logging
import stomper 
import fnmatch


logger = logging.getLogger('words')

class BaseWord(object):
  """ Initializes the Frame object with the inheriting class' name """
  @classmethod
  def __init__(cls):
    cls._frame = stomper.Frame()
    cls._frame.body = cls.__name__

class PING(BaseWord):
  @classmethod
  def howToSay(cls, host, to, timestamp):
    cls._frame.cmd = 'SEND'
    headers = {}
    headers['destination'] = destinations.CMD_REQ_DESTINATION
    headers['to'] = to
    headers['timestamp'] = timestamp
    cls._frame.headers = headers
    
    return cls._frame.pack()
  
  @classmethod
  def listenAndAct(cls, vm, msg):
    headers = msg['headers']
    if fnmatch.fnmatch(vm.id, headers['to']): 
      vm.pong(msg)

class PONG(BaseWord):
  @classmethod
  def howToSay(cls, vm, pingMsg):
    cls._frame.cmd = 'SEND'
    headers = {}
    headers['destination'] = destinations.CMD_RES_DESTINATION
    headers['from'] = vm.id
    headers['timestamp'] = pingMsg['headers']['timestamp'] 
    cls._frame.headers = headers

    return cls._frame.pack()

  @classmethod
  def listenAndAct(cls, host, msg):
    host.processPong(msg)


class CMD_RUN(BaseWord):
  @classmethod
  def howToSay(cls, host, to, cmdId, cmd, args=(), env={}, path=None, fileForStdin=''):
    cls._frame.cmd = 'SEND'
    headers = {}

    headers['destination'] = destinations.CMD_REQ_DESTINATION
    headers['to'] = to
    headers['cmd-id'] = cmdId

    headers['cmd'] = cmd
    headers['args'] = args
    headers['env'] = env
    headers['path'] = path

    headers['fileForStdin'] = fileForStdin

    cls._frame.headers = headers

    return cls._frame.pack()

  @classmethod
  def listenAndAct(cls, vm, msg):
    headers = msg['headers']
    #TODO: sanity checks for the headers
    #if the VM's id matches the given 'to' destination,
    #either trivially or "pattern"-ly
    if fnmatch.fnmatch(vm.id, headers['to']): 
      paramsList = ('cmd', 'args', 'env', 'path', 'fileForStdin')
      params = {}
      for p in paramsList:
        params[p] = headers.get(p)

      cmdId = headers.get('cmd-id')

      cmdExecuter = CommandExecuter.CommandExecuter(cmdId, params)
      cmdExecuter.executeCommand(
          ).addCallback( cmdExecuter.getExecutionResults
          ).addErrback( cmdExecuter.errorHandler 
          ).addCallback( vm.dealWithExecutionResults
          )

class CMD_RESULT(BaseWord):
  @classmethod
  def howToSay(cls, vm, results):
    #results is a dict with keys = ('cmd-id', 'out', 'err', 'finished', 'exitCodeOrSignal', 'resources' )
    cls._frame.cmd = 'SEND'

    cls._frame.headers['destination'] = destinations.CMD_RES_DESTINATION
    cls._frame.headers['cmd-id'] = results['cmd-id']

    results = support.serialize(results)

    cls._frame.body = ' '.join( (cls._frame.body, results) )

    return cls._frame.pack()
		

  @classmethod
  def listenAndAct(cls, host, resultsMsg):
    #we receive the command execution results,
    #as sent by one of the vms (in serialized form)
    host.processCmdResult(resultsMsg)



class HELLO(BaseWord):
  @classmethod
  def howToSay(cls, vm):
    cls._frame.cmd = 'SEND'
    cls._frame.headers = {'destination': destinations.CONN_DESTINATION, 'id': vm.id, 'ip': vm.ip}
    return cls._frame.pack()

  @classmethod
  def listenAndAct(cls, host, msg):
    headers = msg['headers']
    vmId = headers['id']
    vmIp = headers['ip']
    host.addVM(vmId, vmIp)


class BYE(BaseWord):
  @classmethod
  def howToSay(cls, vm):
    cls._frame.cmd = 'SEND'
    cls._frame.headers = {'destination': destinations.CONN_DESTINATION, 'id': vm.id, 'ip': vm.ip}
    return cls._frame.pack()

  @classmethod
  def listenAndAct(cls, host, msg):
    headers = msg['headers']
    who = headers['id']
    host.removeVM(who)

class STILL_ALIVE(BaseWord):
  @classmethod
  def howToSay(cls, vm):
    cls._frame.cmd = 'SEND'
    cls._frame.headers = {'destination': destinations.CONN_DESTINATION, 'id': vm.id, 'ip': vm.ip }
    return cls._frame.pack()

  @classmethod
  def listenAndAct(cls, host, msg):
    headers = msg['headers']
    vmId = headers['id']
    vmIp = headers['ip']
    host.keepVMForNow(vmId, vmIp)


#because ain't ain't a word!
class AINT(BaseWord):
  @classmethod
  def listenAndAct(cls, requester, msg):
    logger.warn("Unknown message type received. Data = '%s'" % str(msg))
    

