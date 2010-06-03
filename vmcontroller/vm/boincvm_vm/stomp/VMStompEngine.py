import boincvm_common.stomp.protocol.MsgInterpreter as MsgInterpreter
import boincvm_common.stomp.protocol.words as words
import boincvm_common.stomp.protocol.destinations as destinations
import boincvm_common.stomp.BaseStompEngine as BaseStompEngine
import boincvm_common.support as support

import stomper
import logging
import netifaces

from twisted.internet.task import LoopingCall


class VMStompEngine(BaseStompEngine.BaseStompEngine):
  """ This basically models a client (ie, VM instance)"""
  
  logger = logging.getLogger(support.discoverCaller())

  def __init__(self, config):
    msgInterpreter = MsgInterpreter.MsgInterpreter(self)
    BaseStompEngine.BaseStompEngine.__init__(self, msgInterpreter)
 
    networkInterface = config.get('VM', 'network_interface')
    period = int(config.get('VM', 'beacon_interval'))

    self._startSendingBeacons = lambda: LoopingCall( self._sendBeacon ).start(period, now=False)

    self._initId(networkInterface)


  def connected(self, msg):
    res = []
    #once connected, subscribe
    res.append(stomper.subscribe(destinations.CMD_REQ_DESTINATION))

    #announce ourselves
    res.append( words.HELLO().howToSay(self) )
 
    #FIXME: even better whould be to wait for the HELLO back from the host
    self._startSendingBeacons()

    return tuple(res)

  def pong(self, pingMsg):
    self.protocol.sendStompMessage( words.PONG().howToSay(self, pingMsg) )

  def dealWithExecutionResults(self, results):
    resultsFields = ('cmd-id', 'out', 'err', 'finished', 'exitCodeOrSignal', 'resources' )
    #see CommandExecuter.getExecutionResults

    resultsDict = dict( zip( resultsFields, results ) )
    #self.protocol got injected by StompProtocol
    self.protocol.sendStompMessage( words.CMD_RESULT().howToSay(self, resultsDict) )

  @property
  def id(self):
    return self._id

  @property
  def ip(self):
    return self._ip

  def __repr__(self):
    return "VM with ID/IP: %s/%s" % (self.id, self.ip)

  def _initId(self, iface):
    networkInterfaceData = netifaces.ifaddresses(iface)
    self._id, self._ip = [ networkInterfaceData[af][0]['addr'] for af in (netifaces.AF_LINK, netifaces.AF_INET) ]
    self._id = self._id.upper()
    self.logger.debug("VM instantiated with id/ip %s/%s" % (self._id, self._ip) )

  def _sendBeacon(self):
    self.logger.info("%s stayin' aliiiive" % self)
    self.protocol.sendStompMessage( words.STILL_ALIVE().howToSay(self) )




