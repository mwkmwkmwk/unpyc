from collections import namedtuple
from enum import Enum
import inspect

from .helpers import PythonError
from .stmt import *
from .expr import *
from .code import Code
from .bytecode import *
from .postproc import uncomp, unreturn

TRACE = False

# TODO:
#
# - make a nice ast metaclass
# - clean expr
# - clean up the stack item mess
# - contexts for expressions dammit
# - bump as many versions as easily possible
# - figure out what to do about line numbers
# - make a test suite
# - find a way to print nested code objects after stage 3
# - clean up import mess
# - make sure signed/unsigned numbers are right
# - None is not exactly a keyword until 2.4
# - py 1.4:
#
#   - mangling
#
# - py 1.5:
#
#   - tuple arguments are called '.num' instead of ''
#
# - py 2.1:
#
#   - future
#
# - py 2.2:
#
#   - nuke __module__ = __name__
#   - unfuture true divide
#   - detect generators, add if 0: yield
#
# - py 2.3:
#
#   - encoding...
#   - SET_LINENO no more
#   - nofree flag
#
# - py 2.4:
#
#   - None is now a keyword
#   - enter peephole:
#
#     - UNARY_NOT JUMP_IF_FALSE [POP] -> JUMP_IF_TRUE [POP]
#     - true const JUMP_IF_FALSE POP -> NOPs
#     - JUMP_IF_FALSE/TRUE chain shortening
#
# - py 2.6:
#
#   - except a as b
#
# - py 3.0:
#
#   - yeah, well, unicode is everywhere
#   - real funny except
#   - nonlocal
#   - ellipsis allowed everywhere
#
# - py 2.7 & 3.1:
#
#   - comprehension changes (funny arg)
#   - JUMP_IF_FALSE/TRUE changed to POP_* and *_OR_POP
#   - multiple items in with
#
# - py 3.1:
#
#   - <> and barry
#
# - py 2.7 & 3.2:
#
#   - setup with
#
# - py 3.2:
#
#   - from .
#
# - py 3.3:
#
#   - qualnames
#
# - py 3.4:
#
#   - classderef
#
# - py 3.5:
#
#   - empty else is elided
#
# and for prettifier:
#
# - names:
#
#   - verify optimized/not
#   - deal with name types
#   - stuff 'global' somewhere
#   - verify used names don't collide with keywords
#
# - decide same/different line
# - clean statements:
#
#   - import: get rid of as
#
# - merge statements:
#
#   - import
#   - access
#   - print
#
# - deal with class/top __doc__ assignments
# - verify function docstrings

# funny intermediate stuff to put on stack

DupTop = namedtuple('DupTop', [])
DupTwo = namedtuple('DupTwo', [])
DupThree = namedtuple('DupThree', [])

RotTwo = namedtuple('RotTwo', [])
RotThree = namedtuple('RotThree', [])
RotFour = namedtuple('RotFour', [])

Iter = namedtuple('Iter', ['expr'])

Import = namedtuple('Import', ['name', 'items'])
Import2Simple = namedtuple('Import2Simple', ['level', 'name', 'attrs'])
Import2Star = namedtuple('Import2Star', ['level', 'name'])
Import2From = namedtuple('Import2From', ['level', 'fromlist', 'name', 'exprs'])

MultiAssign = namedtuple('MultiAssign', ['src', 'dsts'])
PrintTo = namedtuple('PrintTo', ['expr', 'vals'])

UnpackSlot = namedtuple('UnpackSlot', ['expr', 'idx'])
UnpackArgSlot = namedtuple('UnpackArgSlot', ['args', 'idx'])
UnpackVarargSlot = namedtuple('UnpackVarargSlot', ['args'])
UnpackBeforeSlot = namedtuple('UnpackBeforeSlot', ['expr', 'idx'])
UnpackAfterSlot = namedtuple('UnpackAfterSlot', ['expr', 'idx'])
UnpackStarSlot = namedtuple('UnpackStarSlot', ['expr'])

IfStart = namedtuple('IfStart', ['expr', 'flow', 'neg', 'pop'])
IfExprTrue = namedtuple('IfExprTrue', ['expr', 'flow'])
IfExprElse = namedtuple('IfExprElse', ['cond', 'true', 'flow'])
IfDead = namedtuple('IfDead', ['cond', 'true', 'flow'])

CompareStart = namedtuple('CompareStart', ['first', 'rest', 'flows'])
Compare = namedtuple('Compare', ['first', 'rest', 'flows'])
CompareLast = namedtuple('CompareLast', ['first', 'rest', 'flows'])
CompareNext = namedtuple('CompareNext', ['first', 'rest', 'flows'])

WantPop = namedtuple('WantPop', [])
WantRotPop = namedtuple('WantRotPop', [])
WantFlow = namedtuple('WantFlow', ['any', 'true', 'false'])
WantReturn = namedtuple('WantReturn', ['expr'])

SetupLoop = namedtuple('SetupLoop', ['flow'])
SetupFinally = namedtuple('SetupFinally', ['flow'])
SetupExcept = namedtuple('SetupExcept', ['flow'])

Loop = namedtuple('Loop', ['flow'])
While = namedtuple('While', ['expr', 'end', 'block'])
ForStart = namedtuple('ForStart', ['expr', 'flow'])
TopForStart = namedtuple('TopForStart', ['expr', 'flow'])
ForLoop = namedtuple('ForLoop', ['expr', 'dst', 'flow'])
TopForLoop = namedtuple('TopForLoop', ['expr', 'dst', 'flow'])

TryFinallyPending = namedtuple('TryFinallyPending', ['body', 'flow'])
TryFinally = namedtuple('TryFinally', ['body'])

TryExceptEndTry = namedtuple('TryExceptEndTry', ['flow', 'body'])
TryExceptMid = namedtuple('TryExceptMid', ['else_', 'body', 'items', 'any', 'flows'])
TryExceptMatchMid = namedtuple('TryExceptMatchMid', ['expr'])
TryExceptMatchOk = namedtuple('TryExceptMatchOk', ['expr', 'next'])
TryExceptMatch = namedtuple('TryExceptMatch', ['expr', 'dst', 'next'])
TryExceptAny = namedtuple('TryExceptAny', [])
PopExcept = namedtuple('PopExcept', [])

UnaryCall = namedtuple('UnaryCall', ['code'])
Locals = namedtuple('Locals', [])

DupAttr = namedtuple('DupAttr', ['expr', 'name'])
DupSubscr = namedtuple('DupSubscr', ['expr', 'index'])
DupSliceNN = namedtuple('DupSliceNN', ['expr'])
DupSliceEN = namedtuple('DupSliceEN', ['expr', 'start'])
DupSliceNE = namedtuple('DupSliceNE', ['expr', 'end'])
DupSliceEE = namedtuple('DupSliceEE', ['expr', 'start', 'end'])

InplaceSimple = namedtuple('InplaceSimple', ['dst', 'src', 'stmt'])
InplaceAttr = namedtuple('InplaceAttr', ['expr', 'name', 'src', 'stmt'])
InplaceSubscr = namedtuple('InplaceSubscr', ['expr', 'index', 'src', 'stmt'])
InplaceSliceNN = namedtuple('InplaceSliceNN', ['expr', 'src', 'stmt'])
InplaceSliceEN = namedtuple('InplaceSliceEN', ['expr', 'start', 'src', 'stmt'])
InplaceSliceNE = namedtuple('InplaceSliceNE', ['expr', 'end', 'src', 'stmt'])
InplaceSliceEE = namedtuple('InplaceSliceEE', ['expr', 'start', 'end', 'src', 'stmt'])

TmpVarAttrStart = namedtuple('TmpVarAttrStart', ['tmp', 'expr', 'name'])
TmpVarCleanup = namedtuple('TmpVarCleanup', ['tmp'])

Closure = namedtuple('Closure', ['var'])
ClosuresTuple = namedtuple('ClosuresTuple', ['vars'])

FinalElse = namedtuple('FinalElse', ['flow', 'maker'])
AssertJunk = namedtuple('AssertJunk', ['expr', 'msg'])

WithEnter = namedtuple('WithEnter', ['tmp', 'expr'])
WithResult = namedtuple('WithResult', ['tmp', 'expr'])
WithStart = namedtuple('WithStart', ['tmp', 'expr'])
WithStartTmp = namedtuple('WithStartTmp', ['tmp', 'expr', 'res'])
WithTmp = namedtuple('WithTmp', ['tmp', 'expr', 'res', 'flow'])
WithInnerResult = namedtuple('WithInnerResult', ['tmp', 'expr', 'flow'])
With = namedtuple('With', ['tmp', 'expr', 'dst', 'flow'])
WithEndPending = namedtuple('WithEndPending', ['tmp', 'flow', 'stmt'])
WithEnd = namedtuple('WithEnd', ['tmp', 'stmt'])
WithExit = namedtuple('WithExit', ['stmt'])
WithExitDone = namedtuple('WithExitDone', ['stmt'])

# final makers

class FinalJunk(namedtuple('FinalJunk', [])):
    def __call__(self, else_):
        return StmtJunk(else_)

class FinalIf(namedtuple('FinalIf', ['expr', 'body'])):
    def __call__(self, else_):
        return StmtIfRaw(self.expr, self.body, else_)

class FinalLoop(namedtuple('FinalLoop', ['body'])):
    def __call__(self, else_):
        return StmtLoop(self.body, else_)

class FinalExcept(namedtuple('FinalExcept', ['body', 'items', 'any'])):
    def __call__(self, else_):
        return StmtExcept(self.body, self.items, self.any, else_)

# regurgitables

class Regurgitable: __slots__ = ()

class Store(Regurgitable, namedtuple('Store', ['dst'])): pass
class Inplace(Regurgitable, namedtuple('Inplace', ['stmt'])): pass

# fake opcodes

class JumpIfTrue(OpcodeFlow): pass
class JumpIfFalse(OpcodeFlow): pass
class PopJumpIfTrue(OpcodeFlow): pass
class PopJumpIfFalse(OpcodeFlow): pass
class JumpUnconditional(OpcodeFlow): pass
class JumpContinue(OpcodeFlow): pass
class JumpSkipJunk(OpcodeFlow): pass


class FwdFlow(Regurgitable, namedtuple('FwdFlow', ['flow'])): pass
class RevFlow(Regurgitable, namedtuple('RevFlow', ['flow'])): pass

# for checks

Regurgitable = (Regurgitable, Stmt, Opcode)

def _maybe_want_pop(flag):
    if flag:
        return None
    else:
        return WantPop()

# wantables

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
        return res


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

    def parse(res, opcode):
        pass
        if looplen:
            arg = stack[-looplen:]
            del stack[-looplen:]
        else:
            arg = []


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


# visitors

class NoMatch(Exception):
    pass

_VISITORS = {}

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

def visitor(func):
    asp = inspect.getfullargspec(func)
    aself, aop, *astack = asp.args
    flag = asp.annotations.get(aself)
    stack = [asp.annotations[x] for x in astack]
    op = asp.annotations[aop]
    if not isinstance(op, tuple):
        op = op,
    for op in op:
        _VISITORS.setdefault(op, []).append(_Visitor(func, stack, flag))
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

    _VISITORS.setdefault(lop, []).append(_Visitor(visit_lsd_load, stack, flag))
    _VISITORS.setdefault(sop, []).append(_Visitor(visit_lsd_store, stack, flag))
    _VISITORS.setdefault(dop, []).append(_Visitor(visit_lsd_delete, stack, flag))
    return func

# visitors

# line numbers

@visitor
def visit_set_lineno(
    self,
    op: OpcodeSetLineno,
):
    self.lineno = op.param
    return []

@visitor
def visit_nop(
    self,
    op: OpcodeNop,
):
    return []

# stack ops

def _register_token(otype, ttype):
    @visitor
    def visit_token(
        self,
        op: otype,
    ):
        return [ttype()]

