#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import sys
from urllib.parse import quote

print(quote(sys.stdin.read()), end=' ')
