from distutils.core import setup

setup(name='boincvm_host',
    version='0.5',
    description='Host side files for BOINC VM controller',
    author='David Garcia Quintas',
    author_email='dgquintas@gmail.com',
    scripts=['boincvm_host/boinc-host-controller.py'],
    packages=[
      'boincvm_host',

      'boincvm_host.controllers',
      'boincvm_host.controllers.scripts',

      'boincvm_host.stomp',

      'boincvm_host.xmlrpc',
      ],
#    data_files =[ ('/etc/boinc-vm-controller', ['boincvm_host/HostConfig.cfg']), ] 
)

