from distutils.core import setup

setup(name='boincvm_vm',
    version='0.5',
    description='VM side files for BOINC VM controller',
    author='David Garcia Quintas',
    author_email='dgquintas@gmail.com',
    scripts=['boincvm_vm/boinc-vm-controller.py'],
    packages=[
      'boincvm_vm',
      
      'boincvm_vm.stomp',
      ],
    data_files =[ ('/etc/boinc-vm-controller', ['boincvm_vm/VMConfig.cfg']), ] 
)

