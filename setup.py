#!/usr/bin/env python3

from setuptools import setup
from sys import version_info

ver = version_info[:3]
if ver < (3, 5, 2):
    raise SystemExit('Sorry! multio requires python 3.5.2 or later.')

setup(
    name='multio',
    description='multio - an unified async library for curio and trio',
    license='MIT',
    version='0.2.3',
    author='theelous3, SunDwarf, and Akuli',
    url='https://github.com/theelous3/multio',
    python_requires=">=3.5.2",
    packages=[
        'multio'
    ],
    classifiers=[
        'Programming Language :: Python :: 3',
        'Framework :: Trio',
    ],
    extras_require={
        'curio': [
            'curio>=0.7.0'
        ],
        'trio': [
            'trio>=0.2.0'
        ]
    }
)