for otype, ttype in {
    OpcodeDupTop: DupTop,
    OpcodeDupTwo: DupTwo,
    OpcodeRotTwo: RotTwo,
    OpcodeRotThree: RotThree,
    OpcodeRotFour: RotFour,
    OpcodePopExcept: PopExcept,
    OpcodeLoadLocals: Locals,
    OpcodeLoadBuildClass: ExprBuildClass,
    OpcodeBreakLoop: StmtBreak,
}.items():
    _register_token(otype, ttype)

@visitor
def visit_dup_topx(
    self,
    op: OpcodeDupTopX,
):
    if op.param == 2:
        return [DupTwo()]
    elif op.param == 3:
        return [DupThree()]
    else:
        raise PythonError("funny DUP_TOPX parameter")

@visitor
def _visit_want_pop(
    self,
    op: OpcodePopTop,
    want: WantPop,
):
    return []

@visitor
def _visit_want_rot_two(
    self,
    op: OpcodePopTop,
    want: WantRotPop,
    _: RotTwo,
):
    return []


# expressions - unary

def _register_unary(otype, etype):
    @visitor
    def visit_unary(
        self,
        op: otype,
        expr: Expr,
    ):
        return [etype(expr)]

for otype, etype in {
    OpcodeUnaryPositive: ExprPos,
    OpcodeUnaryNegative: ExprNeg,
    OpcodeUnaryNot: ExprNot,
    OpcodeUnaryConvert: ExprRepr,
    OpcodeUnaryInvert: ExprInvert,
}.items():
    _register_unary(otype, etype)

# expressions - binary

def _register_binary(otype, etype):
    @visitor
    def visit_binary(
        self,
        op: otype,
        expr1: Expr,
        expr2: Expr,
    ):
        return [etype(expr1, expr2)]

for otype, etype in {
    OpcodeBinaryPower: ExprPow,
    OpcodeBinaryMultiply: ExprMul,
    OpcodeBinaryDivide: ExprDiv,
    OpcodeBinaryModulo: ExprMod,
    OpcodeBinaryAdd: ExprAdd,
    OpcodeBinarySubtract: ExprSub,
    OpcodeBinaryLshift: ExprShl,
    OpcodeBinaryRshift: ExprShr,
    OpcodeBinaryAnd: ExprAnd,
    OpcodeBinaryOr: ExprOr,
    OpcodeBinaryXor: ExprXor,
    OpcodeBinaryTrueDivide: ExprTrueDiv,
    OpcodeBinaryFloorDivide: ExprFloorDiv,
    OpcodeBinaryMatrixMultiply: ExprMatMul,
}.items():
    _register_binary(otype, etype)

# expressions - build container

@visitor
def visit_build_tuple(
    self,
    op: OpcodeBuildTuple,
    exprs: Exprs('param', 1),
):
    return [ExprTuple(exprs)]

@visitor
def visit_build_list(
    self,
    op: OpcodeBuildList,
    exprs: Exprs('param', 1),
):
    return [ExprList(exprs)]

@visitor
def visit_build_set(
    self,
    op: OpcodeBuildSet,
    exprs: Exprs('param', 1),
):
    return [ExprSet(exprs)]

# x in const set special

@visitor
def visit_frozenset(
    self,
    op: OpcodeCompareOp,
    fset: Frozenset
):
    if op.param not in [CmpOp.IN, CmpOp.NOT_IN]:
        raise PythonError("funny place for frozenset")
    if not fset.exprs:
        raise PythonError("can't make empty set display out of frozenset")
    return [ExprSet(fset.exprs), op]

@visitor
def visit_build_map(
    self,
    op: OpcodeBuildMap,
):
    if op.param and not self.version.has_store_map:
        raise PythonError("Non-zero param for BUILD_MAP")
    return [ExprDict([])]

@visitor
def visit_build_map_step(
    self: 'has_reversed_kv',
    op: OpcodeStoreSubscr,
    dict_: ExprDict,
    _1: DupTop,
    val: Expr,
    _2: RotTwo,
    key: Expr
):
    dict_.items.append(DictItem(key, val))
    return [dict_]

@visitor
def visit_build_map_step(
    self: ('!has_reversed_kv', '!has_store_map'),
    op: OpcodeStoreSubscr,
    dict_: ExprDict,
    _1: DupTop,
    key: Expr,
    val: Expr,
    _2: RotThree,
):
    dict_.items.append(DictItem(key, val))
    return [dict_]

@visitor
def visit_build_map_step(
    self,
    op: OpcodeStoreMap,
    dict_: ExprDict,
    val: Expr,
    key: Expr,
):
    dict_.items.append(DictItem(key, val))
    return [dict_]

# expressions - function call

@visitor
def visit_binary_call(
    self,
    op: OpcodeBinaryCall,
    expr: Expr,
    params: ExprTuple,
):
    return [ExprCall(expr, CallArgs([CallArgPos(arg) for arg in params.exprs]))]

@visitor
def visit_call_function(
    self,
    op: OpcodeCallFunction,
    fun: Expr,
    args: Exprs('args', 1),
    kwargs: Exprs('kwargs', 2),
):
    return [ExprCall(
        fun,
        CallArgs(
            [CallArgPos(arg) for arg in args] +
            [CallArgKw(arg, self.string(name)) for name, arg in kwargs]
        )
    )]

@visitor
def visit_call_function(
    self,
    op: OpcodeCallFunctionVar,
    fun: Expr,
    args: Exprs('args', 1),
    kwargs: Exprs('kwargs', 2),
    vararg: Expr,
):
    return [ExprCall(
        fun,
        CallArgs(
            [CallArgPos(arg) for arg in args] +
            [CallArgKw(arg, self.string(name)) for name, arg in kwargs] +
            [CallArgVar(vararg)]
        )
    )]

@visitor
def visit_call_function(
    self,
    op: OpcodeCallFunctionKw,
    fun: Expr,
    args: Exprs('args', 1),
    kwargs: Exprs('kwargs', 2),
    varkw: Expr,
):
    return [ExprCall(
        fun,
        CallArgs(
            [CallArgPos(arg) for arg in args] +
            [CallArgKw(arg, self.string(name)) for name, arg in kwargs] +
            [CallArgVarKw(varkw)]
        )
    )]

@visitor
def visit_call_function(
    self,
    op: OpcodeCallFunctionVarKw,
    fun: Expr,
    args: Exprs('args', 1),
    kwargs: Exprs('kwargs', 2),
    vararg: Expr,
    varkw: Expr,
):
    return [ExprCall(
        fun,
        CallArgs(
            [CallArgPos(arg) for arg in args] +
            [CallArgKw(arg, self.string(name)) for name, arg in kwargs] +
            [CallArgVar(vararg), CallArgVarKw(varkw)]
        )
    )]

# expressions - load const

@visitor
def visit_load_const(
    self,
    op: OpcodeLoadConst,
):
    return [op.const]

# expressions - storable

@lsd_visitor
def visit_store_name(
    self,
    op: (OpcodeLoadName, OpcodeStoreName, OpcodeDeleteName),
):
    return ExprName(op.param)

@lsd_visitor
def visit_store_global(
    self,
    op: (OpcodeLoadGlobal, OpcodeStoreGlobal, OpcodeDeleteGlobal),
):
    return ExprGlobal(op.param)

@lsd_visitor
def visit_store_fast(
    self,
    op: (OpcodeLoadFast, OpcodeStoreFast, OpcodeDeleteFast),
):
    return self.fast(op.param)

@lsd_visitor
def visit_store_deref(
    self,
    op: (OpcodeLoadDeref, OpcodeStoreDeref, None),
):
    return self.deref(op.param)

@lsd_visitor
def visit_store_attr(
    self,
    op: (OpcodeLoadAttr, OpcodeStoreAttr, OpcodeDeleteAttr),
    expr: Expr,
):
    return ExprAttr(expr, op.param)

@lsd_visitor
def visit_store_subscr(
    self,
    op: (OpcodeBinarySubscr, OpcodeStoreSubscr, OpcodeDeleteSubscr),
    expr: Expr,
    idx: Expr
):
    return ExprSubscr(expr, idx)

@lsd_visitor
def visit_store_slice_nn(
    self,
    op: (OpcodeSliceNN, OpcodeStoreSliceNN, OpcodeDeleteSliceNN),
    expr: Expr,
):
    return ExprSubscr(expr, ExprSlice2(None, None))

@lsd_visitor
def visit_store_slice_en(
    self,
    op: (OpcodeSliceEN, OpcodeStoreSliceEN, OpcodeDeleteSliceEN),
    expr: Expr,
    start: Expr,
):
    return ExprSubscr(expr, ExprSlice2(start, None))

@lsd_visitor
def visit_store_slice_ne(
    self,
    op: (OpcodeSliceNE, OpcodeStoreSliceNE, OpcodeDeleteSliceNE),
    expr: Expr,
    end: Expr
):
    return ExprSubscr(expr, ExprSlice2(None, end))

@lsd_visitor
def visit_store_slice_ee(
    self,
    op: (OpcodeSliceEE, OpcodeStoreSliceEE, OpcodeDeleteSliceEE),
    expr: Expr,
    start: Expr,
    end: Expr,
):
    return ExprSubscr(expr, ExprSlice2(start, end))

@visitor
def visit_build_slice(
    self,
    op: OpcodeBuildSlice,
    exprs: Exprs('param', 1),
):
    params = [None if isinstance(expr, ExprNone) else expr for expr in exprs]
    if op.param == 2:
        return [ExprSlice2(*params)]
    elif op.param == 3:
        return [ExprSlice3(*params)]
    else:
        raise PythonError("funny slice length")

# list & tuple unpacking

@visitor
def visit_unpack_sequence(
    self,
    op: (OpcodeUnpackTuple, OpcodeUnpackSequence)
):
    res = ExprTuple([])
    return [Store(res)] + [UnpackSlot(res, idx) for idx in reversed(range(op.param))]

@visitor
def visit_unpack_list(
    self,
    op: OpcodeUnpackList,
):
    res = ExprList([])
    return [Store(res)] + [UnpackSlot(res, idx) for idx in reversed(range(op.param))]

@visitor
def visit_store_unpack(
    self,
    op: Store,
    slot: UnpackSlot,
):
    assert len(slot.expr.exprs) == slot.idx
    slot.expr.exprs.append(op.dst)
    return []

# optimized unpacking

@visitor
def visit_unpack_opt_two_skip(
    self: ('has_unpack_opt', 'has_nop'),
    op: JumpSkipJunk,
    a: Expr,
    b: Expr,
    _: RotTwo
):
    src = ExprTuple([a, b])
    dst = ExprTuple([])
    return [StmtAssign([dst], src), UnpackSlot(dst, 1), UnpackSlot(dst, 0), WantFlow(op.flow, [], [])]

@visitor
def visit_unpack_opt_three_skip(
    self: ('has_unpack_opt', 'has_nop'),
    op: JumpSkipJunk,
    a: Expr,
    b: Expr,
    c: Expr,
    _1: RotThree,
    _2: RotTwo
):
    src = ExprTuple([a, b, c])
    dst = ExprTuple([])
    return [StmtAssign([dst], src), UnpackSlot(dst, 2), UnpackSlot(dst, 1), UnpackSlot(dst, 0), WantFlow(op.flow, [], [])]

@visitor
def visit_unpack_opt_two_skip(
    self: ('has_unpack_opt', '!has_nop'),
    op: Store,
    a: Expr,
    b: Expr,
    _: RotTwo,
):
    src = ExprTuple([a, b])
    dst = ExprTuple([op.dst])
    return [StmtAssign([dst], src), UnpackSlot(dst, 1)]

@visitor
def visit_unpack_opt_three_skip(
    self: ('has_unpack_opt', '!has_nop'),
    op: Store,
    a: Expr,
    b: Expr,
    c: Expr,
    _1: RotThree,
    _2: RotTwo,
):
    src = ExprTuple([a, b, c])
    dst = ExprTuple([op.dst])
    return [StmtAssign([dst], src), UnpackSlot(dst, 2), UnpackSlot(dst, 1)]

# old argument unpacking

