import boincvm_common.support as support

import stomper
import logging

class BaseStompEngine(stomper.Engine):
  """
  G{classtree BaseStompEngine}
  """
  
  logger = logging.getLogger(support.discoverCaller())

  def __init__(self, msgInterpreter):
    stomper.Engine.__init__(self)
    self._msgInterpreter = msgInterpreter


  def ack(self, msg):
    """Called when a MESSAGE message is received"""
    #msg is an unpacked frame
    headers = msg['headers']
  
    self._msgInterpreter.interpret(msg)

    if headers.get('ack') == 'client':
      res = stomper.Engine.ack(self, msg)
    else:
      res = stomper.NO_REPONSE_NEEDED

    return (res, )

  def error(self, msg):
    return ( stomper.Engine.error(self, msg) ,)

  def receipt(self, msg):
    return ( stomper.Engine.receipt(self, msg) ,)


  def react(self, msg):
    """ Returns an iterable of responses """
    rxdFrame = stomper.unpack_frame(msg)
    cmd = rxdFrame['cmd']

    self.logger.info("Received a %s message." % cmd)
    self.logger.debug("Headers: %s ; Body: %s" % (rxdFrame['headers'], rxdFrame['body']))
    return iter(stomper.Engine.react(self, msg))

