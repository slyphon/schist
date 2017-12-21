#!/usr/bin/env python

from distutils.core import setup

VERSION='0.0.1' # @@VERSION@@

setup(
  name='zshbackup',
  version=VERSION,
  description='backup your zshhistory to a sqlite3 db',
  author='Jonathan Simms',
  author_email='jds@slyphon.com',
  url='https://github.com/slyphon/zsh-history-backup',
  packages = ['zshbackup'],
  python_requires='>2.7, <=3.7'
)

