#!/usr/bin/env python

from setuptools import setup, Extension

# May need to adjust these to suit your system, but a standard installation of the BOINC client from source will put things in these places
boinc = Extension('boinc', runtime_library_dirs=['./boinc-linux-i386/lib/'],
	extra_objects=['./boinc-linux-i386/lib/libboinc.a', './boinc-linux-i386/lib/libboinc_api.a'],
	sources = ['./boincmodule.c'],
	libraries = ['stdc++', 'boinc', 'boinc_api', 'dl','crypto','ssl'],
	library_dirs = ['/usr/local/lib/', './boinc-linux-i386/lib/'],
	include_dirs = ['./boinc-linux-i386/include/'],
	extra_compile_args = ['-fPIC'], extra_link_args = ['-fPIC'])

setup (name = 'PyBoinc',
       version = '0.3.2',
       description = 'Basic python bindings for BOINC network computing package',
       author = 'David Weir',
       author_email = 'david.weir03@imperial.ac.uk',
       url = 'http://plato.tp.ph.ic.ac.uk/~djw03/boinc-python/',
       #packages = ['pyboinc'],
       install_requires  = ['setuptools'],
       long_description = """
       Python bindings for BOINC APIs.
       """,
       classifiers=[
          "License :: OSI Approved :: GPL v2 or later License",
          "Programming Language :: Python",
          "Topic :: Distributive Computing",
          "Topic :: Software Development :: Libraries :: Python Modules",
          "Intended Audience :: Developers",
          "Development Status :: 0.3.2"],
       ext_modules = [boinc]
       )
