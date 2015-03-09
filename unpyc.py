#!/usr/bin/env python3

import sys

from envy.format.pyc import PycFile
from envy.python.code import Code

with open(sys.argv[1], 'rb') as fp:
    pyc = PycFile(fp)

#pyc.print()

code = Code(pyc.code, pyc.version)
sys.stdout.write(code.show(0))
