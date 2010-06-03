""" Controller for the VirtualBox hypervisor.

"""
#to avoid conflicting with VB's own MachineState symbol
from boincvm_host.controllers import MachineState as GenericMachineState 
from boincvm_common import support
from boincvm_common import Exceptions 

from twisted.internet import protocol, reactor, defer, threads

import logging
import os
import platform
import sys
import uuid


WAITING_GRACE_MS = 30000  #FIXME: magic number of milliseconds

logger = logging.getLogger(__name__)



######## PUBLIC API ################

def start(vm):
  vbox = _ctx['vbox']
  mgr = _ctx['mgr']
  #what an ugly hack this is...
  if platform.system() != "Windows":
    def impl():
      m = _findMachineByNameOrId(vm)
      mId = m.id
      session = mgr.getSessionObject(vbox)
      logger.info("Starting VM for machine %s" % m.name)
      progress = vbox.openRemoteSession(session, mId, "vrdp", "")
      progress.waitForCompletion(WAITING_GRACE_MS) 
      completed = progress.completed
      logger.info("Startup of machine %s completed: %s" % (m.name, str(completed)))
      session.close() 
        
      return True 
    d = threads.deferToThread(impl)
    

  else:
    m = _findMachineByNameOrId(vm)
    mName = str(m.name)
    processProtocol = VBoxHeadlessProcessProtocol()
    pseudoCWD = os.path.dirname(sys.modules[__name__].__file__)
    vboxBinariesPath = None #TODO: use VBOX_INSTALL_PATH
    cmdWithPath = os.path.join(pseudoCWD, 'scripts', 'vboxstart.bat')
    cmdWithArgs = ("vboxstart.bat", vboxBinariesPath, mName)
    cmdPath = os.path.join(pseudoCWD, 'scripts')
    newProc = lambda: reactor.spawnProcess( processProtocol, cmdWithPath, args=cmdWithArgs, env=None, path=cmdPath )
    reactor.callWhenRunning(newProc)
    d = True #in order to have a unique return 

  try:
    _startCollectingPerfData(vm)
  except:
    pass #TODO: loggging
  
  logger.debug("Controller method %s invoked" % support.discoverCaller() )
  return d



def powerOff(vm):
  def impl():
    session = _getSessionForVM(vm)
    console = session.console
    try:
#      progress = console.powerDownAsync() 
#      progress.waitForCompletion(-1) #XXX
      console.powerButton()
    finally:
      session.close()

    return True

  logger.debug("Controller method %s invoked" % support.discoverCaller() )
  d = threads.deferToThread( impl )
  return d



def pause(vm): 
  def impl():
    session = _getSessionForVM(vm)
    console = session.console
    try:
      console.pause() 
    finally:
      session.close()

    return True

  logger.debug("Controller method %s invoked" % support.discoverCaller() )
  d = threads.deferToThread( impl )
  return d

def unpause(vm):
  def impl():
    session = _getSessionForVM(vm)
    console = session.console
    try:
      console.resume()
    finally:
      session.close()

    return True

  logger.debug("Controller method %s invoked" % support.discoverCaller() )
  d = threads.deferToThread( impl )
  return d

def saveState(vm):
  def impl():
    session = _getSessionForVM(vm)
    console = session.console
    try:
      progress = console.saveState()
      progress.waitForCompletion(WAITING_GRACE_MS)
    finally:
      session.close()

    return True

  logger.debug("Controller method %s invoked" % support.discoverCaller() )
  d = threads.deferToThread( impl )
  return d


def saveSnapshot( vm, name, desc):
  def impl():
    session = _getSessionForVM(vm)
    console = session.console
    try:
      progress = console.takeSnapshot(name, desc) 
      progress.waitForCompletion(-1) #XXX
    finally:
      session.close()

    return True

  logger.debug("Controller method %s invoked" % support.discoverCaller() )
  d = threads.deferToThread( impl )
  return d

def restoreSnapshot(vm):
  def impl():
    session = _getSessionForVM(vm)
    console = session.console
    try:
      progress = console.discardCurrentState()
      progress.waitForCompletion(-1) #XXX
    finally:
      session.close()

    return True

  logger.debug("Controller method %s invoked" % support.discoverCaller() )
  d = threads.deferToThread( impl )
  return d

def getState( vm): 
  def _getNameForMachineStateCode(c):
    d = _ctx['ifaces']._Values['MachineState']
    revD = [k for (k,v) in d.iteritems() if v == c]
    return revD[0]

  logger.debug("Controller method %s invoked" % support.discoverCaller() )
  
  vbox = _ctx['vbox']
  m = vbox.findMachine(vm)
  stateCode = m.state
  stateName = _getNameForMachineStateCode(stateCode)
  return stateName

