#!/usr/bin/env python3

from setuptools import setup, find_packages
from sys import version_info

ver = version_info[:3]
min_py_ver = (3, 5, 2)
min_py_ver_str = '.'.join([str(x) for x in min_py_ver])
if ver < min_py_ver:
    raise SystemExit('Sorry! multio requires python {} or later.'.format(min_py_ver_str))

setup(
    name='multio',
    description='multio - an unified async library for curio and trio',
    license='MIT',
    version='0.2.5',
    author='theelous3, SunDwarf, and Akuli',
    url='https://github.com/theelous3/multio',
    python_requires=">={}".format(min_py_ver_str),
    packages=find_packages(),
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