@visitor
def visit_unpack_arg(
    self,
    op: OpcodeUnpackArg,
):
    res = StmtArgs([], None)
    return [res] + [UnpackArgSlot(res, idx) for idx in reversed(range(op.param))]

@visitor
def visit_unpack_arg(
    self,
    op: OpcodeUnpackVararg,
):
    res = StmtArgs([], None)
    return [res, UnpackVarargSlot(res)] + [UnpackArgSlot(res, idx) for idx in reversed(range(op.param))]

@visitor
def visit_store_unpack_arg(
    self,
    op: Store,
    slot: UnpackArgSlot,
):
    assert len(slot.args.args) == slot.idx
    slot.args.args.append(op.dst)
    return []

@visitor
def visit_store_unpack_vararg(
    self,
    op: Store,
    slot: UnpackVarargSlot,
):
    slot.args.vararg = op.dst
    return []

# extended unpacking

@visitor
def visit_unpack_sequence(
    self,
    op: OpcodeUnpackEx,
):
    res = ExprUnpackEx([], None, [])
    return [
        Store(res)
    ] + [
        UnpackAfterSlot(res, idx) for idx in reversed(range(op.after))
    ] + [
        UnpackStarSlot(res)
    ] + [
        UnpackBeforeSlot(res, idx) for idx in reversed(range(op.before))
    ]

@visitor
def visit_store_unpack_before(
    self,
    op: Store,
    slot: UnpackBeforeSlot,
):
    assert len(slot.expr.before) == slot.idx
    slot.expr.before.append(op.dst)
    return []

@visitor
def visit_store_unpack_star(
    self,
    op: Store,
    slot: UnpackStarSlot,
):
    slot.expr.star = op.dst
    return []

@visitor
def visit_store_unpack_after(
    self,
    op: Store,
    slot: UnpackAfterSlot,
):
    assert len(slot.expr.after) == slot.idx
    slot.expr.after.append(op.dst)
    return []

# statements

@visitor
def _visit_stmt(
    self,
    op: Stmt,
    block: Block
):
    block.stmts.append(op)
    return [block]

# single expression statement

@visitor
def _visit_print_expr(
    self,
    op: OpcodePrintExpr,
    expr: Expr,
):
    return [StmtPrintExpr(expr)]

@visitor
def _visit_single_expr(
    self: '!always_print_expr',
    op: OpcodePopTop,
    block: Block,
    expr: Expr,
):
    return [block, StmtSingle(expr)]

# assignment

@visitor
def visit_store_assign(
    self,
    op: Store,
    src: Expr,
):
    return [StmtAssign([op.dst], src)]

@visitor
def visit_store_multi_start(
    self,
    op: Store,
    src: Expr,
    _: DupTop,
):
    return [MultiAssign(src, [op.dst])]

@visitor
def visit_store_multi_next(
    self,
    op: Store,
    multi: MultiAssign,
    _: DupTop,
):
    multi.dsts.append(op.dst)
    return [multi]

@visitor
def visit_store_multi_end(
    self,
    op: Store,
    multi: MultiAssign,
):
    multi.dsts.append(op.dst)
    return [StmtAssign(multi.dsts, multi.src)]

# print statement

@visitor
def visit_print_item(
    self,
    op: OpcodePrintItem,
    expr: Expr,
):
    return [StmtPrint([expr], False)]

@visitor
def visit_print_newline(
    self,
    op: OpcodePrintNewline,
):
    return [StmtPrint([], True)]

# print to

@visitor
def visit_print_item_to(
    self,
    op: OpcodePrintItemTo,
    to: Expr,
    _dup: DupTop,
    expr: Expr,
    _rot: RotTwo,
):
    return [PrintTo(to, [expr])]

@visitor
def visit_print_item_to(
    self,
    op: OpcodePrintItemTo,
    print: PrintTo,
    _dup: DupTop,
    expr: Expr,
    _rot: RotTwo,
):
    print.vals.append(expr)
    return [print]

@visitor
def visit_print_to_end(
    self,
    op: OpcodePopTop,
    print: PrintTo,
):
    return [StmtPrintTo(print.expr, print.vals, False)]

@visitor
def visit_print_newline_to(
    self,
    op: OpcodePrintNewlineTo,
    print: PrintTo,
):
    return [StmtPrintTo(print.expr, print.vals, True)]

@visitor
def visit_print_newline_to(
    self,
    op: OpcodePrintNewlineTo,
    expr: Expr,
):
    return [StmtPrintTo(expr, [], True)]

# return statement

@visitor
def _visit_return(
    self,
    op: OpcodeReturnValue,
    expr: Expr,
):
    return [StmtReturn(expr)]

# assert. ouch. has to be before raise.

@visitor
def _visit_assert_1(
    self: ('has_assert', '!has_short_assert'),
    op: OpcodeRaiseVarargs,
    ifstart: IfStart,
    block: Block,
    orstart: IfStart,
    block2: Block,
    exprs: Exprs('param', 1),
):
    if ifstart.neg or not orstart.neg or ifstart.pop or orstart.pop:
        raise NoMatch
    if block.stmts or block2.stmts:
        raise PythonError("extra assert statements")
    if not isinstance(exprs[0], ExprGlobal) or exprs[0].name != 'AssertionError':
        raise PythonError("hmm, I wanted an assert...")
    if not isinstance(ifstart.expr, ExprGlobal) or ifstart.expr.name != '__debug__':
        raise PythonError("hmm, I wanted an assert...")
    if op.param == 1:
        return [StmtAssert(orstart.expr), WantPop(), WantFlow([], orstart.flow, ifstart.flow)]
    elif op.param == 2:
        return [StmtAssert(orstart.expr, exprs[1]), WantPop(), WantFlow([], orstart.flow, ifstart.flow)]
    else:
        raise PythonError("funny assert params")

@visitor
def _visit_assert_2(
    self: ('has_short_assert', '!has_raise_from'),
    op: FwdFlow,
    start: IfStart,
    body: Block,
):
    if not start.neg or start.pop:
        raise NoMatch
    if (len(body.stmts) != 1
        or not isinstance(body.stmts[0], StmtRaise)
        or not isinstance(body.stmts[0].cls, ExprGlobal)
        or body.stmts[0].cls.name != 'AssertionError'
        or body.stmts[0].tb is not None
    ):
        raise NoMatch
    return [AssertJunk(start.expr, body.stmts[0].val), WantFlow([], start.flow, []), op]

@visitor
def _visit_assert_2(
    self: ('has_short_assert', 'has_raise_from'),
    op: FwdFlow,
    start: IfStart,
    body: Block,
):
    if not start.neg or start.pop:
        raise NoMatch
    if (len(body.stmts) != 1
        or not isinstance(body.stmts[0], StmtRaise)
        or body.stmts[0].tb is not None
    ):
        raise NoMatch
    val = body.stmts[0].cls
    if isinstance(val, ExprGlobal) and val.name == 'AssertionError':
        return [AssertJunk(start.expr, None), WantFlow([], start.flow, [])]
    elif (isinstance(val, ExprCall)
        and isinstance(val.expr, ExprGlobal)
        and val.expr.name == 'AssertionError'
        and len(val.args.args) == 1
        and not val.args.args[0][0]
    ):
        return [AssertJunk(start.expr, val.args.args[0][1]), WantFlow([], start.flow, []), op]
    else:
        raise PythonError("that's still not an assert")

@visitor
def _visit_assert_junk(
    self,
    op: OpcodePopTop,
    junk: AssertJunk,
):
    return [StmtAssert(*junk)]

@visitor
def _visit_assert_or(
    self: 'has_jump_cond_fold',
    op: FwdFlow,
    start: IfStart,
    block: Block,
    junk: AssertJunk,
):
    if not start.neg or start.pop:
        raise NoMatch
    if block.stmts:
        raise NoMatch
    return [AssertJunk(ExprBoolOr(start.expr, junk.expr), junk.msg), WantFlow([], start.flow, []), op]

# raise statement

# Python 1.0 - 1.2
@visitor
def _visit_raise_1(
    self,
    op: OpcodeRaiseException,
    cls: Expr,
    _: ExprNone,
):
    return [StmtRaise(cls)]

@visitor
def _visit_raise_2(
    self,
    op: OpcodeRaiseException,
    cls: Expr,
    val: Expr,
):
    return [StmtRaise(cls, val)]

# Python 1.3-2.7
@visitor
def _visit_raise_varargs(
    self: '!has_raise_from',
    op: OpcodeRaiseVarargs,
    exprs: Exprs('param', 1),
):
    if len(exprs) > 3:
        raise PythonError("too many args to raise")
    if len(exprs) == 0 and not self.version.has_reraise:
        raise PythonError("too few args to raise")
    return [StmtRaise(*exprs)]

# Python 3
@visitor
def _visit_raise_from(
    self: 'has_raise_from',
    op: OpcodeRaiseVarargs,
    exprs: Exprs('param', 1),
):
    if len(exprs) < 2:
        return [StmtRaise(*exprs)]
    elif len(exprs) == 2:
        return [StmtRaise(exprs[0], None, exprs[1])]
    else:
        raise PythonError("too many args to raise")

# exec statement

@visitor
def _visit_exec_3(
    self,
    op: OpcodeExecStmt,
    code: Expr,
    env: Expr,
    _: DupTop,
):
    if isinstance(env, ExprNone):
        return [StmtExec(code, None, None)]
    else:
        return [StmtExec(code, env, None)]

@visitor
def _visit_exec_3(
    self,
    op: OpcodeExecStmt,
    code: Expr,
    globals: Expr,
    locals: Expr,
):
    return [StmtExec(code, globals, locals)]

# imports

@visitor
def _visit_import_name(
    self: '!has_import_as',
    op: OpcodeImportName,
):
    return [Import(op.param, [])]

@visitor
def _visit_store_name_import(
    self,
    op: Store,
    import_: Import,
):
    if import_.items:
        raise PythonError("non-empty items for plain import")
    return [StmtImport(-1, import_.name, [], op.dst)]

@visitor
def _visit_import_from_star(
    self: '!has_import_star',
    op: OpcodeImportFrom,
    import_: Import,
):
    if op.param != '*':
        raise NoMatch
    if import_.items:
        raise PythonError("non-empty items for star import")
    return [StmtImportStar(-1, import_.name), WantPop()]

@visitor
def _visit_import_from(
    self,
    op: OpcodeImportFrom,
    import_: Import,
):
    if op.param == '*':
        raise NoMatch
    import_.items.append(op.param)
    return [import_]

@visitor
def _visit_import_from_end(
    self,
    op: OpcodePopTop,
    import_: Import,
):
    return [StmtFromImport(-1, import_.name, [FromItem(x, None) for x in import_.items])]

# imports - v2

@visitor
def _visit_import_name(
    self: ('has_import_as', '!has_relative_import'),
    op: OpcodeImportName,
    _: ExprNone,
):
    return [Import2Simple(-1, op.param, [])]

@visitor
def _visit_import_name(
    self: 'has_relative_import',
    op: OpcodeImportName,
    level: ExprInt,
    _: ExprNone,
):
    return [Import2Simple(level.val, op.param, [])]

@visitor
def _visit_import_name_attr(
    self,
    op: OpcodeLoadAttr,
    import_: Import2Simple,
):
    import_.attrs.append(op.param)
    return [import_]

@visitor
def _visit_store_name_import(
    self,
    op: Store,
    import_: Import2Simple,
):
    return [StmtImport(import_.level, import_.name, import_.attrs, op.dst)]

@visitor
def _visit_import_name(
    self: ('has_import_as', '!has_relative_import'),
    op: OpcodeImportName,
    expr: ExprTuple,
):
    fromlist = [self.string(item) for item in expr.exprs]
    if fromlist == ['*']:
        return [Import2Star(-1, op.param)]
    else:
        return [Import2From(-1, fromlist, op.param, [])]

