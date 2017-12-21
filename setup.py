#!/usr/bin/env python

from distutils.core import setup

setup(
  name='slyphon_zshhist_backup',
  version=open('VERSION').read().strip(),
  description='backup your zshhistory to a sqlite3 db',
  author='Jonathan Simms',
  author_email='jds@slyphon.com',
  url='https://github.com/slyphon/zsh-history-backup',
  package_dir = {'': 'src'},
  packages = ['slyphon.zshbackup'],
)

