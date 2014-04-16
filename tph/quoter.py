#!/usr/bin/env python
# -*- coding:utf-8 -*-

import sys
from urllib import quote

print quote(sys.stdin.read()),
