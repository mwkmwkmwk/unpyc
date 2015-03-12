#!/usr/bin/env python3

"""A python decompiler.

Turns pyc files back into readable py source.  General mode of operation is
as follows:

1. envy.format.pyc and .marshal read the pyc file and deserialize it into
   structures similiar to those used by Python internally at runtime.
2. envy.python.code and .bytecode walk the structures and parse the bytecode
   embedded in code objects - we effectively get a disassembler at this point.
3. envy.python.deco turns the opcode lists into statements, gradually merging
   them and connecting the blocks together.  The code at this stage is in
   a superset of Python that allows describing all opcodes on their own.
4. envy.python.ast converts the code into python AST and puts finishing touches
   on it.  The AST is then printed.

While decompilation is fairly accurate, some information is irreversibly lost:

1. Comments, all of them.  Sorry.

   This includes the encoding comment at the top, as well as the shebang line.
   There's little point in recovering shebang, and it's impossible anyway.
   The encoding comment is quite important, however - it determines how
   unicode strings should be represented in the decompiled output.  Perhaps
   we could add a commandline option to set the encoding...

2. Likewise, all information about horizontal code layout is gone -
   indentation, spaces before/after operators, etc.  Line numbers are
   preserved, so we can roughly recover the vertical layout, but it only
   really works on whole-statement level - if a single statement is spread
   over a few lines, recovering the exact layout is messy and/or impossible.

   There are two heuristics we could attempt here:

   - recover the general indentation convention (amount, tabs vs spaces) from
     junk left in docstrings, if present.  Not half bad.
   - for long statements (esp. long list or dict literals), figure out roughly
     how much vertical space they take, and try various layouts until we get
     roughly the right amount of lines.  Ew.

3. If you happen to be using -O, all assert statements are *gone*.  Sorry.

4. If you happen to be using -OO, all docstrings are likewise gone.

5. Dead code: depending on version, dead code may or may not be retained
   in pyc code.  This includes things like:

    3 # loose literal (other than docstring)

    if 0: # always false condition - the whole block removed
        ...

    if 1: # always true condition - if statement removed, contents hoisted up
        ...

    if x:
        return 3
        foo() # code after return

6. "return None" cannot always be distinguished from implicit None return by
   falling off the end of the function.

7. Const folding: 2 + 2 will become 4.

8. 'in' optimization: x in [1, 2, 3] is optimized to x in (1, 2, 3).
"""

import sys

from envy.format.pyc import PycFile
from envy.python.code import Code

for fname in sys.argv[1:]:
    print("{}...".format(fname))
    with open(fname, 'rb') as fp:
        pyc = PycFile(fp)

    pyc.print()

    code = Code(pyc.code, pyc.version)
    sys.stdout.write(code.show(0))
