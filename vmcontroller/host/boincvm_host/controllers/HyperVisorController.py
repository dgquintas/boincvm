""" Instantiates the apropriate controller.

It follows the naming convention defined by appending 
the hypervisor name, as gotten from the provided configuration, 
with "Controller". Such a class must be exist and be accesible.

Note that if the controller class resides in a different package,
its name must include the package name as well.
"""
import boincvm_common.support as support

from twisted.internet import defer

import logging

logger = logging.getLogger( 'controllers.HyperVisorController' )

_controller = support.UninitializedPlaceholder("Please, use controllers.ControllerFactory to obtain the HyperVisorController") 

def start(vm):
  """start(vm)"""
  return defer.maybeDeferred( _controller.start, vm )

def powerOff(vm):
  """powerOff(vm)"""
  return defer.maybeDeferred( _controller.powerOff, vm )

def pause(vm): 
  """pause(vm)"""
  return defer.maybeDeferred( _controller.pause, vm )

def unpause(vm):
  """unpause(vm)"""
  return defer.maybeDeferred( _controller.unpause, vm )

def saveState(vm):
  """saveState(vm)"""
  return defer.maybeDeferred( _controller.saveState, vm )

def getState(vm):
  """getState(vm)"""
  return defer.maybeDeferred( _controller.getState, vm )

def saveSnapshot(vm, name, desc = ""):
  """saveSnapshot(vm, name, desc = "")"""
  return defer.maybeDeferred( _controller.saveSnapshot, vm, name, desc )

def restoreSnapshot(vm):
  """restoreSnapshot(vm)"""
  return defer.maybeDeferred( _controller.restoreSnapshot, vm )

def listAvailableVMs():
  """listAvailableVMs()"""
  return defer.maybeDeferred( _controller.listAvailableVMs )

def listRunningVMs():
  """listRunningVMs()"""
  return defer.maybeDeferred( _controller.listRunningVMs )

def getNamesToIdsMapping():
  """getNamesToIdsMapping"""
  return defer.maybeDeferred( _controller.getNamesToIdsMapping )

def getIdsToNamesMapping(): 
  """getIdsToNamesMapping"""
  return defer.maybeDeferred( _controller.getIdsToNamesMapping )

def getPerformanceData(vm):
  """getPerformanceData(vm)"""
  return defer.maybeDeferred( _controller.getPerformanceData, vm)

def createVM(name, hddImagePath):
  """createVM(name, hddImagePath)"""
  return defer.maybeDeferred( _controller.createVM, name, hddImagePath ) 


