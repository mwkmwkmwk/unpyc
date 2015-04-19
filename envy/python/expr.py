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

from .ast import *

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

class CompItem(Node, abstract=True):
    pass

class CompFor(CompItem):
    dst = Field(Expr)
    expr = Field(Expr)

    def show(self):
        return 'for {} in {}'.format(self.dst.show(None), self.expr.show(None))

class CompIf(CompItem):
    expr = Field(Expr)

    def show(self):
        return 'if {}'.format(self.expr.show(None))

class Comp(Node):
    expr = Field(Expr)
    items = ListField(CompItem)

    def show(self):
        return '{} {}'.format(
            self.expr.show(None),
            ' '.join(item.show() for item in self.items)
        )


# TODO: print unicode/byte strings as appropriate for the python version
# TODO: context-aware printing
# TODO: nuke frozenset from load_from_marshal



# singletons

class ExprNone(Expr):
    def show(self, ctx):
        return 'None'


class ExprEllipsis(Expr):
    def show(self, ctx):
        return "..."

class ExprBuildClass(Expr):
    def show(self, ctx):
        return '$buildclass'

class ExprAnyTrue(Expr):
    def show(self, ctx):
        return '$true'

# literals


class ExprBool(Expr):
    val = Field(bool)

    def show(self, ctx):
        return str(self.val)


class ExprInt(Expr):
    val = Field(int)

    def show(self, ctx):
        return str(self.val)


class ExprLong(Expr):
    val = Field(int)

    def show(self, ctx):
        return str(self.val) + 'L'


class ExprFloat(Expr):
    val = Field(float)

    def show(self, ctx):
        return str(self.val)


class ExprComplex(Expr):
    val = Field(complex)

    def show(self, ctx):
        return str(self.val)


class ExprString(Expr):
    val = Field(bytes)

    def show(self, ctx):
        # XXX
        return repr(self.val)


class ExprUnicode(Expr):
    val = Field(str)

    def show(self, ctx):
        # XXX
        return repr(self.val)

# containers


class ExprTuple(Expr):
    exprs = ListField(Expr)

    def show(self, ctx):
        # XXX
        return '({}{})'.format(
            ', '.join(v.show(ctx) for v in self.exprs),
            ',' if len(self.exprs) == 1 else ''
        )


class ExprList(Expr):
    exprs = ListField(Expr)

    def show(self, ctx):
        # XXX
        return '[{}]'.format(
            ', '.join(v.show(ctx) for v in self.exprs),
        )


class ExprSet(Expr):
    exprs = ListField(Expr)

    def show(self, ctx):
        # XXX
        return '{{{}}}'.format(
            ', '.join(v.show(ctx) for v in self.exprs),
        )


class ExprListComp(Expr):
    comp = Field(Comp)

    def show(self, ctx):
        return '[{}]'.format(self.comp.show())


class ExprSetComp(Expr):
    comp = Field(Comp)

    def show(self, ctx):
        return '{{{}}}'.format(self.comp.show())


class ExprDictComp(Expr):
    key = Field(Expr)
    val = Field(Expr)
    items = ListField(CompItem)

    def show(self, ctx):
        return '{{{}: {} {}}}'.format(
            self.key.show(None),
            self.val.show(None),
            ' '.join(item.show() for item in self.items)
        )


class ExprGenExp(Expr):
    comp = Field(Comp)

    def show(self, ctx):
        return '({})'.format(self.comp.show())


class DictItem(Node):
    key = Field(Expr)
    val = Field(Expr)

    def show(self):
        return '{}: {}'.format(self.key.show(None), self.val.show(None))


class ExprDict(Expr):
    items = ListField(DictItem)

    def show(self, ctx):
        return '{{{}}}'.format(
            ', '.join(
                item.show()
                for item in self.items
            ),
        )


class ExprUnpackEx(Expr):
    before = ListField(Expr)
    star = MaybeField(Expr, volatile=True)
    after = ListField(Expr)

    def show(self, ctx):
        if not self.before and not self.after:
            return '(*{},)'.format(self.star.show(None))
        return '({})'.format(
            ', '.join(
                [expr.show(None) for expr in self.before] +
                ['*' + self.star.show(None)] +
                [expr.show(None) for expr in self.after]
            )
        )


