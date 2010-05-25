import boincvm_common.support as support

from twisted.internet.protocol import Protocol, ReconnectingClientFactory
from twisted.internet import reactor

import stomper
import logging

class StompProtocol(Protocol):
  
  #transport available at self.transport, as set by BaseProtocol.makeConnection
  #factory available at self.factory, as set by Factory.buildProtocol

  logger = logging.getLogger( support.discoverCaller() )

  def __init__(self, stompEngine, username, password):
    self._username = username
    self._password = password
    self._myEngine = stompEngine
    self._myEngine.protocol = self #inject ourselves into the engine, FIXME

  def connectionMade(self):
    """
    Called when a connection is made. 
    Protocol initialization happens here
    """
    self.logger.info("Connection with the broker made")
    stompConnectMsg = stomper.connect(self._username, self._password)
    self.transport.write(stompConnectMsg)

  def connectionLost(self, reason):
    """Called when the connection is shut down"""
    pass

  def dataReceived(self, data):
    """Called whenever data is received"""
    reactions =  self._myEngine.react(data)
    if reactions: #reaction is an iterable
      for reaction in reactions:
        self.transport.write(reaction)
 
  def sendStompMessage(self, msg):
    self.transport.write(msg)


class StompProtocolFactory(ReconnectingClientFactory):

  logger = logging.getLogger( support.discoverCaller() )

  def __init__(self, engine, username, password):
    self.protocol = lambda: StompProtocol(engine, username, password)

    self.delay = 5.0 #XXX: this isn't a public attribute, working around a twisted bug
    self.factor = 1.0
    self.jitter = 0.0

  def buildProtocol(self, addr):
    try:
      #will create a protocol of the class given in self.protocol (set in the ctor)
      p = ReconnectingClientFactory.buildProtocol(self, addr)
    except Exception, e:
      #this could happen if, for instance, we can't start a helper prog (such as vboxwebsrv)
      reactor.stop()
      raise
    def augmentedConnectionMade():
      p.baseConnectionMade()
      p.factory.resetDelay()
    p.baseConnectionMade = p.connectionMade
    p.connectionMade = augmentedConnectionMade
    return p

  def clientConnectionLost(self, connector, reason):
    self.logger.info("Connection with the broker lost: %s" % reason)
    ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

  def clientConnectionFailed(self, connector, reason):
    self.logger.error("Connection with the broker failed: %s" % reason )
    ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)