def listAvailableVMs():
  def impl():
    vbox = _ctx['vbox']
    ms = _getMachines()
    msNames = [ str(m.name) for m in ms ]
    return msNames
  logger.debug("Controller method %s invoked" % support.discoverCaller() )
  d = threads.deferToThread(impl)
  return d

def listRunningVMs():
  def impl():
    vbox = _ctx['vbox']
    ms = _getMachines()
    isRunning = lambda m: m.state ==  _ctx['ifaces'].MachineState_Running
    res = filter( isRunning, ms )
    res = [ str(m.name) for m in res ]
    return res
  
  logger.debug("Controller method %s invoked" % support.discoverCaller() )
  d = threads.deferToThread(impl)
  return d

def getNamesToIdsMapping(): 
  macToName = _getMACToNameMapping()
  nameToMac = support.reverseDict(macToName)
  return nameToMac

def getIdsToNamesMapping(): 
  macToName = _getMACToNameMapping()
  return macToName


def getPerformanceData(vm):
  def impl():
    return _perf.query( ["*"], [vm] )
    
  logger.debug("Controller method %s invoked" % support.discoverCaller() )
  d = threads.deferToThread(impl)
  return d
  

def createVM(name, hddImagePath):
  vbox = _ctx['vbox']
  mgr = _ctx['mgr']
  def impl():
    ms = _getMachines()
    for m in ms:
      if m.name == name:
        raise ValueError("VM '%s' already exists" % name)
    guestType = vbox.getGuestOSType('Linux26') 
    newMachine = vbox.createMachine(name, guestType.id, "", "00000000-0000-0000-0000-000000000000", False)
    if not os.path.isfile( hddImagePath ):
      raise IOError("HDD image path doesn't point to a valid file: %s" % hddImagePath )
      
    try:
      newMachine.saveSettings()
      #register the machine with VB (ie, make it visible)
      vbox.registerMachine( newMachine )
      
      session = mgr.getSessionObject(vbox)
      vbox.openSession( session, newMachine.id )
      mutableM = session.machine
      _attachNICs( mutableM )
      _addSCSIStorageController( mutableM )
      _attachHDToMachine( mutableM, hddImagePath )
    except Exception, e: 
      if session.state == _ctx['ifaces'].SessionState_Open :
        session.close()

      m = vbox.unregisterMachine(newMachine.id)
      m.deleteSettings()
      msg = "Rolled back creation of VM '%s'" % m.name
      logger.debug(msg)

      #the following two lines should go in a finally:,
      #but that's not supported by python 2.4
      if session.state == _ctx['ifaces'].SessionState_Open:
        session.close()

      raise

    #the following two lines should go in a finally:,
    #but that's not supported by python 2.4
    if session.state == _ctx['ifaces'].SessionState_Open:
      session.close()

    return (True, name)

  logger.debug("Controller method %s invoked" % support.discoverCaller() )
  d = threads.deferToThread( impl )
  return d

######### internal methods follow #################

def _attachNICs(mutableM):
  vbox = _ctx['vbox']
  def _findHostOnlyInterface():
    host = vbox.host
    for iface in host.getNetworkInterfaces():
      if iface.interfaceType == _ctx['ifaces'].HostNetworkInterfaceType_HostOnly:
        return iface
    else:
      raise ValueError('No Host-Only interface found on the host')

  nic0 = mutableM.getNetworkAdapter(0) #NAT
  nic1 = mutableM.getNetworkAdapter(1) #host-only

  nic0.attachToNAT()
  nic0.enabled = True

  nic1.attachToHostOnlyInterface()
  hostOnlyIface = _findHostOnlyInterface()
  nic1.hostInterface = hostOnlyIface.name
  nic1.enabled = True

  mutableM.saveSettings()

def _addSCSIStorageController(mutableM):
  newController = mutableM.addStorageController('SCSI', _ctx['ifaces'].StorageBus_SCSI )
  newController.controllerType = _ctx['ifaces'].StorageControllerType_LsiLogic

  mutableM.saveSettings()

def _attachHDToMachine(mutableM, hddImagePath):
  vbox = _ctx['vbox']
  mgr = _ctx['mgr']

