from enum import IntEnum

from envy.format.marshal import (
    MarshalNone,
    MarshalBool,
    MarshalEllipsis,
    MarshalInt,
    MarshalLong,
    MarshalFloat,
    MarshalComplex,
    MarshalString,
    MarshalUnicode,
    MarshalTuple,
    MarshalFrozenset,
)

from .helpers import PythonError

class CmpOp(IntEnum):
    LT = 0
    LE = 1
    EQ = 2
    NE = 3
    GT = 4
    GE = 5
    IN = 6
    NOT_IN = 7
    IS = 8
    IS_NOT = 9
    EXC_MATCH = 10

COMPARE_OPS = {
    CmpOp.LT: '<',
    CmpOp.LE: '<=',
    CmpOp.EQ: '==',
    CmpOp.NE: '!=',
    CmpOp.GT: '>',
    CmpOp.GE: '>=',
    CmpOp.IN: 'in',
    CmpOp.NOT_IN: 'not in',
    CmpOp.IS: 'is',
    CmpOp.IS_NOT: 'is not',
}

# TODO: print unicode/byte strings as appropriate for the python version
# TODO: context-aware printing
# TODO: nuke frozenset from load_from_marshal


class Expr:
    __slots__ = 'version',

    def __init__(self, version):
        self.version = version


# singletons

class ExprNone(Expr):
    __slots__ = ()

    def show(self, ctx):
        return 'None'


class ExprEllipsis(Expr):
    __slots__ = ()

    def show(self, ctx):
        return "..."

# literals

class ExprSimple(Expr):
    __slots__ = 'val',

    def __init__(self, version, val):
        super().__init__(version)
        self.val = val


class ExprBool(ExprSimple):
    __slots__ = ()

    def show(self, ctx):
        return str(self.val)


class ExprInt(ExprSimple):
    __slots__ = ()

    def show(self, ctx):
        return str(self.val)


class ExprLong(ExprSimple):
    __slots__ = ()

    def show(self, ctx):
        return str(self.val) + 'L'


class ExprFloat(ExprSimple):
    __slots__ = ()

    def show(self, ctx):
        return str(self.val)


class ExprComplex(ExprSimple):
    __slots__ = ()

    def show(self, ctx):
        return str(self.val)


class ExprString(ExprSimple):
    __slots__ = ()

    def show(self, ctx):
        # XXX
        return repr(self.val)


class ExprUnicode(ExprSimple):
    __slots__ = ()

    def show(self, ctx):
        # XXX
        return repr(self.val)

# containers

class ExprSequence(Expr):
    __slots__ = 'exprs',

    def __init__(self, version, exprs):
        super().__init__(version)
        self.exprs = exprs


class ExprTuple(ExprSequence):
    __slots__ = ()

    def show(self, ctx):
        # XXX
        return '({}{})'.format(
            ', '.join(v.show(ctx) for v in self.exprs),
            ',' if len(self.exprs) == 1 else ''
        )


class ExprList(ExprSequence):
    __slots__ = ()

    def show(self, ctx):
        # XXX
        return '[{}]'.format(
            ', '.join(v.show(ctx) for v in self.exprs),
        )


class ExprDict(Expr):
    __slots__ = 'items',

    def __init__(self, version, items):
        super().__init__(version)
        self.items = items

    def show(self, ctx):
        return '{{{}}}'.format(
            ', '.join(
                '{}: {}'.format(k.show(ctx), v.show(ctx))
                for k, v in self.items
            ),
        )


# unary

class ExprUn(Expr):
    __slots__ = 'e1',

    def __init__(self, version, e1):
        super().__init__(version)
        self.e1 = e1

    def show(self, ctx):
        # XXX
        return '({}{})'.format(self.sign, self.e1.show(ctx))


class ExprPos(ExprUn):
    __slots__ = ()
    sign = '+'


class ExprNeg(ExprUn):
    __slots__ = ()
    sign = '-'


class ExprNot(ExprUn):
    __slots__ = ()
    sign = 'not '


class ExprRepr(ExprUn):
    __slots__ = ()

    def show(self, ctx):
        # XXX
        return '(`{}`)'.format(self.e1.show(ctx))


class ExprInvert(ExprUn):
    __slots__ = ()
    sign = '~'


# binary

class ExprBin(Expr):
    __slots__ = 'e1', 'e2'

    def __init__(self, version, e1, e2):
        super().__init__(version)
        self.e1 = e1
        self.e2 = e2

    def show(self, ctx):
        # XXX
        return '({} {} {})'.format(self.e1.show(ctx), self.sign, self.e2.show(ctx))


