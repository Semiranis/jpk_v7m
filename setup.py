# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

with open('requirements.txt') as f:
	install_requires = f.read().strip().split('\n')

# get version from __version__ variable in jpk_v7m/__init__.py
from jpk_v7m import __version__ as version

setup(
	name='jpk_v7m',
	version=version,
	description='Experimental app for JPK_V7M',
	author='Levitating Frog',
	author_email='none',
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
