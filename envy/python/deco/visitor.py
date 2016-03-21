import inspect

from ..stmt import *

from . import TRACE
from .want import *
from .stack import *

# visitors

VISITORS = {}

class _Visitor:
    __slots__ = 'func', 'wanted', 'flag'

    def __init__(self, func, wanted, flag=None):
        self.func = func
        self.wanted = [
            x if isinstance(x, Wantable) else SimpleWant(x)
            for x in reversed(wanted)
        ]
        self.flag = flag

    def visit(self, opcode, deco):
        if not deco.version.match(self.flag):
            raise NoMatch
        pos = len(deco.stack)
        prev = []
        for idx, want in enumerate(self.wanted):
            cur, pos = want.get(deco.stack, pos, opcode, prev, self.wanted[idx+1:])
            prev.append(cur)
        newstack = self.func(deco, opcode, *reversed(prev))
        if TRACE:
            print("\tVISIT {} [{} -> {}] {}".format(
                ', '.join(type(x).__name__ for x in deco.stack[:pos]),
                ', '.join(type(x).__name__ for x in deco.stack[pos:]),
                ', '.join(type(x).__name__ for x in newstack),
                type(opcode).__name__
            ))
        del deco.stack[pos:]
        return newstack

def register_visitor(func, op, stack, flag):
    if not isinstance(op, tuple):
        op = op,
    vis = _Visitor(func, stack, flag)
    for op in op:
        VISITORS.setdefault(op, []).append(vis)

def visitor(func):
    asp = inspect.getfullargspec(func)
    aself, aop, *astack = asp.args
    flag = asp.annotations.get(aself)
    stack = [asp.annotations[x] for x in astack]
    op = asp.annotations[aop]
    register_visitor(func, op, stack, flag)
    return func

def lsd_visitor(func):
    asp = inspect.getfullargspec(func)
    aself, aop, *astack = asp.args
    flag = asp.annotations.get(aself)
    stack = [asp.annotations[x] for x in astack]
    lop, sop, dop = asp.annotations[aop]

    def visit_lsd_load(self, op, *args):
        dst = func(self, op, *args)
        return [dst]

    def visit_lsd_store(self, op, *args):
        dst = func(self, op, *args)
        return [Store(dst)]

    def visit_lsd_delete(self, op, *args):
        dst = func(self, op, *args)
        return [StmtDel(dst)]

    register_visitor(visit_lsd_load, lop, stack, flag)
    register_visitor(visit_lsd_store, sop, stack, flag)
    register_visitor(visit_lsd_delete, dop, stack, flag)
    return func


from .inplace import *
from .lsd import *
from .token import *
from .expr import *
from .stmt import *
from .cmp import *
from .with_ import * # CLEAN
from .import_ import * # CLEAN
from .comp import *
from .finally_ import *
from .def_ import * # CLEAN
from .class_ import * # CLEAN
from .unpack import *
from .flow import * # XXX deps
from .raise_ import * # XXX deps
from .if_ import * # XXX deps
from .loop import * # XXX deps
from .for_ import * # XXX deps
from .except_ import * # XXX deps