class ExprMul(ExprBin):
    __slots__ = ()
    sign = '*'


class ExprDiv(ExprBin):
    __slots__ = ()
    sign = '/'


class ExprMod(ExprBin):
    __slots__ = ()
    sign = '%'


class ExprAdd(ExprBin):
    __slots__ = ()
    sign = '+'


class ExprSub(ExprBin):
    __slots__ = ()
    sign = '-'


class ExprShl(ExprBin):
    __slots__ = ()
    sign = '<<'


class ExprShr(ExprBin):
    __slots__ = ()
    sign = '>>'


class ExprAnd(ExprBin):
    __slots__ = ()
    sign = '&'


class ExprOr(ExprBin):
    __slots__ = ()
    sign = '|'


class ExprXor(ExprBin):
    __slots__ = ()
    sign = '^'


class ExprBoolAnd(ExprBin):
    __slots__ = ()
    sign = 'and'


class ExprBoolOr(ExprBin):
    __slots__ = ()
    sign = 'or'


# compares

class ExprCmp(Expr):
    __slots__ = ('items')

    def __init__(self, version, items):
        super().__init__(version)
        self.items = items

    def show(self, ctx):
        return '({})'.format(' '.join(
            COMPARE_OPS[item]
            if isinstance(item, CmpOp)
            else item.show(ctx)
            for item in self.items
        ))


# attributes, indexing

class ExprAttr(Expr):
    __slots__ = 'expr', 'name'

    def __init__(self, version, expr, name):
        super().__init__(version)
        self.expr = expr
        self.name = name

    def show(self, ctx):
        return '({}).{}'.format(self.expr.show(ctx), self.name)


class ExprSubscr(ExprBin):
    __slots__ = ()

    def show(self, ctx):
        return '{}[{}]'.format(self.e1.show(ctx), self.e2.show(ctx))


class ExprSlice(Expr):
    __slots__ = 'expr', 'start', 'end', 'step'

    def __init__(self, version, expr, start, end, step=None):
        super().__init__(version)
        self.expr = expr
        self.start = start
        self.end = end
        self.step = step

    def show(self, ctx):
        def maybe(x):
            return x.show(ctx) if x is not None else ''
        if self.step is None:
            return '{}[{}:{}]'.format(self.expr.show(ctx), maybe(self.start), maybe(self.end))
        else:
            return '{}[{}:{}:{}]'.format(self.expr.show(ctx), maybe(self.start), maybe(self.end), self.step.show(ctx))


# calls

class ExprCall(Expr):
    __slots__ = 'expr', 'params'

    def __init__(self, version, expr, params):
        super().__init__(version)
        self.expr = expr
        self.params = params

    def show(self, ctx):
        return '{}({})'.format(
            self.expr.show(ctx),
            ', '.join(
                param.show(ctx)
                for param in self.params
            )
        )


# names

class ExprName(Expr):
    __slots__ = 'name',

    def __init__(self, version, name):
        super().__init__(version)
        self.name = name

    def show(self, ctx):
        return self.name

# just get rid of it.

class ExprFrozenset(Expr):
    __slots__ = 'exprs',

    def __init__(self, version, exprs):
        super().__init__(version)
        self.exprs = exprs

    def show(self, ctx):
        # XXX
        return '$frozenset([{}])'.format(', '.join(v.show(ctx) for v in self.exprs))


def from_marshal(obj, version):
    if isinstance(obj, MarshalNone):
        return ExprNone(version)
    if isinstance(obj, MarshalBool):
        return ExprBool(version, obj.val)
    if isinstance(obj, MarshalEllipsis):
        return ExprEllipsis(version)
    if isinstance(obj, MarshalInt):
        return ExprInt(version, obj.val)
    if isinstance(obj, MarshalLong):
        return ExprLong(version, obj.val)
    if isinstance(obj, MarshalFloat):
        return ExprFloat(version, obj.val)
    if isinstance(obj, MarshalComplex):
        return ExprComplex(version, obj.val)
    if isinstance(obj, MarshalString):
        return ExprString(version, obj.val)
    if isinstance(obj, MarshalUnicode):
        return ExprUnicode(version, obj.val)
    if isinstance(obj, MarshalTuple):
        return ExprTuple(version, [from_marshal(sub, version) for sub in obj.val])
    if isinstance(obj, MarshalFrozenset):
        return ExprFrozenset(version, [from_marshal(sub, version) for sub in obj.val])
    raise PythonError("can't map {} to expression".format(type(obj)))
