import logging

import HyperVisorController
from boincvm_common import Exceptions

logger = logging.getLogger('controllers.ControllerFactory')

def createController(config):
  """ Creates the appropriate (hypervisor) controller based on the
      given configuration. 

      This is the place where to perform particular initialization tasks for 
      the particular hypervisor controller implementations.
  """
  hv = config.get('Hypervisor', 'hypervisor')
  try:
    hvMod = __import__(hv, globals=globals(), level=-1)
  except ImportError:
    msg = "Hypervisor '%s' is not supported" % hv
    logger.fatal(msg)
    raise Exceptions.ConfigError(msg)

  logger.info("Using %s as the HyperVisor" % hvMod.__name__)

  HyperVisorController._controller = hvMod

  return HyperVisorController