# unary

class ExprUn(Expr, abstract=True):
    e1 = Field(Expr)

    def show(self, ctx):
        # XXX
        return '({}{})'.format(self.sign, self.e1.show(ctx))


class ExprPos(ExprUn):
    sign = '+'


class ExprNeg(ExprUn):
    sign = '-'


class ExprNot(ExprUn):
    sign = 'not '


class ExprRepr(ExprUn):
    def show(self, ctx):
        # XXX
        return '(`{}`)'.format(self.e1.show(ctx))


class ExprInvert(ExprUn):
    sign = '~'


class ExprYield(ExprUn):
    sign = 'yield '


class ExprYieldFrom(ExprUn):
    sign = 'yield from '


# binary

class ExprBin(Expr, abstract=True):
    e1 = Field(Expr)
    e2 = Field(Expr)

    def show(self, ctx):
        # XXX
        return '({} {} {})'.format(self.e1.show(ctx), self.sign, self.e2.show(ctx))


class ExprPow(ExprBin):
    sign = '**'


class ExprMul(ExprBin):
    sign = '*'


class ExprDiv(ExprBin):
    sign = '/'


class ExprMod(ExprBin):
    sign = '%'


class ExprAdd(ExprBin):
    sign = '+'


class ExprSub(ExprBin):
    sign = '-'


class ExprShl(ExprBin):
    sign = '<<'


class ExprShr(ExprBin):
    sign = '>>'


class ExprAnd(ExprBin):
    sign = '&'


class ExprOr(ExprBin):
    sign = '|'


class ExprXor(ExprBin):
    sign = '^'


class ExprBoolAnd(ExprBin):
    sign = 'and'


class ExprBoolOr(ExprBin):
    sign = 'or'


class ExprTrueDiv(ExprBin):
    sign = '$/'


class ExprFloorDiv(ExprBin):
    sign = '//'


class ExprMatMul(ExprBin):
    sign = '@'


class ExprIf(Expr):
    cond = Field(Expr)
    true = Field(Expr)
    false = Field(Expr)

    def show(self, ctx):
        return '({} if {} else {})'.format(
            self.true.show(None),
            self.cond.show(None),
            self.false.show(None),
        )


# compares

class CmpItem(Node):
    op = Field(CmpOp)
    expr = Field(Expr)

class ExprCmp(Expr):
    first = Field(Expr)
    rest = ListField(CmpItem)

    def show(self, ctx):
        return '({} {})'.format(self.first.show(ctx), ' '.join(
            '{} {}'.format(COMPARE_OPS[item.op], item.expr.show(ctx))
            for item in self.rest
        ))


# attributes, indexing

class ExprAttr(Expr):
    expr = Field(Expr)
    name = Field(str)

    def show(self, ctx):
        return '({}).{}'.format(self.expr.show(ctx), self.name)


class ExprSubscr(Expr):
    e1 = Field(Expr)
    e2 = Field(Expr)

    def show(self, ctx):
        return '{}[{}]'.format(self.e1.show(ctx), self.e2.show(ctx))


class ExprSlice2(Expr):
    start = MaybeField(Expr)
    end = MaybeField(Expr)

    def show(self, ctx):
        def maybe(x):
            return x.show(ctx) if x is not None else ''
        return '{}:{}'.format(maybe(self.start), maybe(self.end))


class ExprSlice3(Expr):
    start = MaybeField(Expr)
    end = MaybeField(Expr)
    step = MaybeField(Expr)

    def show(self, ctx):
        def maybe(x):
            return x.show(ctx) if x is not None else ''
        return '{}:{}:{}'.format(maybe(self.start), maybe(self.end), maybe(self.step))


# calls

class ExprCall(Expr):
    expr = Field(Expr)
    args = Field(CallArgs)

    def show(self, ctx):
        return '{}({})'.format(
            self.expr.show(ctx),
            self.args.show()
        )


# names

class ExprName(Expr):
    name = Field(str)

    def show(self, ctx):
        return self.name


