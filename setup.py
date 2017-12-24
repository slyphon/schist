#!/usr/bin/env python

from setuptools import setup

VERSION='0.0.1' # @@VERSION@@

setup(
  name='schist',
  version=VERSION,
  description='backup your zshhistory to a sqlite3 db',
  author='Jonathan Simms',
  author_email='jds@slyphon.com',
  url='https://github.com/slyphon/zsh-history-backup',
  packages = ['schist'],
  python_requires='>2.7, <=3.7',
  install_requires=[
    'arrow>=0.12.0,<1.0'
    'python-dateutil>=2.6.1,<3.0',
    'six>=1.11.0,<2',
    'backports.functools-lru-cache>=1.4,<2.0',
  ]
)
