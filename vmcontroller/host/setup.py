#!/usr/bin/env python

import distribute_setup
distribute_setup.use_setuptools()

from setuptools import setup

setup(name='boincvm_host',
    version='0.5',
    description='Host side files for BOINC VM controller',
    author='David Garcia Quintas',
    author_email='dgquintas@gmail.com',
    url = 'http://bitbucket.org/dgquintas/boincvm/',
    scripts=['boincvm_host/boinc-host-controller.py'],
    packages=[
      'boincvm_host',
      'boincvm_host.controllers',
      'boincvm_host.controllers.scripts',
      'boincvm_host.stomp',
      'boincvm_host.xmlrpc',
      ],
    install_requires  = ['setuptools', 'twisted', 'stomper', 'netifaces',
                         'coilmq', 'simplejson'],
    classifiers=[
      "License :: OSI Approved :: GPL v2 or later License",
      "Programming Language :: Python",
      "Topic :: Virtual Machine Controller",
      "Topic :: Software Development :: Libraries :: Python Modules",
      "Intended Audience :: Developers",
      "Development Status :: 0.5"],
#    data_files =[ ('/etc/boinc-vm-controller', ['boincvm_host/HostConfig.cfg']), ] 
)
  
