#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import sys
from urllib.parse import unquote

print(unquote(sys.stdin.read()), end=' ')
