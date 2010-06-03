from twisted.trial import unittest
from twisted.internet import reactor, defer


import sys
import os
from StringIO import StringIO 
from ConfigParser import SafeConfigParser
from boincvm_host.controllers import ControllerFactory 
from boincvm_host.controllers import VirtualBox 
import logging

logging.basicConfig(level=logging.DEBUG, \
    format='%(asctime)s - %(name)s - %(levelname)s: %(message)s', )


class TestControllerCreation(unittest.TestCase):

  def setUp(self):
    pass
    
  def test_createVirtualBoxController(self):
    cfg = \
"""
[Hypervisor]
hypervisor=VirtualBox
hypervisor_helpers_path=
"""
    configFile = StringIO(cfg)
    self.config = SafeConfigParser()
    self.config.readfp(configFile)
    configFile.close()

    controller = ControllerFactory.createController(self.config)
    self.assertTrue(controller)
    self.assertEqual( controller._controller, VirtualBox) 