@visitor
def _visit_import_name(
    self: 'has_relative_import',
    op: OpcodeImportName,
    level: ExprInt,
    expr: ExprTuple,
):
    fromlist = [self.string(item) for item in expr.exprs]
    if fromlist == ['*']:
        return [Import2Star(level.val, op.param)]
    else:
        return [Import2From(level.val, fromlist, op.param, [])]

@visitor
def _visit_import_star(
    self,
    op: OpcodeImportStar,
    import_: Import2Star,
):
    return [StmtImportStar(import_.level, import_.name)]

@visitor
def _visit_import_from(
    self,
    op: OpcodeImportFrom,
    import_: Import2From,
):
    idx = len(import_.exprs)
    if (idx >= len(import_.fromlist) or import_.fromlist[idx] != op.param):
        raise PythonError("fromlist mismatch")
    return [import_, UnpackSlot(import_, idx)]

@visitor
def _visit_import_from_end(
    self,
    op: OpcodePopTop,
    import_: Import2From,
):
    return [StmtFromImport(import_.level, import_.name, [FromItem(a, b) for a, b in zip(import_.fromlist, import_.exprs)])]

# misc flow

@visitor
def _visit_flow(self, op: FwdFlow, want: WantFlow):
    if op.flow in want.any:
        want.any.remove(op.flow)
    elif op.flow in want.true:
        want.true.remove(op.flow)
    elif op.flow in want.false:
        want.false.remove(op.flow)
    else:
        raise NoMatch
    if not want.any and not want.true and not want.false:
        return []
    else:
        return [want]

@visitor
def _visit_extra(self, op: JumpContinue, extra: WantFlow):
    for x in extra.any[:]:
        if x.dst <= x.src:
            op.flow.append(x)
            extra.any.remove(x)
    if not any(extra):
        return [op]
    return [op, extra]

@visitor
def _visit_extra(self, op: JumpContinue, pop: PopExcept):
    return [op, pop]

@visitor
def _visit_pop_jit(self, op: OpcodeJumpIfTrueOrPop):
    return [JumpIfTrue(op.pos, op.nextpos, [op.flow]), OpcodePopTop(op.pos, op.nextpos)]

@visitor
def _visit_pop_jit(self, op: OpcodeJumpIfFalseOrPop):
    return [JumpIfFalse(op.pos, op.nextpos, [op.flow]), OpcodePopTop(op.pos, op.nextpos)]

@visitor
def _visit_pop_jit(self, op: OpcodeJumpIfTrue):
    return [JumpIfTrue(op.pos, op.nextpos, [op.flow])]

@visitor
def _visit_pop_jit(self, op: OpcodeJumpIfFalse):
    return [JumpIfFalse(op.pos, op.nextpos, [op.flow])]

@visitor
def _visit_pop_jit(self, op: OpcodePopJumpIfTrue):
    return [PopJumpIfTrue(op.pos, op.nextpos, [op.flow])]

@visitor
def _visit_pop_jit(self, op: OpcodePopJumpIfFalse):
    return [PopJumpIfFalse(op.pos, op.nextpos, [op.flow])]

@visitor
def _visit_extra(self, op: JumpIfTrue, extra: WantFlow):
    if extra.false or extra.any:
        raise NoMatch
    return [JumpIfTrue(op.pos, op.nextpos, op.flow + extra.true)]

@visitor
def _visit_extra(self, op: JumpIfFalse, extra: WantFlow):
    if extra.true or extra.any:
        raise NoMatch
    return [JumpIfFalse(op.pos, op.nextpos, op.flow + extra.false)]

@visitor
def _visit_extra(self, op: JumpSkipJunk, extra: WantFlow):
    if extra.true or extra.false:
        raise NoMatch
    return [JumpSkipJunk(op.pos, op.nextpos, op.flow + extra.any)]

@visitor
def _visit_extra(self, op: JumpUnconditional, extra: WantFlow):
    if extra.true or extra.false:
        raise NoMatch
    return [JumpUnconditional(op.pos, op.nextpos, op.flow + extra.any)]

@visitor
def _visit_if_end(
    self,
    op: JumpUnconditional,
    final: FinalElse,
    inner: Block,
):
    return [final.maker(inner), JumpUnconditional(op.pos, op.nextpos, op.flow + final.flow)]

@visitor
def _visit_if_end(
    self,
    op: (FwdFlow, OpcodeEndFinally),
    final: FinalElse,
    inner: Block,
    want: MaybeWantFlow,
):
    return [final.maker(inner), WantFlow(final.flow + want.any, want.true, want.false), op]

# if / and / or

@visitor
def _visit_if(self, op: JumpSkipJunk, block: Block):
    return [block, FinalElse(op.flow, FinalJunk()), Block([]), WantPop()]

@visitor
def _visit_if(self, op: JumpIfFalse, expr: Expr):
    return [IfStart(expr, op.flow, False, False), Block([]), WantPop()]

@visitor
def _visit_if(self, op: JumpIfTrue, expr: Expr):
    return [IfStart(expr, op.flow, True, False), Block([]), WantPop()]

@visitor
def _visit_if(self, op: PopJumpIfFalse, expr: Expr):
    return [IfStart(expr, op.flow, False, True), Block([])]

@visitor
def _visit_if(self, op: PopJumpIfTrue, expr: Expr):
    return [IfStart(expr, op.flow, True, True), Block([])]

@visitor
def _visit_if_else(
    self,
    op: JumpUnconditional,
    block: Block,
    start: IfStart,
    body: Block,
):
    if start.neg:
        if not self.version.has_if_not_opt:
            raise NoMatch
        expr = ExprNot(start.expr)
    else:
        expr = start.expr
    return [
        block,
        FinalElse(op.flow, FinalIf(expr, body)),
        Block([]),
        _maybe_want_pop(start.pop),
        WantFlow(start.flow, [], [])
    ]

@visitor
def _visit_and(
    self,
    op: FwdFlow,
    start: IfStart,
    block: Block,
    expr: Expr,
    want: MaybeWantFlow,
):
    if start.pop:
        raise NoMatch
    if block.stmts:
        raise PythonError("extra and/or statements")
    if start.neg:
        want.true.extend(start.flow)
        return [ExprBoolOr(start.expr, expr), want, op]
    else:
        want.false.extend(start.flow)
        return [ExprBoolAnd(start.expr, expr), want, op]

@visitor
def _visit_and(
    self,
    op: FwdFlow,
    start: IfStart,
    block: Block,
    ret: WantReturn,
    want: MaybeWantFlow,
):
    if start.pop:
        raise NoMatch
    if block.stmts:
        raise PythonError("extra and/or statements")
    if start.neg:
        want.true.extend(start.flow)
        return [WantReturn(ExprBoolOr(start.expr, ret.expr)), want, op]
    else:
        want.false.extend(start.flow)
        return [WantReturn(ExprBoolAnd(start.expr, ret.expr)), want, op]

@visitor
def _visit_folded_if(
    self: 'has_jump_cond_fold',
    op: FwdFlow,
    start: IfStart,
    blocka: Block,
    final: FinalElse,
    blockb: Block,
    _: WantPop,
):
    if start.pop or start.neg:
        raise NoMatch
    if blocka.stmts:
        raise PythonError("extra and-if statements")
    if_ = final.maker
    if not isinstance(if_, FinalIf):
        raise NoMatch
    return [FinalElse(final.flow, FinalIf(ExprBoolAnd(start.expr, if_.expr), if_.body)), blockb, WantPop(), WantFlow([], [], start.flow), op]

@visitor
def _visit_folded_if(
    self: 'has_jump_cond_fold',
    op: FwdFlow,
    start: IfStart,
    block: Block,
    _: WantPop,
    want: MaybeWantFlow,
):
    if start.pop or start.neg:
        raise NoMatch
    if len(block.stmts) != 1:
        raise PythonError("extra and-ifdead statements")
    if_ = block.stmts[0]
    if not isinstance(if_, StmtIfDead):
        raise PythonError("wrong and-ifdead statements")
    want.false.extend(start.flow)
    return [StmtIfDead(ExprBoolAnd(start.expr, if_.cond), if_.body), WantPop(), want, op]

@visitor
def _visit_ifexpr(self: 'has_if_expr', op: JumpUnconditional, expr: Expr):
    return [IfExprTrue(expr, op.flow)]

@visitor
def _visit_ifexpr(
    self,
    op: FwdFlow,
    start: IfStart,
    block: Block,
    true: IfExprTrue,
):
    if start.pop:
        raise NoMatch
    if op.flow not in start.flow:
        raise NoMatch
    if block.stmts:
        raise PythonError("extra if expr statements")
    if start.neg:
        expr = ExprNot(start.expr)
    else:
        expr = start.expr
    return [
        IfExprElse(expr, true.expr, true.flow),
        _maybe_want_pop(start.pop),
        WantFlow(start.flow, [], []),
        op
    ]

@visitor
def _visit_ifexpr(
    self,
    op: FwdFlow,
    if_: IfExprElse,
    false: Expr,
    want: MaybeWantFlow,
):
    res = ExprIf(if_.cond, if_.true, false)
    want.any.extend(if_.flow)
    return [ExprIf(if_.cond, if_.true, false), want, op]

@visitor
def _visit_folded_if(
    self: 'has_jump_cond_fold',
    op: FwdFlow,
    start: IfStart,
    block: Block,
    if_: IfExprElse,
    _: WantPop,
    want: MaybeWantFlow,
):
    if start.pop or start.neg:
        raise NoMatch
    if block.stmts:
        raise PythonError("extra and-if expr statements")
    want.false.extend(start.flow)
    return [IfExprElse(ExprBoolAnd(start.expr, if_.cond), if_.true, if_.flow), WantPop(), want, op]

@visitor
def _visit_ifexpr(
    self,
    op: FwdFlow,
    start: IfStart,
    block: Block,
    true: IfExprTrue,
):
    if start.pop:
        raise NoMatch
    if op.flow in start.flow:
        raise NoMatch
    if block.stmts:
        raise PythonError("extra if expr and/or statements")
    if not start.neg:
        return [IfExprTrue(ExprBoolAnd(start.expr, true.expr), start.flow + true.flow), op]
    else:
        return [IfExprTrue(ExprBoolOr(start.expr, true.expr), start.flow + true.flow), op]

@visitor
def _visit_ifexpr_true(self, op: JumpSkipJunk, expr: Expr):
    return [
        IfExprElse(ExprAnyTrue(), expr, op.flow),
        WantPop()
    ]

# XXX nuke it
def _ensure_dead_end(deco, block):
    if not block.stmts:
        raise PythonError("empty dead block")
    final = block.stmts[-1]
    if isinstance(final, StmtFinalContinue):
        pass
    elif isinstance(final, StmtReturn) and deco.version.has_dead_return:
        pass
    elif isinstance(final, StmtIf):
        for item in final.items:
            _ensure_dead_end(deco, item[1])
        _ensure_dead_end(deco, final.else_)
    else:
        raise PythonError("invalid dead block {}".format(final))

def _process_dead_end(deco, block):
    if not block.stmts:
        raise PythonError("empty dead block")
    final = block.stmts[-1]
    if isinstance(final, StmtContinue):
        block.stmts[-1] = StmtFinalContinue()
    elif isinstance(final, StmtFinalContinue):
        pass
    elif isinstance(final, StmtReturn) and deco.version.has_dead_return:
        pass
    elif isinstance(final, StmtIfDead):
        pass
    elif isinstance(final, StmtIfRaw):
        # XXX eh
        final.else_ = _process_dead_end(deco, final.else_)
    elif isinstance(final, StmtExcept):
        # XXX eh
        final.else_ = _process_dead_end(deco, final.else_)
    elif isinstance(final, StmtLoop):
        final.else_ = _process_dead_end(deco, final.else_)
    else:
        raise PythonError("invalid dead block {}".format(final))
    return block

