#!/usr/bin/env python

from __future__ import absolute_import
from __future__ import print_function

import io
import re
from glob import glob
from os.path import basename, dirname, join, splitext

from setuptools import setup, find_packages

# stolen from https://blog.ionelmc.ro/2014/05/25/python-packaging/#the-setup-script

def read(*a, **kw):
  return io.open(
    join(dirname(__file__), *a),
    encoding=kw.get('encoding', 'utf8')
  ).read()

setup(
  name='schist',
  version=read('VERSION'),
  license='MIT',
  description='backup your zshhistory to a sqlite3 db',
  author='Jonathan Simms',
  author_email='jds@slyphon.com',
  url='https://github.com/slyphon/schist',
  packages=find_packages('src', exclude=['tests']),
  package_dir={'': 'src'},
  py_modules=[splitext(basename(path))[0] for path in glob('src/*.py')],
  python_requires='>2.7, <=3.7',
  install_requires=[
    'arrow>=0.12.0,<1.0'
    'python-dateutil>=2.6.1,<3.0',
    'six>=1.11.0,<2',
    'backports.functools-lru-cache>=1.4,<2.0',
  ],
  entry_points={
    'console_scripts': [
      'schist=schist:app'
    ]
  }
)