#function _assignRandomUUIDToHD not useful anymore:
#VBox fixed the bug the prevented assignation of uuid
#in the openHardDisk method
#  def _assignRandomUUIDToHD():
#    UUID_LINE_KEY = 'ddb.uuid.image' #XXX: always?
#    hdd = file(hddImagePath, 'r+b')
#    pos = 0
#    for l in hdd: #it should be around line 20
#      if l.startswith(UUID_LINE_KEY):
#        newUUIDLine = '%s="%s"' % (UUID_LINE_KEY, uuid.uuid4())
#        msg = "Using '%s' as the new UUID line for HDD image '%s'" % \
#            (newUUIDLine, hddImagePath)
#        logger.debug(msg)
#        hdd.seek(pos)
#        hdd.write(newUUIDLine)
#        hdd.close()
#        break
#      pos += len(l)
#    return
#
#  #_assignRandomUUIDToHD()

  newUUID = str(uuid.uuid4())
  hdd = vbox.openHardDisk(hddImagePath, _ctx['ifaces'].AccessMode_ReadWrite, True, newUUID, False, '')
  hddId = hdd.id
  mutableM.attachDevice('SCSI', 0, 0, _ctx['ifaces'].DeviceType_HardDisk, hddId ) 
  mutableM.saveSettings()


def _startCollectingPerfData(vm):
  _perf.setup(["*"], [vm], 10, 15) #FIXME: magic numbers: period, count

def _getMachines():
  return _ctx['vboxmgr'].getArray(_ctx['vbox'], 'machines')

def _findMachineByNameOrId(vm):
  vbox = _ctx['vbox']
  for m in _getMachines():
    if (m.name == vm) or (m.id == vm):
      res = m
      break
  else: #only reached if "break" never exec'd
    raise Exceptions.NoSuchVirtualMachine(str(vm))
  
  return res 

def _getSessionForVM(vm):
  vbox = _ctx['vbox']
  mgr = _ctx['mgr']
  session = mgr.getSessionObject(vbox)
  m = _findMachineByNameOrId(vm) 
  try:
    vbox.openExistingSession(session, m.id)
  except:
    vbox.openSession(session, m.id)
  return session 



def _getMACToNameMapping():
  vbox = _ctx['vbox']
  def numsToColonNotation(nums):
    nums = str(nums)
    #gotta insert a : every two number, except for the last group.
    g = ( nums[i:i+2] for i in xrange(0, len(nums), 2) )
    return ':'.join(g)
  vbox = _ctx['vbox']
  ms = _getMachines()
  entriesGen = ( ( numsToColonNotation(m.getNetworkAdapter(1).MACAddress), str(m.name) ) 
      for m in _getMachines() ) 
  #entriesGen = ( ( m.getNetworkAdapter(1).MACAddress, str(m.name) ) for m in _getMachines() )

  mapping = dict(entriesGen)
  return mapping


def _initVRDPPorts():
  mgr = _ctx['mgr']
  vbox = _ctx['vbox']
  for i, m in enumerate(_getMachines()):
    if m.sessionState == _ctx['ifaces'].SessionState_Closed:

      session = mgr.getSessionObject(vbox)
      try: 
        vbox.openSession( session, m.id )
        mutableM = session.machine
        if mutableM.state == _ctx['ifaces'].MachineState_PoweredOff:
          vrdpServer = mutableM.VRDPServer
          vrdpServer.authType = _ctx['ifaces'].VRDPAuthType_Null
          vrdpPort = 3389 + i+1 
          vrdpServer.ports = str(vrdpPort)
          logger.debug("VRDP port set to %d for VM %s" % (vrdpPort, mutableM.name))
          mutableM.saveSettings()
        
      finally:
        if session.state == _ctx['ifaces'].SessionState_Open:
          session.close()
    else:
      logger.debug("Ignoring %s (Session state '%s')" % (m.name, m.sessionState))


class _VBoxHeadlessProcessProtocol(protocol.ProcessProtocol):

  logger = logging.getLogger( support.discoverCaller() )

  def connectionMade(self):
    self.transport.closeStdin()
    self.logger.debug("VBoxHeadless process started!")

  def outReceived(self, data):
    self.logger.debug("VBoxHeadless stdout: %s" % data)
  def errReceived(self, data):
    self.logger.debug("VBoxHeadless stderr: %s" % data)

  def inConnectionLost(self):
    pass #we don't care about stdin. We do in fact close it ourselves

  def outConnectionLost(self):
    self.logger.info("VBoxHeadless closed its stdout")
  def errConnectionLost(self):
    self.logger.info("VBoxHeadless closed its stderr")

  def processExited(self, reason):
    #This is called when the child process has been reaped 
    pass
  def processEnded(self, reason):
    #This is called when all the file descriptors associated with the child
    #process have been closed and the process has been reaped
    self.logger.warn("Process ended (code: %s) " % reason.value.exitCode)



############ INITIALIZATION ######################

from vboxapi import VirtualBoxManager
_vboxmgr = VirtualBoxManager(None, None)
_ctx = { 
        'vboxmgr': _vboxmgr,
        'ifaces': _vboxmgr.constants,
        'vbox': _vboxmgr.vbox,
        'mgr': _vboxmgr.mgr
      }
_initVRDPPorts()