@visitor
def _visit_dead_if(
    self,
    op: FwdFlow,
    start: IfStart,
    block: Block,
    want: MaybeWantFlow,
):
    block = _process_dead_end(self, block)
    if start.neg:
        expr = ExprNot(start.expr)
    else:
        expr = start.expr
    if any(want):
        return [
            FinalElse(want.any + want.true + want.false, FinalIf(expr, block)),
            Block([]),
            _maybe_want_pop(start.pop),
            WantFlow(start.flow, [], []),
            op
        ]
    elif op.flow in start.flow:
        return [
            StmtIfDead(expr, block),
            _maybe_want_pop(start.pop),
            WantFlow(start.flow, [], []),
            op
        ]
    else:
        true = unreturn(block)
        # TODO: somehow verify stuff is going to be returned in this case
        return [start, Block([]), IfExprTrue(true, []), op]

# comparisons

@visitor
def _visit_cmp(
    self,
    op: OpcodeCompareOp,
    e1: Expr, e2: Expr,
):
    if op.param is CmpOp.EXC_MATCH:
        raise NoMatch
    return [ExprCmp(e1, [CmpItem(op.param, e2)])]

# chained comparisons

# start #1
@visitor
def _visit_cmp_start(
    self,
    op: OpcodeCompareOp,
    a: Expr, b: Expr,
    _dup: DupTop, _rot: RotThree,
):
    if op.param is CmpOp.EXC_MATCH:
        raise NoMatch
    return [CompareStart(a, [CmpItem(op.param, b)], [])]

# start #2 and middle #3
@visitor
def _visit_cmp_jump(self, op: JumpIfFalse, cmp: CompareStart):
    return [Compare(cmp.first, cmp.rest, cmp.flows + op.flow), WantPop()]

# middle #2
@visitor
def _visit_cmp_next(
    self,
    op: OpcodeCompareOp,
    cmp: Compare, expr: Expr,
    _dup: DupTop, _rot: RotThree,
):
    if op.param is CmpOp.EXC_MATCH:
        raise NoMatch
    return [CompareStart(cmp.first, cmp.rest + [CmpItem(op.param, expr)], cmp.flows)]

# end #1
@visitor
def _visit_cmp_last(
    self,
    op: OpcodeCompareOp,
    cmp: Compare, expr: Expr,
):
    if op.param is CmpOp.EXC_MATCH:
        raise NoMatch
    return [CompareLast(cmp.first, cmp.rest + [CmpItem(op.param, expr)], cmp.flows)]

# end #2
@visitor
def _visit_cmp_last_jump(self, op: JumpUnconditional, cmp: CompareLast):
    return [
        ExprCmp(cmp.first, cmp.rest),
        WantFlow(op.flow, [], []),
        WantRotPop(),
        WantFlow([], [], cmp.flows)
    ]

# end #2 - return
@visitor
def _visit_cmp_last_jump(
    self: 'has_dead_return',
    op: OpcodeReturnValue,
    cmp: CompareLast,
):
    return [
        WantReturn(ExprCmp(cmp.first, cmp.rest)),
        WantRotPop(),
        WantFlow([], [], cmp.flows),
    ]

@visitor
def _visit_want_return(self, op: OpcodeReturnValue, want: WantReturn):
    return [StmtReturn(want.expr)]

# $loop framing

@visitor
def _visit_setup_loop(self, op: OpcodeSetupLoop):
    return [SetupLoop(op.flow), Block([])]

@visitor
def _visit_pop_loop(
    self,
    op: OpcodePopBlock,
    setup: SetupLoop,
    block: Block,
):
    return [FinalElse([setup.flow], FinalLoop(block)), Block([])]

# actual loops

@visitor
def _visit_loop(self, op: RevFlow):
    return [Loop(op.flow), Block([])]

# continue

CONTINUABLES = (
    ForLoop,
    Block,
    IfStart,
    FinalElse,
    TryExceptMid,
    TryExceptMatch,
    TryExceptAny,
)

@visitor
def _visit_continue(
    self,
    op: JumpContinue,
    loop: Loop,
    items: LoopDammit,
):
    for item in items:
        if isinstance(item, CONTINUABLES) or isinstance(item, (TopForLoop, TryExceptEndTry)):
            pass
        else:
            raise NoMatch
    if not all(flow in loop.flow for flow in op.flow):
        raise NoMatch
    for flow in op.flow:
        loop.flow.remove(flow)
    return [loop] + items + [StmtContinue()]

@visitor
def _visit_continue(
    self,
    op: OpcodeContinueLoop,
    loop: Loop,
    items: LoopDammit,
):
    seen = False
    for item in items:
        if isinstance(item, (SetupExcept, SetupFinally, With)):
            seen = True
        elif isinstance(item, CONTINUABLES):
            pass
        else:
            raise NoMatch
    if not seen:
        raise PythonError("got CONTINUE_LOOP where a JUMP_ABSOLUTE would suffice")
    if op.flow not in loop.flow:
        raise NoMatch
    loop.flow.remove(op.flow)
    return [loop] + items + [StmtContinue()]

# while loop

def _loopit(block):
    if (len(block.stmts) == 1
        and isinstance(block.stmts[0], StmtIfDead)
    ):
        if_ = block.stmts[0]
        return Block([StmtWhileRaw(if_.cond, if_.body)])
    else:
        raise PythonError("weird while loop")

@visitor
def _visit_while(
    self,
    op: OpcodePopBlock,
    setup: SetupLoop,
    empty: Block,
    loop: Loop,
    body: Block,
):
    if empty.stmts:
        raise PythonError("junk before while in loop")
    if loop.flow:
        raise PythonError("loop not dry in pop block")
    return [FinalElse([setup.flow], FinalLoop(_loopit(body))), Block([])]


@visitor
def _visit_while_true(
    self: '!has_while_true_end_opt',
    op: OpcodePopTop,
    loop: Loop,
    body: Block,
):
    if loop.flow:
        raise PythonError("loop not dry in pop block")
    return [StmtWhileRaw(ExprAnyTrue(), _process_dead_end(self, body))]


def _split_inf_loop(deco, stmts, cont_ok):
    split = None
    for idx, stmt in enumerate(stmts):
        if isinstance(stmt, StmtContinue):
            if cont_ok:
                split = idx
                sstmt = StmtFinalContinue()
            else:
                break
        elif isinstance(stmt, StmtReturn) and deco.version.has_dead_return:
            split = idx
            sstmt = stmt
    if split is None:
        raise PythonError("no split in optimized infinite loop")
    return Block(stmts[:split] + [sstmt]), Block(stmts[split+1:])

def _make_inf_loop(deco, stmts, cont_ok):
    body, else_ = _split_inf_loop(deco, stmts, cont_ok)
    return StmtLoop(
        Block([StmtWhileRaw(
            ExprAnyTrue(),
            body
        )]),
        else_
    )


@visitor
def _visit_while_true(
    self: 'has_while_true_end_opt',
    op: (JumpUnconditional, FwdFlow),
    setup: SetupLoop,
    block: Block,
    loop: Loop,
    body: Block,
):
    if block.stmts:
        raise PythonError("junk in optimized infinite loop")
    if loop.flow:
        raise PythonError("loop not dry in fake pop block")
    return [_make_inf_loop(self, body.stmts, True), WantFlow([setup.flow], [], []), op]


@visitor
def _visit_while_true(
    self: ('has_while_true_end_opt', 'has_dead_return'),
    op: (JumpUnconditional, FwdFlow),
    setup: SetupLoop,
    body: Block,
):
    return [_make_inf_loop(self, body.stmts, False), WantFlow([setup.flow], [], []), op]

@visitor
def _visit_continue(
    self,
    op: JumpContinue,
    setup: SetupLoop,
    block: Block,
    loop: Loop,
    body: Block,
    items: LoopDammit,
):
    for item in items:
        if isinstance(item, CONTINUABLES) or isinstance(item, (TopForLoop, TryExceptEndTry)):
            pass
        else:
            raise NoMatch
    if loop.flow:
        raise PythonError("got outer continue, but inner loop not dry yet")
    if block.stmts:
        raise PythonError("non-empty loop block in outer continue")
    body, else_ = _split_inf_loop(self, body.stmts, True)
    return [
        FinalElse([setup.flow], FinalLoop(Block([StmtWhileRaw(ExprAnyTrue(), body)]))),
        else_
    ] + items + [op]

# for loop

@visitor
def _visit_for_start(
    self,
    op: OpcodeForLoop,
    expr: Expr,
    zero: ExprInt,
    loop: Loop,
    block: Block,
):
    if block.stmts:
        raise PythonError("junk in for")
    if zero.val != 0:
        raise PythonError("funny for loop start")
    return [loop, ForStart(expr, op.flow)]

@visitor
def visit_store_multi_start(self, op: Store, start: ForStart):
    return [
        ForLoop(start.expr, op.dst, start.flow),
        Block([])
    ]

@visitor
def _visit_for_end(
    self,
    op: FwdFlow,
    loop: Loop,
    for_: ForLoop,
    body: Block,
):
    if op.flow != for_.flow:
        raise NoMatch
    if loop.flow:
        raise PythonError("mismatched for loop")
    body = _process_dead_end(self, body)
    return [StmtForRaw(for_.expr, for_.dst, body)]

@visitor
def _visit_for_end(
    self,
    op: JumpContinue,
    loop: Loop,
    for_: ForLoop,
    body: Block,
):
    if loop.flow:
        raise NoMatch
    body = _process_dead_end(self, body)
    return [StmtForRaw(for_.expr, for_.dst, body), WantFlow([for_.flow], [], []), op]

@visitor
def _visit_for_end(
    self,
    op: JumpUnconditional,
    loop: Loop,
    for_: ForLoop,
    body: Block,
):
    if loop.flow:
        raise NoMatch
    body = _process_dead_end(self, body)
    return [StmtForRaw(for_.expr, for_.dst, body), WantFlow([for_.flow], [], []), op]

# new for loop

@visitor
def visit_get_iter(self, op: OpcodeGetIter, expr: Expr):
    return [Iter(expr)]

@visitor
def _visit_for_iter(
    self,
    op: OpcodeForIter,
    iter_: Iter,
    loop: Loop,
    block: Block,
):
    if block.stmts:
        raise PythonError("junk in for")
    return [loop, ForStart(iter_.expr, op.flow)]

@visitor
def _visit_for_iter(
    self: 'has_dead_return',
    op: OpcodeForIter,
    iter_: Iter,
):
    return [Loop([]), ForStart(iter_.expr, op.flow)]

@visitor
def _visit_for_iter(
    self,
    op: OpcodeForIter,
    expr: Expr,
    loop: Loop,
    block: Block,
):
    if block.stmts:
        raise PythonError("junk in for")
    return [loop, TopForStart(expr, op.flow)]

@visitor
def visit_store_multi_start(self, op: Store, start: TopForStart):
    return [
        TopForLoop(start.expr, op.dst, start.flow),
        Block([])
    ]

@visitor
def _visit_for_end(
    self,
    op: FwdFlow,
    loop: Loop,
    top: TopForLoop,
    body: Block,
):
    if op.flow != top.flow:
        raise NoMatch
    if loop.flow:
        raise PythonError("mismatched for loop")
    body = _process_dead_end(self, body)
    return [StmtForTop(top.expr, top.dst, body)]

# access

@visitor
def _visit_access(self, op: OpcodeAccessMode, mode: ExprInt):
    return [StmtAccess(op.param, mode.val)]

# try finally

# need block to make sure we're not inside with
@visitor
def _visit_setup_finally(self, op: OpcodeSetupFinally, block: Block):
    return [block, SetupFinally(op.flow), Block([])]

@visitor
def _visit_finally_pop(
    self,
    op: OpcodePopBlock,
    setup: SetupFinally,
    block: Block,
):
    return [TryFinallyPending(block, setup.flow)]

@visitor
def _visit_finally(
    self,
    op: FwdFlow,
    try_: TryFinallyPending,
    _: ExprNone,
):
    if try_.flow != op.flow:
        raise PythonError("funny finally")
    return [TryFinally(try_.body), Block([])]

@visitor
def _visit_finally_end(
    self,
    op: OpcodeEndFinally,
    try_: TryFinally,
    inner: Block,
):
    return [StmtFinally(try_.body, inner)]

# try except

# start try except - store address of except clause