class ExprGlobal(Expr):
    name = Field(str)

    def show(self, ctx):
        return '$global[{}]'.format(self.name)


class ExprFast(Expr):
    idx = Field(int)
    name = Field(str)

    def show(self, ctx):
        return '{}${}'.format(self.name, self.idx)


class ExprDeref(Expr):
    idx = Field(int)
    name = Field(str)

    def show(self, ctx):
        return '{}$d{}'.format(self.name, self.idx)

# functions - to be cleaned up by prettifier


class DecoCode(Node):
    block = Field(Block)
    # XXX has to go
    code = Field(object)
    varnames = ListField(str)

    def show(self):
        return self.block.show()


class ExprFunctionRaw(Expr):
    code = Field(DecoCode)
    defargs = ListField(Expr)
    defkwargs = DictField(str, Expr)
    ann = DictField(str, Expr)
    closures = ListField(Expr)

    def show(self, ctx):
        # TODO some better idea?
        if self.defargs or self.closures:
            return '($functionraw {} ; {} ; {} ; {})'.format(
                ', '.join(arg.show(None) for arg in self.defargs),
                ', '.join('{}={}'.format(name, arg.show(None)) for name, arg in self.defkwargs.items()),
                ', '.join('{}:{}'.format(name, ann.show(None)) for name, ann in self.ann.items()),
                ', '.join(c.show(None) for c in self.closures)
            )
        return '$functionraw'


class ExprFunction(Expr):
    name = MaybeField(str)
    args = Field(FunArgs)
    block = Field(Block)

    def show(self, ctx):
        # TODO some better idea?
        return '$function {}({})'.format(self.name, self.args.show())


class ExprClassRaw(Expr):
    name = Field(str)
    args = Field(CallArgs)
    code = Field(DecoCode)
    closures = ListField(Expr)

    def show(self, ctx):
        if self.args.args:
            return '$classraw {}({})'.format(
                self.name,
                self.args.show()
            )
        else:
            return '$classraw {}()'.format(self.name)


class ExprClass(Expr):
    name = Field(str)
    args = Field(CallArgs)
    body = Field(Block)

    def show(self, ctx):
        if self.args.args:
            return '$class {}({})'.format(
                self.name,
                self.args.show()
            )
        else:
            return '$class {}()'.format(self.name)


class ExprLambda(Expr):
    args = Field(FunArgs)
    expr = Field(Expr)

    def show(self, ctx):
        return '(lambda {}: {})'.format(self.args.show(), self.expr.show(None))


class ExprNewListCompRaw(Expr):
    expr = Field(Expr)
    topdst = Field(Expr)
    items = ListField(CompItem)
    arg = Field(Expr)

    def show(self, ctx):
        return '$newlistcompraw({} top {} in {} {})'.format(
            self.expr.show(None),
            self.topdst.show(None),
            self.arg.show(None),
            ' '.join(item.show() for item in self.items),
        )


class ExprNewSetCompRaw(Expr):
    expr = Field(Expr)
    topdst = Field(Expr)
    items = ListField(CompItem)
    arg = Field(Expr)

    def show(self, ctx):
        return '$newsetcompraw({} top {} in {} {})'.format(
            self.expr.show(None),
            self.topdst.show(None),
            self.arg.show(None),
            ' '.join(item.show() for item in self.items),
        )


class ExprNewDictCompRaw(Expr):
    key = Field(Expr)
    val = Field(Expr)
    topdst = Field(Expr)
    items = ListField(CompItem)
    arg = Field(Expr)

    def show(self, ctx):
        return '$newdictcompraw({}: {} top {} in {} {})'.format(
            self.key.show(None),
            self.val.show(None),
            self.topdst.show(None),
            self.arg.show(None),
            ' '.join(item.show() for item in self.items),
        )


class ExprCallComp(Expr):
    fun = Field(ExprFunctionRaw)
    expr = Field(Expr)

    def show(self, ctx):
        return '$callcomp({})'.format(self.expr.show(None))


class Frozenset(Node):
    exprs = ListField(Expr)


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
        return Frozenset([from_marshal(sub, version) for sub in obj.val])
    raise PythonError("can't map {} to expression".format(type(obj)))
