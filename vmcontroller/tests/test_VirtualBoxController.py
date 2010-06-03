from __future__ import print_function
from twisted.trial import unittest
from twisted.internet import reactor, defer

import sys
import os
import tempfile
import logging
import shutil 
import pdb 

logging.basicConfig(level=logging.INFO, \
    format='%(asctime)s - %(name)s - %(levelname)s: %(message)s', )

VBOX_FOLDER = tempfile.mkdtemp()
os.putenv("VBOX_USER_HOME", VBOX_FOLDER)
print("Using %s as the VBOX_USER_HOME" % VBOX_FOLDER)

from boincvm_host.controllers import VirtualBox 

_vboxifaces = VirtualBox._ctx['ifaces']


class TestVirtualBoxController(unittest.TestCase):

  def __del__(self):
    shutil.rmtree(VBOX_FOLDER)

  def setUp(self):
    self.vb = reload(VirtualBox)
 
  def test_10createVM(self):
    _toStdMACSyntax = lambda s: \
      ':'.join([ s[i:i+2]  for i in range(0,len(s),2) ])

    IMAGE1_LOCATION = 'testVMImages/image1/cernvm-1.6.0-x86.vmdk'
    IMAGE2_LOCATION = 'testVMImages/image2/cernvm-1.6.0-x86.vmdk'
    def _checkResults(results):
      for s,r in results:
        self.assertTrue(s)
        self.assertIdentical( r[0], True )
        machineName = r[1]
        m = self.vb._findMachineByNameOrId(machineName)

        nic0 = m.getNetworkAdapter(0)
        nic0attachmentType = nic0.attachmentType
        self.assertEquals(_vboxifaces.NetworkAttachmentType_NAT, nic0attachmentType)

        nic1 = m.getNetworkAdapter(1)
        self.assertEquals(self.vb.getNamesToIdsMapping().get(machineName), \
            _toStdMACSyntax(nic1.MACAddress))

        nic1attachmentType = nic1.attachmentType
        self.assertEquals(_vboxifaces.NetworkAttachmentType_HostOnly, nic1attachmentType)

        hd = m.getMediumAttachment('SCSI', 0,0).medium
        if machineName == 'image1':
          self.assertSubstring(IMAGE1_LOCATION, hd.location)
        elif machineName == 'image2':
          self.assertSubstring(IMAGE2_LOCATION, hd.location)





    imagePath1 = os.path.join(sys.path[0], 
        IMAGE1_LOCATION)
    imagePath2 = os.path.join(sys.path[0], 
        IMAGE2_LOCATION)

    self.assertTrue(os.path.isfile(imagePath1))
    self.assertTrue(os.path.isfile(imagePath2))

    d1 = self.vb.createVM("image1", imagePath1)
    d2 = self.vb.createVM("image2", imagePath2)
    
    dl = defer.DeferredList([d1,d2])
    dl.addCallback( _checkResults )
    return dl


  def test_20listAvailableVMs(self):
    def _checkResults(results):
      self.assertIn( 'image1', results) 
      self.assertIn( 'image2', results) 

    d = self.vb.listAvailableVMs()
    d.addCallback( _checkResults )
    return d

  def test_30getState(self):
    self.assertEquals('PoweredOff', self.vb.getState('image1'))
    self.assertEquals('PoweredOff', self.vb.getState('image2'))

  def _test_40start(self):
    d = self.vb.start('image1')
    d.addCallback( self.assertIdentical, True)
    return d