@visitor
def _visit_setup_except(self, op: OpcodeSetupExcept):
    return [SetupExcept(op.flow), Block([])]

# finish try clause - pop block & jump to else clause, start except clause

@visitor
def _visit_except_pop_try(self, op: OpcodePopBlock, setup: SetupExcept, block: Block):
    return [TryExceptEndTry(setup.flow, block)]

@visitor
def _visit_except_end_try(self, op: JumpUnconditional, try_: TryExceptEndTry):
    return [TryExceptMid(op.flow, try_.body, [], None, []), WantFlow([try_.flow], [], [])]

@visitor
def _visit_except_end_try(self, op: StmtContinue, try_: TryExceptEndTry):
    return [TryExceptMid([], Block(try_.body.stmts + [StmtFinalContinue()]), [], None, []), WantFlow([try_.flow], [], [])]

# except match clause:
#
# - dup exception type
# - compare with expression
# - jump to next if unmatched
# - pop comparison result and type
# - either pop or store value
# - pop traceback

@visitor
def _visit_except_match_check(
    self,
    op: OpcodeCompareOp,
    try_: TryExceptMid,
    _: DupTop,
    expr: Expr,
):
    if try_.any:
        raise PythonError("making an except match after blanket")
    if op.param != CmpOp.EXC_MATCH:
        raise PythonError("funny except match")
    return [try_, TryExceptMatchMid(expr)]

@visitor
def _visit_except_match_jump(
    self: '!has_new_jump',
    op: JumpIfFalse,
    mid: TryExceptMatchMid,
):
    return [
        TryExceptMatchOk(mid.expr, op.flow),
        WantPop(),
        WantPop()
    ]

@visitor
def _visit_except_match_jump(
    self: 'has_new_jump',
    op: PopJumpIfFalse,
    mid: TryExceptMatchMid,
):
    return [
        TryExceptMatchOk(mid.expr, op.flow),
        WantPop(),
    ]

@visitor
def _visit_except_match_pop(self, op: OpcodePopTop, try_: TryExceptMatchOk):
    return [
        TryExceptMatch(try_.expr, None, try_.next),
        Block([]),
        WantPop()
    ]

@visitor
def _visit_except_match_store(self, op: Store, match: TryExceptMatchOk):
    return [
        TryExceptMatch(match.expr, op.dst, match.next),
        Block([]),
        WantPop()
    ]

@visitor
def _visit_except_match_end(
    self,
    op: FwdFlow,
    try_: TryExceptMid,
    match: TryExceptMatch,
    block: Block,
    want: MaybeWantFlow,
    _: PopExcept,
):
    return [
        TryExceptMid(
            try_.else_,
            try_.body,
            try_.items + [ExceptClause(match.expr, match.dst, _process_dead_end(self, block))],
            None,
            try_.flows + want.any + want.true + want.false,
        ),
        _maybe_want_pop(self.version.has_new_jump),
        WantFlow([], [], match.next),
        op
    ]

@visitor
def _visit_except_match_end(
    self,
    op: JumpUnconditional,
    try_: TryExceptMid,
    match: TryExceptMatch,
    block: Block,
    _: PopExcept,
):
    return [
        TryExceptMid(
            try_.else_,
            try_.body,
            try_.items + [ExceptClause(match.expr, match.dst, block)],
            None,
            try_.flows + op.flow,
        ),
        _maybe_want_pop(self.version.has_new_jump),
        WantFlow([], [], match.next)
    ]

@visitor
def _visit_except_match_end(
    self: '!has_pop_except',
    op: JumpUnconditional,
    try_: TryExceptMid,
    match: TryExceptMatch,
    block: Block,
):
    return [
        TryExceptMid(
            try_.else_,
            try_.body,
            try_.items + [ExceptClause(match.expr, match.dst, block)],
            None,
            try_.flows + op.flow,
        ),
        _maybe_want_pop(self.version.has_new_jump),
        WantFlow([], [], match.next)
    ]

@visitor
def _visit_except_match_end(
    self: '!has_pop_except',
    op: FwdFlow,
    try_: TryExceptMid,
    match: TryExceptMatch,
    block: Block,
    want: MaybeWantFlow,
):
    block = _process_dead_end(self, block)
    return [
        TryExceptMid(
            try_.else_,
            try_.body,
            try_.items + [ExceptClause(match.expr, match.dst, block)],
            None,
            try_.flows + want.any + want.true + want.false,
        ),
        _maybe_want_pop(self.version.has_new_jump),
        WantFlow([], [], match.next),
        op
    ]

@visitor
def _visit_except_any(
    self,
    op: OpcodePopTop,
    try_: TryExceptMid,
):
    if try_.any:
        raise PythonError("making a second except blanket")
    return [
        try_,
        TryExceptAny(),
        Block([]),
        WantPop(),
        WantPop()
    ]

@visitor
def _visit_except_any_end(
    self,
    op: JumpUnconditional,
    try_: TryExceptMid,
    _: TryExceptAny,
    block: Block,
    _2: PopExcept,
):
    return [
        TryExceptMid(
            try_.else_,
            try_.body,
            try_.items,
            block,
            try_.flows + op.flow,
        )
    ]

@visitor
def _visit_except_any_end(
    self: '!has_pop_except',
    op: JumpUnconditional,
    try_: TryExceptMid,
    _: TryExceptAny,
    block: Block,
):
    return [
        TryExceptMid(
            try_.else_,
            try_.body,
            try_.items,
            block,
            try_.flows + op.flow,
        )
    ]

@visitor
def _visit_except_any_end(
    self: '!has_pop_except',
    op: OpcodeEndFinally,
    try_: TryExceptMid,
    _: TryExceptAny,
    block: Block,
    want: MaybeWantFlow,
):
    block = _process_dead_end(self, block)
    return [
        TryExceptMid(
            try_.else_,
            try_.body,
            try_.items,
            block,
            try_.flows + want.any + want.true + want.false,
        ),
        op
    ]

@visitor
def _visit_except_any_end(
    self,
    op: OpcodeEndFinally,
    try_: TryExceptMid,
    _: TryExceptAny,
    block: Block,
    want: MaybeWantFlow,
    _2: PopExcept,
):
    block = _process_dead_end(self, block)
    return [
        TryExceptMid(
            try_.else_,
            try_.body,
            try_.items,
            block,
            try_.flows + want.any + want.true + want.false,
        ),
        op
    ]

@visitor
def _visit_except_end(
    self,
    op: OpcodeEndFinally,
    try_: TryExceptMid,
):
    if try_.flows:
        if try_.else_:
            return [
                FinalElse(try_.flows, FinalExcept(try_.body, try_.items, try_.any)),
                Block([]),
                WantFlow(try_.else_, [], [])
            ]
        else:
            return [
                FinalElse(try_.flows, FinalExcept(try_.body, try_.items, try_.any)),
                Block([]),
            ]
    elif try_.else_:
        return [
            StmtExceptDead(try_.body, try_.items, try_.any),
            WantFlow(try_.else_, [], [])
        ]
    else:
        return [
            StmtExceptDead(try_.body, try_.items, try_.any),
        ]


# functions & classes

# make function - py 1.0 - 1.2

@visitor
def _visit_build_function(
    self,
    op: OpcodeBuildFunction,
    code: Code,
):
    return [ExprFunctionRaw(deco_code(code), [], {}, {}, [])]

@visitor
def _visit_set_func_args(
    self,
    op: OpcodeSetFuncArgs,
    args: ExprTuple,
    fun: ExprFunctionRaw,
):
    # bug alert: def f(a, b=1) is compiled as def f(a=1, b)
    return [ExprFunctionRaw(fun.code, args.exprs, {}, {}, [])]

# make function - py 1.3+

@visitor
def _visit_make_function(
    self,
    op: OpcodeMakeFunction,
    args: Exprs('param', 1),
    code: Code,
):
    return [ExprFunctionRaw(deco_code(code), args, {}, {}, [])]

@visitor
def _visit_make_function(
    self: '!has_qualname',
    op: OpcodeMakeFunctionNew,
    kwargs: Exprs('kwargs', 2),
    args: Exprs('args', 1),
    ann: Exprs('ann', 1),
    code: Code,
):
    return [ExprFunctionRaw(
        deco_code(code),
        args,
        {self.string(name): arg for name, arg in kwargs},
        self.make_ann(ann),
        []
    )]

@visitor
def _visit_make_function(
    self: ('has_qualname', 'has_reversed_def_kwargs'),
    op: OpcodeMakeFunctionNew,
    kwargs: Exprs('kwargs', 2),
    args: Exprs('args', 1),
    ann: Exprs('ann', 1),
    code: Code,
    qualname: ExprUnicode,
):
    # XXX qualname
    return [ExprFunctionRaw(
        deco_code(code),
        args,
        {self.string(name): arg for name, arg in kwargs},
        self.make_ann(ann),
        []
    )]

@visitor
def _visit_make_function(
    self: ('has_qualname', '!has_reversed_def_kwargs'),
    op: OpcodeMakeFunctionNew,
    args: Exprs('args', 1),
    kwargs: Exprs('kwargs', 2),
    ann: Exprs('ann', 1),
    code: Code,
    qualname: ExprUnicode,
):
    # XXX qualname
    return [ExprFunctionRaw(
        deco_code(code),
        args,
        {self.string(name): arg for name, arg in kwargs},
        self.make_ann(ann),
        []
    )]

@visitor
def visit_closure_tuple(
    self,
    op: OpcodeBuildTuple,
    closures: Closures,
):
    return [ClosuresTuple([closure.var for closure in closures])]

@visitor
def _visit_make_function(
    self: '!has_sane_closure',
    op: OpcodeMakeClosure,
    args: Exprs('param', 1),
    closures: UglyClosures,
    code: Code,
):
    return [ExprFunctionRaw(deco_code(code), args, {}, {}, closures)]

@visitor
def _visit_make_function(
    self: 'has_sane_closure',
    op: OpcodeMakeClosure,
    args: Exprs('param', 1),
    closures: ClosuresTuple,
    code: Code,
):
    return [ExprFunctionRaw(deco_code(code), args, {}, {}, closures.vars)]

@visitor
def _visit_make_function(
    self: '!has_qualname',
    op: OpcodeMakeClosureNew,
    kwargs: Exprs('kwargs', 2),
    args: Exprs('args', 1),
    ann: Exprs('ann', 1),
    closures: ClosuresTuple,
    code: Code,
):
    return [ExprFunctionRaw(
        deco_code(code),
        args,
        {self.string(name): arg for name, arg in kwargs},
        self.make_ann(ann),
        closures.vars
    )]

@visitor
def _visit_make_function(
    self: ('has_qualname', 'has_reversed_def_kwargs'),
    op: OpcodeMakeClosureNew,
    kwargs: Exprs('kwargs', 2),
    args: Exprs('args', 1),
    ann: Exprs('ann', 1),
    closures: ClosuresTuple,
    code: Code,
    qualname: ExprUnicode,
):
    # XXX qualname
    return [ExprFunctionRaw(
        deco_code(code),
        args,
        {self.string(name): arg for name, arg in kwargs},
        self.make_ann(ann),
        closures.vars
    )]

@visitor
def _visit_make_function(
    self: ('has_qualname', '!has_reversed_def_kwargs'),
    op: OpcodeMakeClosureNew,
    args: Exprs('args', 1),
    kwargs: Exprs('kwargs', 2),
    ann: Exprs('ann', 1),
    closures: ClosuresTuple,
    code: Code,
    qualname: ExprUnicode,
):
    # XXX qualname
    return [ExprFunctionRaw(
        deco_code(code),
        args,
        {self.string(name): arg for name, arg in kwargs},
        self.make_ann(ann),
        closures.vars
    )]

@visitor
def _visit_unary_call(
    self,
    op: OpcodeUnaryCall,
    fun: ExprFunctionRaw,
):
    if fun.defargs:
        raise PythonError("class call with a function with default arguments")
    return [UnaryCall(fun.code)]

