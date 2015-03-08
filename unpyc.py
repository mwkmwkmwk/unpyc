#!/usr/bin/env python3

import sys

from envy.format.pyc import PycFile

with open(sys.argv[1], 'rb') as fp:
    pyc = PycFile(fp)

pyc.print()
