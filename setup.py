#!/usr/bin/env python
# -*- coding:utf-8 -*-

from setuptools import setup, find_packages

setup(
    name = 'TRHaelPPyerCthon',
    version = '0.0',
    packages = find_packages(),
    scripts = ['bin/trac_cmd.py', 'bin/trac_cmd_trac_hacks.sh', 'bin/trac_cmdrc_trachacks.conf'],
    author = "Konubinix",
    author_email = "konubinix@gmail.com",
    maintainer="Konubinix",
    maintainer_email="konubinix@gmail.com",
    install_requires = ["ConfigParser", "xmlrpclib"],
    description = """The Happy Trac RPC Python Helper.

TRHaelPPyerCthon is a set of functions to help you to be fast with trac
management. It is basically a wrapper around the awesome xml rpc plugin for trac
to perform meaningful tasks in one command.""",
    license = "GNU AFFERO GENERAL PUBLIC LICENSE",
    keywords = "",
    url = "",
    zip_safe = True
)
