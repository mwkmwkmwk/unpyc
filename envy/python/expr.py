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


class Expr:
    __slots__ = ()


class ExprNone(Expr):
    __slots__ = ()

    def show(self, version, ctx):
        return 'None'


class ExprBool(Expr):
    __slots__ = 'val',

    def __init__(self, val):
        self.val = val

    def show(self, version, ctx):
        return str(self.val)


class ExprEllipsis(Expr):
    __slots__ = ()

    def show(self, version, ctx):
        return "..."


class ExprInt(Expr):
    __slots__ = 'val',

    def __init__(self, val):
        self.val = val

    def show(self, version, ctx):
        return str(self.val)


class ExprLong(Expr):
    __slots__ = 'val',

    def __init__(self, val):
        self.val = val

    def show(self, version, ctx):
        return str(self.val) + 'L'


class ExprFloat(Expr):
    __slots__ = 'val',

    def __init__(self, val):
        self.val = val

    def show(self, version, ctx):
        return str(self.val)


class ExprComplex(Expr):
    __slots__ = 'val',

    def __init__(self, val):
        self.val = val

    def show(self, version, ctx):
        return str(self.val)


class ExprString(Expr):
    __slots__ = 'val',

    def __init__(self, val):
        self.val = val

    def show(self, version, ctx):
        # XXX
        return repr(self.val)


class ExprUnicode(Expr):
    __slots__ = 'val',

    def __init__(self, val):
        self.val = val

    def show(self, version, ctx):
        # XXX
        return repr(self.val)


class ExprTuple(Expr):
    __slots__ = 'val',

    def __init__(self, val):
        self.val = val

    def show(self, version, ctx):
        # XXX
        return '({}{})'.format(', '.join(v.show(version, ctx) for v in self.val), ',' if len(self.val) == 1 else '')


class ExprFrozenset(Expr):
    __slots__ = 'val',

    def __init__(self, val):
        self.val = val

    def show(self, version, ctx):
        # XXX
        return '$frozenset([{}])'.format(', '.join(v.show(version, ctx) for v in self.val))


def from_marshal(obj):
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
        return ExprTuple([from_marshal(sub) for sub in obj.val])
    if isinstance(obj, MarshalFrozenset):
        return ExprFrozenset([from_marshal(sub) for sub in obj.val])
    raise PythonError("can't map {} to expression".format(type(obj)))