@visitor
def visit_load_closure(
    self,
    op: OpcodeLoadClosure,
):
    return [Closure(self.deref(op.param))]

@visitor
def _visit_build_class(
    self,
    op: OpcodeBuildClass,
    name: Expr,
    bases: ExprTuple,
    call: UnaryCall,
):
    return [ExprClassRaw(
        self.string(name),
        CallArgs([CallArgPos(expr) for expr in bases.exprs]),
        call.code,
        []
    )]

@visitor
def _visit_build_class(
    self: 'has_kwargs',
    op: OpcodeBuildClass,
    name: Expr,
    bases: ExprTuple,
    call: ExprCall,
):
    if call.args.args:
        raise PythonError("class call with args")
    fun = call.expr
    if not isinstance(fun, ExprFunctionRaw):
        raise PythonError("class call with non-function")
    if fun.defargs or fun.defkwargs or fun.ann:
        raise PythonError("class call with a function with default arguments")
    return [ExprClassRaw(
        self.string(name),
        CallArgs([CallArgPos(expr) for expr in bases.exprs]),
        fun.code,
        fun.closures
    )]

@visitor
def _visit_return_locals(
    self,
    op: OpcodeReturnValue,
    _: Locals,
):
    return [StmtEndClass()]

@visitor
def _visit_reserve_fast(
    self,
    op: OpcodeReserveFast,
):
    if self.varnames is not None:
        raise PythonError("duplicate RESERVE_FAST")

    self.varnames = op.param
    return []

@visitor
def _visit_load_build_class(
    self,
    op: OpcodeStoreLocals,
    fast: ExprFast,
):
    if fast.idx != 0 or fast.name != '__locals__':
        raise PythonError("funny locals store")
    return [StmtStartClass()]

@visitor
def _visit_return_locals(
    self,
    op: OpcodeReturnValue,
    closure: Closure,
):
    if closure.var.name != '__class__':
        raise PythonError("returning a funny closure")
    return [StmtReturnClass()]

# inplace assignments

def _register_inplace(otype, stype):
    @visitor
    def _visit_inplace(self, op: otype):
        return [Inplace(stype)]

INPLACE_OPS = [
    (OpcodeInplaceAdd, StmtInplaceAdd),
    (OpcodeInplaceSubtract, StmtInplaceSubtract),
    (OpcodeInplaceMultiply, StmtInplaceMultiply),
    (OpcodeInplaceDivide, StmtInplaceDivide),
    (OpcodeInplaceModulo, StmtInplaceModulo),
    (OpcodeInplacePower, StmtInplacePower),
    (OpcodeInplaceLshift, StmtInplaceLshift),
    (OpcodeInplaceRshift, StmtInplaceRshift),
    (OpcodeInplaceAnd, StmtInplaceAnd),
    (OpcodeInplaceOr, StmtInplaceOr),
    (OpcodeInplaceXor, StmtInplaceXor),
    (OpcodeInplaceTrueDivide, StmtInplaceTrueDivide),
    (OpcodeInplaceFloorDivide, StmtInplaceFloorDivide),
    (OpcodeInplaceMatrixMultiply, StmtInplaceMatrixMultiply),
]

for op, stmt in INPLACE_OPS:
    _register_inplace(op, stmt)

@visitor
def _visit_inplace_simple(
    self,
    op: Inplace,
    dst: (ExprName, ExprGlobal, ExprFast, ExprDeref),
    src: Expr,
):
    return [InplaceSimple(dst, src, op.stmt)]

@visitor
def _visit_inplace_attr(
    self,
    op: Inplace,
    dup: DupAttr,
    src: Expr,
):
    return [InplaceAttr(dup.expr, dup.name, src, op.stmt)]

@visitor
def _visit_inplace_subscr(
    self,
    op: Inplace,
    dup: DupSubscr,
    src: Expr,
):
    return [InplaceSubscr(dup.expr, dup.index, src, op.stmt)]

@visitor
def _visit_inplace_slice_nn(
    self,
    op: Inplace,
    dup: DupSliceNN,
    src: Expr,
):
    return [InplaceSliceNN(dup.expr, src, op.stmt)]

@visitor
def _visit_inplace_slice_en(
    self,
    op: Inplace,
    dup: DupSliceEN,
    src: Expr,
):
    return [InplaceSliceEN(dup.expr, dup.start, src, op.stmt)]

@visitor
def _visit_inplace_slice_ne(
    self,
    op: Inplace,
    dup: DupSliceNE,
    src: Expr,
):
    return [InplaceSliceNE(dup.expr, dup.end, src, op.stmt)]

@visitor
def _visit_inplace_slice_ee(
    self,
    op: Inplace,
    dup: DupSliceEE,
    src: Expr,
):
    return [InplaceSliceEE(dup.expr, dup.start, dup.end, src, op.stmt)]

@visitor
def _visit_load_attr_dup(
    self,
    op: OpcodeLoadAttr,
    expr: Expr,
    _: DupTop,
):
    return [DupAttr(expr, op.param)]

@visitor
def _visit_load_subscr_dup(
    self,
    op: OpcodeBinarySubscr,
    a: Expr,
    b: Expr,
    _dup: DupTwo,
):
    return [DupSubscr(a, b)]

@visitor
def _visit_slice_nn_dup(
    self,
    op: OpcodeSliceNN,
    expr: Expr,
    _: DupTop,
):
    return [DupSliceNN(expr)]

@visitor
def _visit_slice_en_dup(
    self,
    op: OpcodeSliceEN,
    a: Expr,
    b: Expr,
    _dup: DupTwo,
):
    return [DupSliceEN(a, b)]

@visitor
def _visit_slice_ne_dup(
    self,
    op: OpcodeSliceNE,
    a: Expr,
    b: Expr,
    _dup: DupTwo,
):
    return [DupSliceNE(a, b)]

@visitor
def _visit_slice_ee_dup(
    self,
    op: OpcodeSliceEE,
    a: Expr,
    b: Expr,
    c: Expr,
    _dup: DupThree,
):
    return [DupSliceEE(a, b, c)]

@visitor
def _visit_inplace_store_name(
    self,
    op: Store,
    inp: InplaceSimple
):
    if inp.dst != op.dst:
        raise PythonError("simple inplace dest mismatch")
    return [inp.stmt(inp.dst, inp.src)]

@visitor
def _visit_inplace_store_attr(
    self,
    op: OpcodeStoreAttr,
    inp: InplaceAttr,
    _: RotTwo
):
    if inp.name != op.param:
        raise PythonError("inplace name mismatch")
    return [inp.stmt(ExprAttr(inp.expr, inp.name), inp.src)]

@visitor
def _visit_inplace_store_subscr(
    self,
    op: OpcodeStoreSubscr,
    inp: InplaceSubscr,
    _rot: RotThree,
):
    return [inp.stmt(ExprSubscr(inp.expr, inp.index), inp.src)]

@visitor
def _visit_inplace_store_slice_nn(
    self,
    op: OpcodeStoreSliceNN,
    inp: InplaceSliceNN,
    _rot: RotTwo,
):
    return [inp.stmt(ExprSubscr(inp.expr, ExprSlice2(None, None)), inp.src)]

@visitor
def _visit_inplace_store_slice_en(
    self,
    op: OpcodeStoreSliceEN,
    inp: InplaceSliceEN,
    _rot: RotThree,
):
    return [inp.stmt(ExprSubscr(inp.expr, ExprSlice2(inp.start, None)), inp.src)]

@visitor
def _visit_inplace_store_slice_ne(
    self,
    op: OpcodeStoreSliceNE,
    inp: InplaceSliceNE,
    _rot: RotThree,
):
    return [inp.stmt(ExprSubscr(inp.expr, ExprSlice2(None, inp.end)), inp.src)]

@visitor
def _visit_inplace_store_slice_ee(
    self,
    op: OpcodeStoreSliceEE,
    inp: InplaceSliceEE,
    _rot: RotFour,
):
    return [inp.stmt(ExprSubscr(inp.expr, ExprSlice2(inp.start, inp.end)), inp.src)]

# list comprehensions

@visitor
def visit_listcomp_start(
    self,
    op: Store,
    dup: DupAttr,
):
    if not isinstance(op.dst, (ExprName, ExprFast, ExprGlobal)):
        raise NoMatch
    return [TmpVarAttrStart(op.dst, dup.expr, dup.name)]

@visitor
def _visit_listcomp(
    self: '!has_list_append',
    op: StmtForRaw,
    start: TmpVarAttrStart,
):
    if (not isinstance(start.expr, ExprList)
        or len(start.expr.exprs) != 0
        or start.name != 'append'):
        raise PythonError("weird listcomp start")
    stmt, items = uncomp(op, False, False)
    if not (isinstance(stmt, StmtSingle)
        and isinstance(stmt.val, ExprCall)
        and stmt.val.expr == start.tmp
        and len(stmt.val.args.args) == 1
        and isinstance(stmt.val.args.args[0], CallArgPos)
    ):
        raise PythonError("weird old list comp")
    return [ExprListComp(Comp(stmt.val.args.args[0].expr, items)), TmpVarCleanup(start.tmp)]

@visitor
def _visit_listcomp(
    self: 'has_list_append',
    op: StmtForRaw,
    ass: MultiAssign,
):
    if len(ass.dsts) != 1:
        raise PythonError("multiassign in list comp too long")
    if not isinstance(ass.src, ExprList) or ass.src.exprs:
        raise PythonError("comp should start with an empty list")
    tmp = ass.dsts[0]
    stmt, items = uncomp(op, False, False)
    if not (isinstance(stmt, StmtListAppend)
        and stmt.tmp == tmp
    ):
        raise PythonError("weird old list comp")
    return [ExprListComp(Comp(stmt.val, items)), TmpVarCleanup(tmp)]

@visitor
def visit_listcomp_end(
    self,
    op: StmtDel,
    comp: TmpVarCleanup,
):
    if comp.tmp != op.val:
        raise PythonError("deleting a funny name")
    return []

@visitor
def visit_listcomp_item(
    self,
    op: OpcodeListAppend,
    tmp: Expr,
    val: Expr,
):
    return [StmtListAppend(tmp, val)]

@visitor
def visit_listcomp_item(
    self,
    op: OpcodeSetAdd,
    tmp: Expr,
    val: Expr,
):
    return [StmtSetAdd(tmp, val)]

@visitor
def visit_listcomp_item(
    self,
    op: OpcodeStoreSubscr,
    tmp: Expr,
    val: Expr,
    _: RotTwo,
    key: Expr,
):
    return [StmtMapAdd(tmp, key, val)]

# new comprehensions

@visitor
def visit_call_function(
    self,
    op: OpcodeCallFunction,
    fun: ExprFunctionRaw,
    arg: Iter
):
    if (fun.defargs
        or fun.defkwargs
        or fun.ann
        or op.args != 1
        or op.kwargs != 0
    ):
        raise NoMatch
    return [ExprCallComp(fun, arg.expr)]

@visitor
def _visit_fun_comp(
    self: 'has_setdict_comp',
    op: StmtForTop,
    ass: MultiAssign
):
    if len(ass.dsts) != 1:
        raise PythonError("too many dsts to be a comp")
    tmp = ass.dsts[0]
    if not isinstance(tmp, ExprFast):
        raise PythonError("funny tmp for new comp")
    stmt, items, (topdst, arg) = uncomp(op, False, True)
    if isinstance(ass.src, ExprList) and self.version.has_fun_listcomp:
        if not (isinstance(stmt, StmtListAppend)
            and stmt.tmp == tmp
            and len(ass.src.exprs) == 0
        ):
            raise PythonError("funny list comp")
        return [ExprNewListCompRaw(
            stmt.val,
            topdst,
            items,
            arg,
        )]
    elif isinstance(ass.src, ExprSet):
        if not (isinstance(stmt, StmtSetAdd)
            and stmt.tmp == tmp
            and len(ass.src.exprs) == 0
        ):
            raise PythonError("funny set comp")
        return [ExprNewSetCompRaw(
            stmt.val,
            topdst,
            items,
            arg,
        )]
    elif isinstance(ass.src, ExprDict):
        if not (isinstance(stmt, StmtMapAdd)
            and stmt.tmp == tmp
            and len(ass.src.items) == 0
        ):
            raise PythonError("funny dict comp")
        return [ExprNewDictCompRaw(
            stmt.key,
            stmt.val,
            topdst,
            items,
            arg,
        )]
    else:
        raise PythonError("weird comp")

