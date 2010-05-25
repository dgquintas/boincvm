import boincvm_common.support as support
from words import *

import logging
class MsgInterpreter(object):

  logger = logging.getLogger(support.discoverCaller())

  def __init__(self, requester):
    #requester is an instance of Host or VM
    self._requester = requester

  def interpret(self, msg):
    #msg is an unpacked STOMP frame
    firstWord = msg['body'].split(None,1)[0] #only interested in the 1st word

    self.logger.debug("Trying to interpret %s for %s" % (firstWord, self._requester) )
    try:
      word = eval( firstWord )
    except NameError:
      word = AINT #ain't ain't a word!

    word.listenAndAct(self._requester, msg)

