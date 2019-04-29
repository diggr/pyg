#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
from os.path import dirname, abspath, join

base_path = dirname(abspath(__file__))

with open(join(base_path, "README.md")) as readme_file:
    readme = readme_file.read()

with open(join(base_path, "requirements.txt")) as req_file:
    requirements = req_file.readlines()

setup(
    name="pyg",
    description='Passable Youtube Grabber - Datatools for youtube',
    long_description=readme,
    license="GPL-3.0",
    author='Diggr Team',
    author_email='team@diggr.link',
    url='https://github.com/diggr/pyg',
    packages=find_packages(exclude=['dev', 'docs']),
    package_dir={
            'pyg': 'pyg'
        },
    version="1.0.0",
    py_modules=["pyg", "analysis"],
    install_requires=requirements,
    include_package_data=True,
    entry_points="""
        [console_scripts]
        pyg=pyg.cli:cli
    """,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Scientific/Engineering',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'Topic :: System :: Logging',
    ],
    keywords=[
        'datamining', 'youtube', 'elasticsearch', 'data analysis', 'social media analysis'
    ],
)

