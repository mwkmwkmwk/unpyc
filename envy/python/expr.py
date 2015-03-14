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
    __slots__ = ()


# singletons

class ExprNone(Expr):
    __slots__ = ()

    def subprocess(self, process):
        return self

    def show(self, ctx):
        return 'None'


class ExprEllipsis(Expr):
    __slots__ = ()

    def show(self, ctx):
        return "..."

# literals

class ExprSimple(Expr):
    __slots__ = 'val',

    def subprocess(self, process):
        return self

    def __init__(self, val):
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

    def __init__(self, exprs):
        self.exprs = exprs

    def subprocess(self, process):
        return type(self)([process(expr) for expr in self.exprs])


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

    def __init__(self, items):
        self.items = items

    def subprocess(self, process):
        return ExprDict([
            (process(k), process(v))
            for k, v in self.items
        ])

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

    def __init__(self, e1):
        self.e1 = e1

    def subprocess(self, process):
        return type(self)(process(self.e1))

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

    def __init__(self, e1, e2):
        self.e1 = e1
        self.e2 = e2

    def subprocess(self, process):
        return type(self)(process(self.e1), process(self.e2))

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

    def __init__(self, items):
        self.items = items

    def subprocess(self, process):
        return ExprCmp([
            process(item) if isinstance(item, Expr) else item
            for item in self.items
        ])

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

    def __init__(self, expr, name):
        self.expr = expr
        self.name = name

    def subprocess(self, process):
        return ExprAttr(process(self.expr), self.name)

    def show(self, ctx):
        return '({}).{}'.format(self.expr.show(ctx), self.name)


class ExprSubscr(ExprBin):
    __slots__ = ()

    def show(self, ctx):
        return '{}[{}]'.format(self.e1.show(ctx), self.e2.show(ctx))


class ExprSlice(Expr):
    __slots__ = 'expr', 'start', 'end', 'step'

    def __init__(self, expr, start, end, step=None):
        self.expr = expr
        self.start = start
        self.end = end
        self.step = step

    def subprocess(self, process):
        return ExprSlice(
            process(self.expr),
            process(self.start) if self.start else None,
            process(self.end) if self.end else None,
            process(self.step) if self.step else None,
        )

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

    def __init__(self, expr, params):
        self.expr = expr
        self.params = params

    def subprocess(self, process):
        return ExprCall(
            process(self.expr),
            [process(param) for param in self.params]
        )

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

    def __init__(self, name):
        self.name = name

    def subprocess(self, process):
        return self

    def show(self, ctx):
        return self.name


class ExprGlobal(Expr):
    __slots__ = 'name',

    def __init__(self, name):
        self.name = name

    def subprocess(self, process):
        return self

    def show(self, ctx):
        return '$global[{}]'.format(self.name)


class ExprFast(Expr):
    __slots__ = 'idx', 'name',

    def __init__(self, idx, name):
        self.idx = idx
        self.name = name

    def subprocess(self, process):
        return self

    def show(self, ctx):
        return '$fast[{},{}]'.format(self.idx, self.name)

# functions - to be cleaned up by prettifier

class ExprFunctionRaw(Expr):
    __slots__ = 'code',

    def __init__(self, code):
        self.code = code

    def subprocess(self, process):
        return ExprFunctionRaw(process(self.code))

    def show(self, ctx):
        # TODO some better idea?
        return '$functionraw'


class ExprFunction(Expr):
    __slots__ = 'name', 'args', 'block',

    def __init__(self, name, args, block):
        self.name = name
        self.args = args
        self.block = block

    def subprocess(self, process):
        return ExprFunction(
            self.name,
            process(self.args),
            process(self.block)
        )

    def show(self, ctx):
        # TODO some better idea?
        return '$function {}({})'.format(self.name, self.args.show())


class ExprClassRaw(Expr):
    __slots__ = 'name', 'bases', 'code'

    def __init__(self, name, bases, code):
        self.name = name
        self.bases = bases
        self.code = code

    def subprocess(self, process):
        return ExprClassRaw(
            self.name,
            [process(base) for base in self.bases],
            process(self.code)
        )

    def show(self, ctx):
        if self.bases:
            return '$classraw {}({})'.format(
                self.name,
                ', '.join(
                    base.show(None)
                    for base in self.bases
                )
            )
        else:
            return '$classraw {}()'.format(self.name)


class ExprClass(Expr):
    __slots__ = 'name', 'bases', 'body'

    def __init__(self, name, bases, body):
        self.name = name
        self.bases = bases
        self.body = body

    def subprocess(self, process):
        return ExprClass(
            self.name,
            [process(base) for base in self.bases],
            process(self.body)
        )

    def show(self, ctx):
        if self.bases:
            return '$class {}({})'.format(
                self.name,
                ', '.join(
                    base.show(None)
                    for base in self.bases
                )
            )
        else:
            return '$class {}()'.format(self.name)


class ExprLambda(Expr):
    __slots__ = 'args', 'expr',

    def __init__(self, args, expr):
        self.args = args
        self.expr = expr

    def subprocess(self, process):
        return ExprLambda(
            process(self.args),
            process(self.expr)
        )

    def show(self, ctx):
        return '(lambda {}: {})'.format(self.args.show(), self.expr.show(None))


# TODO: just get rid of it.

class ExprFrozenset(Expr):
    __slots__ = 'exprs',

    def __init__(self, exprs):
        self.exprs = exprs

    def show(self, ctx):
        # XXX
        return '$frozenset([{}])'.format(', '.join(v.show(ctx) for v in self.exprs))


def from_marshal(obj, version):
    if isinstance(obj, MarshalNone):
        return ExprNone()
    if isinstance(obj, MarshalBool):
        return ExprBool(obj.val)
    if isinstance(obj, MarshalEllipsis):
        return ExprEllipsis()
    if isinstance(obj, MarshalInt):
        return ExprInt(obj.val)
    if isinstance(obj, MarshalLong):
        return ExprLong(obj.val)
    if isinstance(obj, MarshalFloat):
        return ExprFloat(obj.val)
    if isinstance(obj, MarshalComplex):
        return ExprComplex(obj.val)
    if isinstance(obj, MarshalString):
        return ExprString(obj.val)
    if isinstance(obj, MarshalUnicode):
        return ExprUnicode(obj.val)
    if isinstance(obj, MarshalTuple):
        return ExprTuple([from_marshal(sub, version) for sub in obj.val])
    if isinstance(obj, MarshalFrozenset):
        return ExprFrozenset([from_marshal(sub, version) for sub in obj.val])
    raise PythonError("can't map {} to expression".format(type(obj)))
