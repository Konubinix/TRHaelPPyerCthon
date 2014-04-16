#!/usr/bin/env python
# -*- coding:utf-8 -*-

import sys
from urllib import unquote

print unquote(sys.stdin.read()),
