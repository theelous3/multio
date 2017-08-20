#!/usr/bin/env python3

from setuptools import setup
from sys import version_info

ver = version_info[:2]
if ver < (3, 6):
    raise SystemExit('Sorry! multio requires python 3.6.0 or later.')

setup(
    name='multio',
    description='mulio - an unified async library for curio and trio',
    license='MIT',
    version='0.0.1',
    author='Mark Jameson - aka theelous3, and Akuli',
    url='https://github.com/theelous3/multio',
    packages=['multio'],
    tests_require=['pytest'],
    classifiers=['Programming Language :: Python :: 3']
)