# yield

@visitor
def _visit_yield_stmt(
    self: '!has_yield_expr',
    op: OpcodeYieldValue,
    expr: Expr
):
    return [StmtSingle(ExprYield(expr))]

@visitor
def _visit_yield_stmt(
    self: 'has_yield_expr',
    op: OpcodeYieldValue,
    expr: Expr,
):
    return [ExprYield(expr)]

@visitor
def _visit_yield_from(
    self,
    op: OpcodeYieldFrom,
    iter_: Iter,
    _: ExprNone
):
    return [ExprYieldFrom(iter_.expr)]


# with

@visitor
def _visit_with_exit(
    self: ('has_with', '!has_setup_with', '!has_exit_tmp'),
    op: OpcodeLoadAttr,
    dup: DupAttr,
    _: RotTwo,
):
    if dup.name != '__exit__' or op.param != '__enter__':
        raise PythonError("weird with start")
    return [WithEnter(None, dup.expr)]

@visitor
def _visit_with_exit(
    self: ('has_with', '!has_setup_with', 'has_exit_tmp'),
    op: OpcodeLoadAttr,
    start: TmpVarAttrStart,
):
    if start.name != '__exit__' or op.param != '__enter__':
        raise PythonError("weird with start")
    return [WithEnter(start.tmp, start.expr)]

@visitor
def _visit_with_enter(
    self,
    op: OpcodeCallFunction,
    enter: WithEnter,
):
    if op.args != 0 or op.kwargs != 0:
        raise NoMatch
    return [WithResult(enter.tmp, enter.expr)]

@visitor
def _visit_with_pop(
    self,
    op: OpcodePopTop,
    result: WithResult,
):
    return [WithStart(result.tmp, result.expr)]

@visitor
def _visit_with_pop(
    self,
    op: Store,
    result: WithResult,
):
    return [WithStartTmp(result.tmp, result.expr, op.dst)]

@visitor
def _visit_setup_finally(
    self,
    op: OpcodeSetupFinally,
    start: WithStartTmp
):
    return [WithTmp(start.tmp, start.expr, start.res, op.flow)]

@visitor
def _visit_finally(
    self,
    op: StmtDel, 
    with_: WithTmp,
    expr: Expr
):
    if not (expr == op.val == with_.res):
        raise PythonError("funny with tmp")
    return [WithInnerResult(with_.tmp, with_.expr, with_.flow)]

@visitor
def _visit_store_with(
    self,
    op: Store,
    start: WithInnerResult,
):
    return [With(start.tmp, start.expr, op.dst, start.flow), Block([])]

@visitor
def _visit_setup_finally(
    self,
    op: OpcodeSetupFinally,
    start: WithStart,
):
    return [With(start.tmp, start.expr, None, op.flow), Block([])]

@visitor
def _visit_with_pop(
    self,
    op: OpcodePopBlock,
    with_: With,
    block: Block
):
    return [WithEndPending(with_.tmp, with_.flow, StmtWith(with_.expr, with_.dst, block))]

@visitor
def _visit_finally(
    self,
    op: FwdFlow,
    end: WithEndPending,
    _: ExprNone
):
    if end.flow != op.flow:
        raise PythonError("funny with end")
    return [WithEnd(end.tmp, end.stmt)]

@visitor
def _visit_finally(
    self,
    op: StmtDel,
    end: WithEnd,
    expr: Expr,
):
    if not (expr == op.val == end.tmp):
        raise PythonError("funny with exit")
    return [WithExit(end.stmt)]

@visitor
def _visit_with_exit(
    self: '!has_exit_tmp',
    op: OpcodeWithCleanup,
    exit: WithEnd,
):
    return [WithExitDone(exit.stmt)]

@visitor
def _visit_with_exit(
    self,
    op: OpcodeWithCleanup,
    exit: WithExit
):
    return [WithExitDone(exit.stmt)]

@visitor
def _visit_with_exit(
    self,
    op: OpcodeEndFinally,
    exit: WithExitDone
):
    return [exit.stmt]


class DecoCtx:
    def __init__(self, code):
        self.version = code.version
        self.stack = [Block([])]
        self.code = code
        self.lineno = None
        if self.version.has_kwargs:
            self.varnames = code.varnames
        else:
            self.varnames = None
        if TRACE:
            print("START {} {}".format(code.name, code.firstlineno))
        ops, inflow = self.preproc(code.ops)
        for op in ops:
            if hasattr(op, 'pos'):
                rev = []
                for flow in reversed(inflow[op.pos]):
                    if flow.dst > flow.src:
                        flow = FwdFlow(flow)
                        self.process(flow)
                    else:
                        rev.append(flow)
                if rev:
                    self.process(RevFlow(rev))
            self.process(op)
        if len(self.stack) != 1:
            raise PythonError("stack non-empty at the end: {}".format(
                ', '.join(type(x).__name__ for x in self.stack)
            ))
        if not isinstance(self.stack[0], Block):
            raise PythonError("weirdness on stack at the end")
        self.res = DecoCode(self.stack[0], code, self.varnames or [])

    def preproc(self, ops):
        # first pass: undo jump over true const
        if self.version.has_jump_true_const:
            newops = []
            fakejumps = {}
            for idx, op in enumerate(ops):
                op = ops[idx]
                more = len(ops) - idx - 1
                if (more >= 2
                    and isinstance(op, OpcodeJumpForward)
                    and isinstance(ops[idx+1], OpcodeJumpIfFalse)
                    and isinstance(ops[idx+2], OpcodePopTop)
                    and op.flow.dst == ops[idx+2].nextpos
                ):
                    fakejumps[op.flow.dst] = op.pos
                    newops.append(OpcodeLoadConst(op.pos, op.nextpos, ExprAnyTrue(), None))
                elif isinstance(op, (OpcodeJumpAbsolute, OpcodeContinueLoop)) and op.flow.dst in fakejumps:
                    newops.append(type(op)(op.pos, op.nextpos, Flow(op.flow.src, fakejumps[op.flow.dst])))
                else:
                    newops.append(op)
            ops = newops
        # alt first pass: undo conditional jump folding for jumps with opposite polarisation
        if self.version.has_jump_cond_fold:
            after_jif = {}
            after_jit = {}
            for op in ops:
                if isinstance(op, (OpcodeJumpIfFalse, OpcodeJumpIfFalseOrPop, OpcodePopJumpIfFalse)):
                    after_jif[op.nextpos] = op.pos
                elif isinstance(op, (OpcodeJumpIfTrue, OpcodeJumpIfTrueOrPop, OpcodePopJumpIfTrue)):
                    after_jit[op.nextpos] = op.pos
            newops = []
            for op in ops:
                if isinstance(op, OpcodeJumpIfFalse) and op.flow.dst in after_jit:
                    newops.append(OpcodeJumpIfFalse(op.pos, op.nextpos, Flow(op.pos, after_jit[op.flow.dst])))
                elif isinstance(op, OpcodePopJumpIfFalse) and op.flow.dst in after_jit:
                    newops.append(OpcodeJumpIfFalseOrPop(op.pos, op.nextpos, Flow(op.pos, after_jit[op.flow.dst])))
                elif isinstance(op, OpcodeJumpIfTrue) and op.flow.dst in after_jif:
                    newops.append(OpcodeJumpIfTrue(op.pos, op.nextpos, Flow(op.pos, after_jif[op.flow.dst])))
                elif isinstance(op, OpcodePopJumpIfTrue) and op.flow.dst in after_jif:
                    newops.append(OpcodeJumpIfTrueOrPop(op.pos, op.nextpos, Flow(op.pos, after_jif[op.flow.dst])))
                else:
                    newops.append(op)
            ops = newops
        # second pass: figure out the kinds of absolute jumps
        condflow = {op.nextpos: [] for op in ops}
        for op in ops:
            if isinstance(op, (OpcodePopJumpIfTrue, OpcodePopJumpIfFalse, OpcodeJumpIfTrueOrPop, OpcodeJumpIfFalseOrPop, OpcodeJumpIfTrue, OpcodeJumpIfFalse, OpcodeForLoop, OpcodeForIter, OpcodeSetupExcept)):
                condflow[op.flow.dst].append(op.flow)
        inflow = process_flow(ops)
        newops = []
        for idx, op in enumerate(ops):
            next_unreachable = not condflow[op.nextpos]
            next_end_finally = idx+1 < len(ops) and isinstance(ops[idx+1], OpcodeEndFinally)
            next_pop_top = idx+1 < len(ops) and isinstance(ops[idx+1], OpcodePopTop)
            if isinstance(op, OpcodeJumpAbsolute):
                insert_end = False
                is_final = op.flow == max(inflow[op.flow.dst])
                is_backwards = op.flow.dst <= op.pos
                if not is_backwards:
                    if next_unreachable and not next_end_finally:
                        op = JumpSkipJunk(op.pos, op.nextpos, [op.flow])
                    else:
                        op = JumpUnconditional(op.pos, op.nextpos, [op.flow])
                elif is_final:
                    op = JumpContinue(op.pos, op.nextpos, [op.flow])
                    insert_end = True
                elif next_unreachable and not next_end_finally:
                    if next_pop_top:
                        op = JumpSkipJunk(op.pos, op.nextpos, [op.flow])
                    else:
                        op = JumpContinue(op.pos, op.nextpos, [op.flow])
                else:
                    op = JumpContinue(op.pos, op.nextpos, [op.flow])
                newops.append(op)
            elif isinstance(op, OpcodeJumpForward):
                if next_unreachable and not next_end_finally:
                    op = JumpSkipJunk(op.pos, op.nextpos, [op.flow])
                else:
                    op = JumpUnconditional(op.pos, op.nextpos, [op.flow])
                newops.append(op)
            else:
                newops.append(op)
        ops = newops
        return ops, inflow

    def process(self, op):
        for t in type(op).mro():
            for visitor in _VISITORS.get(t, []):
                try:
                    res = visitor.visit(op, self)
                except NoMatch:
                    pass
                else:
                    for item in res:
                        if item is None:
                            pass
                        elif isinstance(item, Regurgitable):
                            self.process(item)
                        else:
                            self.stack.append(item)
                    return
        if TRACE:
            for x in self.stack:
                print(x)
            print(op)
        raise PythonError("no visitors matched: {}, [{}]".format(
            type(op).__name__,
            ', '.join(type(x).__name__ for x in self.stack)
        ))

    def fast(self, idx):
        if self.varnames is None:
            raise PythonError("no fast variables")
        if idx not in range(len(self.varnames)):
            raise PythonError("fast var out of range")
        return ExprFast(idx, self.varnames[idx])

    def deref(self, idx):
        if idx in range(len(self.code.cellvars)):
            return ExprDeref(idx, self.code.cellvars[idx])
        fidx = idx - len(self.code.cellvars)
        if fidx in range(len(self.code.freevars)):
            return ExprDeref(idx, self.code.freevars[fidx])
        raise PythonError("deref var out of range")

    def string(self, expr):
        if self.version.py3k:
            if not isinstance(expr, ExprUnicode):
                raise PythonError("wanted a string, got {}".format(expr))
            return expr.val
        else:
            if not isinstance(expr, ExprString):
                raise PythonError("wanted a string")
            return expr.val.decode('ascii')

    def make_ann(self, ann):
        if not ann:
            return {}
        *vals, keys = ann
        if not isinstance(keys, ExprTuple):
            raise PythonError("no ann tuple")
        if len(vals) != len(keys.exprs):
            raise PythonError("ann len mismatch")
        return {self.string(k): v for k, v in zip(keys.exprs, vals)}


def deco_code(code):
    return DecoCtx(code).res
