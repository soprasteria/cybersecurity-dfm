#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"Data Feed Manager Setup file"

from distutils.core import setup
from setuptools import setup, find_packages


with open('README.rst') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='dfm',
    version='0.3',
    description='Dynamic Feed Manager',
    long_description=readme,
    author='Alexandre CABROL PERALES',
    author_email='alexandre.cabrol@soprasteria.com',
    url='https://github.com/soprasteria/cybersecurity-dfm',
    license=license,
    install_requires=[
     'feedparser',
     'tweepy',
     'newspaper',
     'readability-lxml',
     'bs4',
     'langdetect',
     'unicodecsv',
     'iso8601',
     'flask',
     'flask-restful',
     'Werkzeug',
     'elasticsearch',
     'Sphinx',
     'sphinxcontrib-httpdomain',
     'praw',
     'pycallgraph',
     'pylint',
     'sphinx-pyreverse',
     'sphinx_rtd_theme',
     'sphinx_git',
     'memory_profiler',
     'selenium',
     'textract',
     'python-magic',
     'sumy'
    ],
    packages=find_packages(exclude=('tests','utils'))
)
