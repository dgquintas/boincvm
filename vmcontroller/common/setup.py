from distutils.core import setup

setup(name='boincvm_common',
    version='0.5',
    description='Common files for BOINC VM controller',
    author='David Garcia Quintas',
    author_email='dgquintas@gmail.com',
    packages=[
      'boincvm_common',

      'boincvm_common.stomp',
      'boincvm_common.stomp.protocol',
      ],
)

