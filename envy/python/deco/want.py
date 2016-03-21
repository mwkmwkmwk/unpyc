# wantables

from ..code import Code
from .stack import *

class Wantable:
    def __init__(self, name, bases, namespace):
        self.__dict__.update(namespace)

    def get(self, stack, pos, opcode, prev, next):
        top = stack[pos-1] if pos else None
        cnt = self.count(top, opcode, prev)
        newpos = pos - cnt
        if newpos < 0:
            raise NoMatch
        return self.parse(stack[newpos:pos], opcode), newpos


class Exprs(Wantable):
    __slots__ = 'attr', 'factor'
    def __init__(self, attr, factor):
        self.attr = attr
        self.factor = factor

    def count(self, top, opcode, prev):
        return getattr(opcode, self.attr) * self.factor

    def parse(self, res, opcode):
        if not all(isinstance(x, Expr) for x in res):
            raise NoMatch
        if self.factor != 1:
            res = list(zip(*[iter(res)] * self.factor))
        return res


class UglyClosures(metaclass=Wantable):
    def count(top, opcode, prev):
        assert prev
        code = prev[-1]
        assert isinstance(code, Code)
        return len(code.freevars)

    def parse(res, opcode):
        if not all(isinstance(x, Closure) for x in res):
            raise NoMatch
        return [x.var for x in res]


class Closures(metaclass=Wantable):
    def count(top, opcode, prev):
        return opcode.param

    def parse(res, opcode):
        if not all(isinstance(x, Closure) for x in res):
            raise NoMatch
        return [x.var for x in res]


class MaybeWantFlow(metaclass=Wantable):
    def count(top, opcode, prev):
        if isinstance(top, WantFlow):
            return 1
        else:
            return 0

    def parse(res, opcode):
        if res:
            return res[0]
        else:
            return WantFlow([], [], [])


class LoopDammit(metaclass=Wantable):
    def get(stack, pos, opcode, prev, next):
        for idx, item in enumerate(next):
            if isinstance(item, SimpleWant) and item.cls is Loop:
                break
        else:
            assert 0
        orig = pos
        pos -= 1
        while pos >= 0 and not isinstance(stack[pos], Loop):
            pos -= 1
        if pos < 0:
            raise NoMatch
        pos += 1 + idx
        return stack[pos:orig], pos


class SimpleWant(Wantable):
    def __init__(self, cls):
        self.cls = cls

    def count(self, top, opcode, prev):
        return 1

    def parse(self, res, opcode):
        res, = res
        if not isinstance(res, self.cls):
            raise NoMatch
        return res


class WantIfOp(Wantable):
    def __init__(self, want, op):
        self.want = want if isinstance(want, Wantable) else SimpleWant(want)
        self.op = op

    def get(self, stack, pos, opcode, prev, next):
        if isinstance(opcode, self.op):
            return self.want.get(stack, pos, opcode, prev, next)
        else:
            return None, pos
