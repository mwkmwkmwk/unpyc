from collections import namedtuple
from enum import Enum

from .helpers import PythonError
from .stmt import *
from .expr import *
from .code import Code
from .bytecode import *
from .ast import uncomp

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
#   - annotations
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

AndStart = namedtuple('AndStart', ['expr', 'flow'])
OrStart = namedtuple('OrStart', ['expr', 'flow'])
IfExprTrue = namedtuple('IfExprTrue', ['expr', 'flow'])
IfExprElse = namedtuple('IfExprElse', ['cond', 'true', 'flow'])

CompareStart = namedtuple('CompareStart', ['items', 'flows'])
Compare = namedtuple('Compare', ['items', 'flows'])
CompareLast = namedtuple('CompareLast', ['items', 'flows'])
CompareNext = namedtuple('CompareNext', ['items', 'flows'])

WantPop = namedtuple('WantPop', [])
WantRotPop = namedtuple('WantRotPop', [])
WantFlow = namedtuple('WantFlow', ['any', 'true', 'false'])

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

# a special marker to put in stack want lists - will match getattr(opcode, attr)
# expressions and pass a list
Exprs = namedtuple('Exprs', ['attr', 'factor'])
UglyClosures = object()
Closures = object()
MaybeWantFlow = object()
LoopDammit = object()

# regurgitables

class Regurgitable: __slots__ = ()

class Store(Regurgitable, namedtuple('Store', ['dst'])): pass
class Inplace(Regurgitable, namedtuple('Inplace', ['stmt'])): pass

# fake opcodes

class JumpIfTrue(OpcodeFlow): pass
class JumpIfFalse(OpcodeFlow): pass
class JumpUnconditional(OpcodeFlow): pass
class JumpContinue(OpcodeFlow): pass
class JumpSkipJunk(OpcodeFlow): pass


class FwdFlow(Regurgitable, namedtuple('FwdFlow', ['flow'])): pass
class RevFlow(Regurgitable, namedtuple('RevFlow', ['flow'])): pass

# for checks

Regurgitable = (Regurgitable, Stmt, Opcode)

# visitors

class NoMatch(Exception):
    pass

_VISITORS = {}

class _Visitor:
    __slots__ = 'func', 'wanted', 'flag'

    def __init__(self, func, wanted, flag=None):
        self.func = func
        self.wanted = wanted
        self.flag = flag

    def visit(self, opcode, deco):
        if not deco.version.match(self.flag):
            raise NoMatch
        total = 0
        closure_num = None
        for want in self.wanted:
            if isinstance(want, Exprs):
                total += getattr(opcode, want.attr) * want.factor
            elif want is Closures:
                total += opcode.param
            elif want is UglyClosures:
                # fuck you.
                if not deco.stack:
                    raise NoMatch
                code = deco.stack[-1]
                if not isinstance(code, Code):
                    raise NoMatch
                closure_num = len(code.freevars)
                total += closure_num
            elif want is MaybeWantFlow:
                if deco.stack and isinstance(deco.stack[-1], WantFlow):
                    total += 1
            elif want is LoopDammit:
                looppos = len(self.wanted) - self.wanted.index(Loop) - 2
                for idx in reversed(range(len(deco.stack))):
                    if isinstance(deco.stack[idx], Loop):
                        looplen = len(deco.stack) - idx - 1 - looppos
                        total += looplen
                        break
                else:
                    raise NoMatch
            else:
                total += 1
        if len(deco.stack) < total:
            raise NoMatch
        if total:
            stack = deco.stack[-total:]
        else:
            stack = []
        args = []
        for want in reversed(self.wanted):
            if isinstance(want, Exprs):
                num = getattr(opcode, want.attr)
                arg = []
                for _ in range(num):
                    exprs = []
                    for _ in range(want.factor):
                        expr = stack.pop()
                        if not isinstance(expr, Expr):
                            raise NoMatch
                        exprs.append(expr)
                    exprs.reverse()
                    arg.append(expr if want.factor == 1 else exprs)
                arg.reverse()
            elif want is Closures:
                arg = []
                for _ in range(opcode.param):
                    expr = stack.pop()
                    if not isinstance(expr, Closure):
                        raise NoMatch
                    arg.append(expr)
                arg.reverse()
            elif want is UglyClosures:
                arg = []
                for _ in range(closure_num):
                    closure = stack.pop()
                    if not isinstance(closure, Closure):
                        raise NoMatch
                    arg.append(closure.var)
                arg.reverse()
            elif want is MaybeWantFlow:
                if deco.stack and isinstance(deco.stack[-1], WantFlow):
                    arg = stack.pop()
                    if not isinstance(arg, WantFlow):
                        raise NoMatch
                else:
                    arg = WantFlow([], [], [])
            elif want is LoopDammit:
                if looplen:
                    arg = stack[-looplen:]
                    del stack[-looplen:]
                else:
                    arg = []
            else:
                arg = stack.pop()
                if not isinstance(arg, want):
                    raise NoMatch
            args.append(arg)
        args.reverse()
        newstack = self.func(opcode, deco, *args)
        if TRACE:
            print("\tVISIT {} [{} -> {}] {}".format(
                ', '.join(type(x).__name__ for x in (deco.stack[:-total] if total else deco.stack)),
                ', '.join(type(x).__name__ for x in (deco.stack[-total:] if total else [])),
                ', '.join(type(x).__name__ for x in newstack),
                type(opcode).__name__
            ))
        if total:
            deco.stack[-total:] = []
        return newstack

def _visitor(op, *stack, **kwargs):
    def inner(func):
        _VISITORS.setdefault(op, []).append(_Visitor(func, stack, **kwargs))
        return func
    return inner


def _lsd_visitor(op_load, op_store, op_delete, *stack):
    def inner(func):

        @_visitor(op_load, *stack)
        def visit_lsd_load(self, deco, *args):
            dst = func(self, deco, *args)
            return [dst]

        @_visitor(op_store, *stack)
        def visit_lsd_store(self, deco, *args):
            dst = func(self, deco, *args)
            return [Store(dst)]

        @_visitor(op_delete, *stack)
        def visit_lsd_delete(self, deco, *args):
            dst = func(self, deco, *args)
            return [StmtDel(dst)]

        return func
    return inner

# visitors

# line numbers

@_visitor(OpcodeSetLineno)
def visit_set_lineno(self, deco):
    deco.lineno = self.param
    return []

@_visitor(OpcodeNop)
def _visit_nop(self, deco):
    return []

# stack ops

@_visitor(OpcodeDupTop)
def visit_dup_top(self, deco):
    return [DupTop()]

@_visitor(OpcodeDupTwo)
def visit_dup_top(self, deco):
    return [DupTwo()]

@_visitor(OpcodeDupTopX)
def visit_dup_topx(self, deco):
    if self.param == 2:
        return [DupTwo()]
    elif self.param == 3:
        return [DupThree()]
    else:
        raise PythonError("funny DUP_TOPX parameter")

@_visitor(OpcodeRotTwo)
def _visit_rot_two(self, deco):
    return [RotTwo()]

@_visitor(OpcodeRotThree)
def visit_rot_three(self, deco):
    return [RotThree()]

@_visitor(OpcodeRotFour)
def _visit_rot_four(self, deco):
    return [RotFour()]

@_visitor(OpcodePopTop, WantPop)
def _visit_want_pop(self, deco, want):
    return []

@_visitor(OpcodePopTop, WantRotPop, RotTwo)
def _visit_want_rot_two(self, deco, want, _):
    return []


# expressions - unary

def _register_unary(otype, etype):
    @_visitor(otype, Expr)
    def visit_unary(self, deco, expr):
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
    @_visitor(otype, Expr, Expr)
    def visit_binary(self, deco, expr1, expr2):
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

@_visitor(OpcodeBuildTuple, Exprs('param', 1))
def visit_build_tuple(self, deco, exprs):
    return [ExprTuple(exprs)]

@_visitor(OpcodeBuildList, Exprs('param', 1))
def visit_build_list(self, deco, exprs):
    return [ExprList(exprs)]

@_visitor(OpcodeBuildSet, Exprs('param', 1))
def visit_build_set(self, deco, exprs):
    return [ExprSet(exprs)]

# x in const set special

@_visitor(OpcodeCompareOp, Frozenset)
def visit_frozenset(self, deco, fset):
    if self.param not in [CmpOp.IN, CmpOp.NOT_IN]:
        raise PythonError("funny place for frozenset")
    if not fset.exprs:
        raise PythonError("can't make empty set display out of frozenset")
    return [ExprSet(fset.exprs), self]

@_visitor(OpcodeBuildMap)
def visit_build_map(self, deco):
    if self.param and not deco.version.has_store_map:
        raise PythonError("Non-zero param for BUILD_MAP")
    return [ExprDict([])]

@_visitor(OpcodeStoreSubscr, ExprDict, DupTop, Expr, RotTwo, Expr, flag='has_reversed_kv')
def visit_build_map_step(self, deco, dict_, _1, val, _2, key):
    dict_.items.append((key, val))
    return [dict_]

@_visitor(OpcodeStoreSubscr, ExprDict, DupTop, Expr, Expr, RotThree, flag=('!has_reversed_kv', '!has_store_map'))
def visit_build_map_step(self, deco, dict_, _1, key, val, _2):
    dict_.items.append((key, val))
    return [dict_]

@_visitor(OpcodeStoreMap, ExprDict, Expr, Expr)
def visit_build_map_step(self, deco, dict_, val, key):
    dict_.items.append((key, val))
    return [dict_]

# expressions - function call

@_visitor(OpcodeBinaryCall, Expr, ExprTuple)
def visit_binary_call(self, deco, expr, params):
    return [ExprCall(expr, CallArgs([('', arg) for arg in params.exprs]))]

@_visitor(OpcodeCallFunction, Expr, Exprs('args', 1), Exprs('kwargs', 2))
def visit_call_function(self, deco, fun, args, kwargs):
    return [ExprCall(fun, CallArgs([('', arg) for arg in args] + [(deco.string(name), arg) for name, arg in kwargs]))]

@_visitor(OpcodeCallFunctionVar, Expr, Exprs('args', 1), Exprs('kwargs', 2), Expr)
def visit_call_function(self, deco, fun, args, kwargs, vararg):
    return [ExprCall(fun, CallArgs([('', arg) for arg in args] + [(deco.string(name), arg) for name, arg in kwargs] + [('*', vararg)]))]

@_visitor(OpcodeCallFunctionKw, Expr, Exprs('args', 1), Exprs('kwargs', 2), Expr)
def visit_call_function(self, deco, fun, args, kwargs, varkw):
    return [ExprCall(fun, CallArgs([('', arg) for arg in args] + [(deco.string(name), arg) for name, arg in kwargs] + [('**', varkw)]))]

@_visitor(OpcodeCallFunctionVarKw, Expr, Exprs('args', 1), Exprs('kwargs', 2), Expr, Expr)
def visit_call_function(self, deco, fun, args, kwargs, vararg, varkw):
    return [ExprCall(fun, CallArgs([('', arg) for arg in args] + [(deco.string(name), arg) for name, arg in kwargs] + [('*', vararg), ('**', varkw)]))]

# expressions - load const

@_visitor(OpcodeLoadConst)
def visit_load_const(self, deco):
    return [self.const]

# expressions - storable

@_lsd_visitor(OpcodeLoadName, OpcodeStoreName, OpcodeDeleteName)
def visit_store_name(self, deco):
    return ExprName(self.param)

@_lsd_visitor(OpcodeLoadGlobal, OpcodeStoreGlobal, OpcodeDeleteGlobal)
def visit_store_global(self, deco):
    return ExprGlobal(self.param)

@_lsd_visitor(OpcodeLoadFast, OpcodeStoreFast, OpcodeDeleteFast)
def visit_store_fast(self, deco):
    return deco.fast(self.param)

@_lsd_visitor(OpcodeLoadDeref, OpcodeStoreDeref, None)
def visit_store_deref(self, deco):
    return deco.deref(self.param)

@_lsd_visitor(OpcodeLoadAttr, OpcodeStoreAttr, OpcodeDeleteAttr, Expr)
def visit_store_attr(self, deco, expr):
    return ExprAttr(expr, self.param)

@_lsd_visitor(OpcodeBinarySubscr, OpcodeStoreSubscr, OpcodeDeleteSubscr, Expr, Expr)
def visit_store_subscr(self, deco, expr, idx):
    return ExprSubscr(expr, idx)

@_lsd_visitor(OpcodeSliceNN, OpcodeStoreSliceNN, OpcodeDeleteSliceNN, Expr)
def visit_store_slice_nn(self, deco, expr):
    return ExprSubscr(expr, ExprSlice(None, None))

@_lsd_visitor(OpcodeSliceEN, OpcodeStoreSliceEN, OpcodeDeleteSliceEN, Expr, Expr)
def visit_store_slice_en(self, deco, expr, start):
    return ExprSubscr(expr, ExprSlice(start, None))

@_lsd_visitor(OpcodeSliceNE, OpcodeStoreSliceNE, OpcodeDeleteSliceNE, Expr, Expr)
def visit_store_slice_ne(self, deco, expr, end):
    return ExprSubscr(expr, ExprSlice(None, end))

@_lsd_visitor(OpcodeSliceEE, OpcodeStoreSliceEE, OpcodeDeleteSliceEE, Expr, Expr, Expr)
def visit_store_slice_ee(self, deco, expr, start, end):
    return ExprSubscr(expr, ExprSlice(start, end))

@_visitor(OpcodeBuildSlice, Exprs('param', 1))
def visit_build_slice(self, deco, exprs):
    if self.param in (2, 3):
        return [ExprSlice(*[None if isinstance(expr, ExprNone) else expr for expr in exprs])]
    else:
        raise PythonError("funny slice length")

# list & tuple unpacking

@_visitor(OpcodeUnpackTuple)
@_visitor(OpcodeUnpackSequence)
def visit_unpack_sequence(self, deco):
    res = ExprTuple([None for _ in range(self.param)])
    return [Store(res)] + [UnpackSlot(res, idx) for idx in reversed(range(self.param))]

@_visitor(OpcodeUnpackList)
def visit_unpack_list(self, deco):
    res = ExprList([None for _ in range(self.param)])
    return [Store(res)] + [UnpackSlot(res, idx) for idx in reversed(range(self.param))]

@_visitor(Store, UnpackSlot)
def visit_store_unpack(self, deco, slot):
    slot.expr.exprs[slot.idx] = self.dst
    return []

# optimized unpacking

@_visitor(JumpSkipJunk, Expr, Expr, RotTwo, flag=('has_unpack_opt', 'has_nop'))
def visit_unpack_opt_two_skip(self, deco, a, b, _):
    src = ExprTuple([a, b])
    dst = ExprTuple([None, None])
    return [StmtAssign([dst], src), UnpackSlot(dst, 1), UnpackSlot(dst, 0), WantFlow(self.flow, [], [])]

@_visitor(JumpSkipJunk, Expr, Expr, Expr, RotThree, RotTwo, flag=('has_unpack_opt', 'has_nop'))
def visit_unpack_opt_three_skip(self, deco, a, b, c, _1, _2):
    src = ExprTuple([a, b, c])
    dst = ExprTuple([None, None, None])
    return [StmtAssign([dst], src), UnpackSlot(dst, 2), UnpackSlot(dst, 1), UnpackSlot(dst, 0), WantFlow(self.flow, [], [])]

@_visitor(Store, Expr, Expr, RotTwo, flag=('has_unpack_opt', '!has_nop'))
def visit_unpack_opt_two_skip(self, deco, a, b, _):
    src = ExprTuple([a, b])
    dst = ExprTuple([self.dst, None])
    return [StmtAssign([dst], src), UnpackSlot(dst, 1)]

@_visitor(Store, Expr, Expr, Expr, RotThree, RotTwo, flag=('has_unpack_opt', '!has_nop'))
def visit_unpack_opt_three_skip(self, deco, a, b, c, _1, _2):
    src = ExprTuple([a, b, c])
    dst = ExprTuple([self.dst, None, None])
    return [StmtAssign([dst], src), UnpackSlot(dst, 2), UnpackSlot(dst, 1)]

# old argument unpacking

@_visitor(OpcodeUnpackArg)
def visit_unpack_arg(self, deco):
    res = FunArgs([None for _ in range(self.param)], [], None, [], {}, None)
    return [StmtArgs(res)] + [UnpackArgSlot(res, idx) for idx in reversed(range(self.param))]

@_visitor(OpcodeUnpackVararg)
def visit_unpack_arg(self, deco):
    res = FunArgs([None for _ in range(self.param)], [], None, [], {}, None)
    return [StmtArgs(res), UnpackVarargSlot(res)] + [UnpackArgSlot(res, idx) for idx in reversed(range(self.param))]

@_visitor(Store, UnpackArgSlot)
def visit_store_unpack_arg(self, deco, slot):
    slot.args.args[slot.idx] = self.dst
    return []

@_visitor(Store, UnpackVarargSlot)
def visit_store_unpack_vararg(self, deco, slot):
    slot.args.vararg = self.dst
    return []

# extended unpacking

@_visitor(OpcodeUnpackEx)
def visit_unpack_sequence(self, deco):
    res = ExprUnpackEx(
        [None for _ in range(self.before)],
        None,
        [None for _ in range(self.after)],
    )
    return [
        Store(res)
    ] + [
        UnpackAfterSlot(res, idx) for idx in reversed(range(self.after))
    ] + [
        UnpackStarSlot(res)
    ] + [
        UnpackBeforeSlot(res, idx) for idx in reversed(range(self.before))
    ]

@_visitor(Store, UnpackBeforeSlot)
def visit_store_unpack_before(self, deco, slot):
    slot.expr.before[slot.idx] = self.dst
    return []

@_visitor(Store, UnpackStarSlot)
def visit_store_unpack_star(self, deco, slot):
    slot.expr.star = self.dst
    return []

@_visitor(Store, UnpackAfterSlot)
def visit_store_unpack_after(self, deco, slot):
    slot.expr.after[slot.idx] = self.dst
    return []

# statements

@_visitor(Stmt, Block)
def _visit_stmt(self, deco, block):
    block.stmts.append(self)
    return [block]

# single expression statement

@_visitor(OpcodePrintExpr, Expr)
def _visit_print_expr(self, deco, expr):
    return [StmtPrintExpr(expr)]

@_visitor(OpcodePopTop, Block, Expr, flag='!always_print_expr')
def _visit_single_expr(self, deco, block, expr):
    return [block, StmtSingle(expr)]

# assignment

@_visitor(Store, Expr)
def visit_store_assign(self, deco, src):
    return [StmtAssign([self.dst], src)]

@_visitor(Store, Expr, DupTop)
def visit_store_multi_start(self, deco, src, _):
    return [MultiAssign(src, [self.dst])]

@_visitor(Store, MultiAssign, DupTop)
def visit_store_multi_next(self, deco, multi, _):
    multi.dsts.append(self.dst)
    return [multi]

@_visitor(Store, MultiAssign)
def visit_store_multi_end(self, deco, multi):
    multi.dsts.append(self.dst)
    return [StmtAssign(multi.dsts, multi.src)]

# print statement

@_visitor(OpcodePrintItem, Expr)
def visit_print_item(self, deco, expr):
    return [StmtPrint([expr], False)]

@_visitor(OpcodePrintNewline)
def visit_print_newline(self, deco):
    return [StmtPrint([], True)]

# print to

@_visitor(OpcodePrintItemTo, Expr, DupTop, Expr, RotTwo)
def visit_print_item_to(self, deco, to, _dup, expr, _rot):
    return [PrintTo(to, [expr])]

@_visitor(OpcodePrintItemTo, PrintTo, DupTop, Expr, RotTwo)
def visit_print_item_to(self, deco, print, _dup, expr, _rot):
    print.vals.append(expr)
    return [print]

@_visitor(OpcodePopTop, PrintTo)
def visit_print_to_end(self, deco, print):
    return [StmtPrintTo(print.expr, print.vals, False)]

@_visitor(OpcodePrintNewlineTo, PrintTo)
def visit_print_newline_to(self, deco, print):
    return [StmtPrintTo(print.expr, print.vals, True)]

@_visitor(OpcodePrintNewlineTo, Expr)
def visit_print_newline_to(self, deco, expr):
    return [StmtPrintTo(expr, [], True)]

# return statement

@_visitor(OpcodeReturnValue, Expr)
def _visit_return(self, deco, expr):
    return [StmtReturn(expr)]

# assert. ouch. has to be before raise.

@_visitor(OpcodeRaiseVarargs, AndStart, Block, OrStart, Block, Exprs('param', 1), flag=('has_assert', '!has_short_assert'))
def _visit_assert_1(self, deco, ifstart, block, orstart, block2, exprs):
    if block.stmts or block2.stmts:
        raise PythonError("extra assert statements")
    if not isinstance(exprs[0], ExprGlobal) or exprs[0].name != 'AssertionError':
        raise PythonError("hmm, I wanted an assert...")
    if not isinstance(ifstart.expr, ExprGlobal) or ifstart.expr.name != '__debug__':
        raise PythonError("hmm, I wanted an assert...")
    if self.param == 1:
        return [StmtAssert(orstart.expr), WantPop(), WantFlow([], orstart.flow, ifstart.flow)]
    elif self.param == 2:
        return [StmtAssert(orstart.expr, exprs[1]), WantPop(), WantFlow([], orstart.flow, ifstart.flow)]
    else:
        raise PythonError("funny assert params")

@_visitor(FwdFlow, OrStart, Block, flag=('has_short_assert', '!has_raise_from'))
def _visit_assert_2(self, deco, start, body):
    if (len(body.stmts) != 1
        or not isinstance(body.stmts[0], StmtRaise)
        or not isinstance(body.stmts[0].cls, ExprGlobal)
        or body.stmts[0].cls.name != 'AssertionError'
        or body.stmts[0].tb is not None
    ):
        raise NoMatch
    return [AssertJunk(start.expr, body.stmts[0].val), WantFlow([], start.flow, []), self]

@_visitor(FwdFlow, OrStart, Block, flag=('has_short_assert', 'has_raise_from'))
def _visit_assert_2(self, deco, start, body):
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
        return [AssertJunk(start.expr, val.args.args[0][1]), WantFlow([], start.flow, []), self]
    else:
        raise PythonError("that's still not an assert")

@_visitor(OpcodePopTop, AssertJunk)
def _visit_assert_junk(self, deco, junk):
    return [StmtAssert(*junk)]

@_visitor(FwdFlow, OrStart, Block, AssertJunk, flag='has_jump_cond_fold')
def _visit_assert_or(self, deco, start, block, junk):
    if block.stmts:
        raise NoMatch
    return [AssertJunk(ExprBoolOr(start.expr, junk.expr), junk.msg), WantFlow([], start.flow, []), self]

# raise statement

# Python 1.0 - 1.2
@_visitor(OpcodeRaiseException, Expr, ExprNone)
def _visit_raise_1(self, deco, cls, _):
    return [StmtRaise(cls)]

@_visitor(OpcodeRaiseException, Expr, Expr)
def _visit_raise_2(self, deco, cls, val):
    return [StmtRaise(cls, val)]

# Python 1.3-2.7
@_visitor(OpcodeRaiseVarargs, Exprs('param', 1), flag='!has_raise_from')
def _visit_raise_varargs(self, deco, exprs):
    if len(exprs) > 3:
        raise PythonError("too many args to raise")
    if len(exprs) == 0 and not deco.version.has_reraise:
        raise PythonError("too few args to raise")
    return [StmtRaise(*exprs)]

# Python 3
@_visitor(OpcodeRaiseVarargs, Exprs('param', 1), flag='has_raise_from')
def _visit_raise_from(self, deco, exprs):
    if len(exprs) < 2:
        return [StmtRaise(*exprs)]
    elif len(exprs) == 2:
        return [StmtRaise(exprs[0], None, exprs[1])]
    else:
        raise PythonError("too many args to raise")

# exec statement

@_visitor(OpcodeExecStmt, Expr, Expr, DupTop)
def _visit_exec_3(self, deco, code, env, _):
    if isinstance(env, ExprNone):
        return [StmtExec(code)]
    else:
        return [StmtExec(code, env)]

@_visitor(OpcodeExecStmt, Expr, Expr, Expr)
def _visit_exec_3(self, deco, code, globals, locals):
    return [StmtExec(code, globals, locals)]

# imports

@_visitor(OpcodeImportName, flag='!has_import_as')
def _visit_import_name(self, deco):
    return [Import(self.param, [])]

@_visitor(Store, Import)
def _visit_store_name_import(self, deco, import_, *args):
    if import_.items:
        raise PythonError("non-empty items for plain import")
    return [StmtImport(-1, import_.name, [], self.dst)]

@_visitor(OpcodeImportFrom, Import)
def _visit_import_from_star(self, deco, import_, flag="!has_import_star"):
    if self.param != '*':
        raise NoMatch
    if import_.items:
        raise PythonError("non-empty items for star import")
    return [StmtImportStar(-1, import_.name), WantPop()]

@_visitor(OpcodeImportFrom, Import)
def _visit_import_from(self, deco, import_):
    if self.param == '*':
        raise NoMatch
    import_.items.append(self.param)
    return [import_]

@_visitor(OpcodePopTop, Import)
def _visit_import_from_end(self, deco, import_):
    return [StmtFromImport(-1, import_.name, [(x, None) for x in import_.items])]

# imports - v2

@_visitor(OpcodeImportName, ExprNone, flag=('has_import_as', '!has_relative_import'))
def _visit_import_name(self, deco, expr):
    return [Import2Simple(-1, self.param, [])]

@_visitor(OpcodeImportName, ExprInt, ExprNone, flag='has_relative_import')
def _visit_import_name(self, deco, level, expr):
    return [Import2Simple(level.val, self.param, [])]

@_visitor(OpcodeLoadAttr, Import2Simple)
def _visit_import_name_attr(self, deco, import_):
    import_.attrs.append(self.param)
    return [import_]

@_visitor(Store, Import2Simple)
def _visit_store_name_import(self, deco, import_):
    return [StmtImport(import_.level, import_.name, import_.attrs, self.dst)]

@_visitor(OpcodeImportName, ExprTuple, flag=('has_import_as', '!has_relative_import'))
def _visit_import_name(self, deco, expr):
    fromlist = [deco.string(item) for item in expr.exprs]
    if fromlist == ['*']:
        return [Import2Star(-1, self.param)]
    else:
        return [Import2From(-1, fromlist, self.param, [])]

@_visitor(OpcodeImportName, ExprInt, ExprTuple, flag='has_relative_import')
def _visit_import_name(self, deco, level, expr):
    fromlist = [deco.string(item) for item in expr.exprs]
    if fromlist == ['*']:
        return [Import2Star(level.val, self.param)]
    else:
        return [Import2From(level.val, fromlist, self.param, [])]

@_visitor(OpcodeImportStar, Import2Star)
def _visit_import_star(self, deco, import_):
    return [StmtImportStar(import_.level, import_.name)]

@_visitor(OpcodeImportFrom, Import2From)
def _visit_import_from(self, deco, import_):
    idx = len(import_.exprs)
    import_.exprs.append(None)
    if (idx >= len(import_.fromlist) or import_.fromlist[idx] != self.param):
        raise PythonError("fromlist mismatch")
    return [import_, UnpackSlot(import_, idx)]

@_visitor(OpcodePopTop, Import2From)
def _visit_import_from_end(self, deco, import_):
    return [StmtFromImport(import_.level, import_.name, list(zip(import_.fromlist, import_.exprs)))]

# misc flow

@_visitor(FwdFlow, WantFlow)
def _visit_flow(self, deco, want):
    if self.flow in want.any:
        want.any.remove(self.flow)
    elif self.flow in want.true:
        want.true.remove(self.flow)
    elif self.flow in want.false:
        want.false.remove(self.flow)
    else:
        raise NoMatch
    if not want.any and not want.true and not want.false:
        return []
    else:
        return [want]

@_visitor(JumpContinue, WantFlow)
def _visit_extra(self, deco, extra):
    for x in extra.any[:]:
        if x.dst <= x.src:
            self.flow.append(x)
            extra.any.remove(x)
    if not any(extra):
        return [self]
    return [self, extra]

@_visitor(JumpContinue, PopExcept)
def _visit_extra(self, deco, pop):
    return [self, pop]

@_visitor(JumpIfTrue, WantFlow)
def _visit_extra(self, deco, extra):
    if extra.false or extra.any:
        raise NoMatch
    return [JumpIfTrue(self.pos, self.nextpos, self.flow + extra.true)]

@_visitor(JumpIfFalse, WantFlow)
def _visit_extra(self, deco, extra):
    if extra.true or extra.any:
        raise NoMatch
    return [JumpIfFalse(self.pos, self.nextpos, self.flow + extra.false)]

@_visitor(JumpSkipJunk, WantFlow)
def _visit_extra(self, deco, extra):
    if extra.true or extra.false:
        raise NoMatch
    return [JumpSkipJunk(self.pos, self.nextpos, self.flow + extra.any)]

@_visitor(JumpUnconditional, WantFlow)
def _visit_extra(self, deco, extra):
    if extra.true or extra.false:
        raise NoMatch
    return [JumpUnconditional(self.pos, self.nextpos, self.flow + extra.any)]

@_visitor(JumpUnconditional, FinalElse, Block)
def _visit_if_end(self, deco, final, inner):
    return [final.maker(inner), JumpUnconditional(self.pos, self.nextpos, self.flow + final.flow)]

@_visitor(FwdFlow, FinalElse, Block, MaybeWantFlow)
@_visitor(OpcodeEndFinally, FinalElse, Block, MaybeWantFlow)
def _visit_if_end(self, deco, final, inner, want):
    return [final.maker(inner), WantFlow(final.flow + want.any, want.true, want.false), self]

# if / and / or

@_visitor(JumpSkipJunk, Block)
def _visit_if(self, deco, block):
    return [block, FinalElse(self.flow, FinalJunk()), Block([]), WantPop()]

@_visitor(JumpIfFalse, Expr)
def _visit_if(self, deco, expr):
    return [AndStart(expr, self.flow), Block([]), WantPop()]

@_visitor(JumpIfTrue, Expr)
def _visit_if(self, deco, expr):
    return [OrStart(expr, self.flow), Block([]), WantPop()]

@_visitor(JumpUnconditional, Block, AndStart, Block)
def _visit_if_else(self, deco, block, if_, body):
    return [block, FinalElse(self.flow, FinalIf(if_.expr, body)), Block([]), WantPop(), WantFlow([], [], if_.flow)]

@_visitor(JumpUnconditional, Block, OrStart, Block, flag='has_if_not_opt')
def _visit_if_else(self, deco, block, if_, body):
    return [block, FinalElse(self.flow, FinalIf(ExprNot(if_.expr), body)), Block([]), WantPop(), WantFlow([], if_.flow, [])]

@_visitor(FwdFlow, AndStart, Block, Expr, MaybeWantFlow)
def _visit_and(self, deco, start, block, expr, want):
    if block.stmts:
        raise PythonError("extra and statements")
    want.false.extend(start.flow)
    return [ExprBoolAnd(start.expr, expr), want, self]

@_visitor(FwdFlow, OrStart, Block, Expr, MaybeWantFlow)
def _visit_and(self, deco, start, block, expr, want):
    if block.stmts:
        raise PythonError("extra or statements")
    want.true.extend(start.flow)
    return [ExprBoolOr(start.expr, expr), want, self]

@_visitor(FwdFlow, AndStart, Block, FinalElse, Block, WantPop, flag='has_jump_cond_fold')
def _visit_folded_if(self, deco, start, blocka, final, blockb, _):
    if blocka.stmts:
        raise PythonError("extra and-if statements")
    if_ = final.maker
    if not isinstance(if_, FinalIf):
        raise NoMatch
    return [FinalElse(final.flow, FinalIf(ExprBoolAnd(start.expr, if_.expr), if_.body)), blockb, WantPop(), WantFlow([], [], start.flow), self]

@_visitor(FwdFlow, AndStart, Block, WantPop, MaybeWantFlow, flag='has_jump_cond_fold')
def _visit_folded_if(self, deco, start, block, _, want):
    if len(block.stmts) != 1:
        raise PythonError("extra and-ifdead statements")
    if_ = block.stmts[0]
    if not isinstance(if_, StmtIfDead):
        raise PythonError("wrong and-ifdead statements")
    want.false.extend(start.flow)
    return [StmtIfDead(ExprBoolAnd(start.expr, if_.cond), if_.body), WantPop(), want, self]

@_visitor(JumpUnconditional, Expr, flag='has_if_expr')
def _visit_ifexpr(self, deco, expr):
    return [IfExprTrue(expr, self.flow)]

@_visitor(FwdFlow, AndStart, Block, IfExprTrue)
def _visit_ifexpr(self, deco, start, block, true):
    if self.flow not in start.flow:
        raise NoMatch
    if block.stmts:
        raise PythonError("extra if expr statements")
    return [IfExprElse(start.expr, true.expr, true.flow), WantPop(), WantFlow([], [], start.flow), self]

@_visitor(FwdFlow, OrStart, Block, IfExprTrue)
def _visit_ifexpr(self, deco, start, block, true):
    if self.flow not in start.flow:
        raise NoMatch
    if block.stmts:
        raise PythonError("extra if expr statements")
    return [IfExprElse(ExprNot(start.expr), true.expr, true.flow), WantPop(), WantFlow([], start.flow, []), self]

@_visitor(FwdFlow, IfExprElse, Expr, MaybeWantFlow)
def _visit_ifexpr(self, deco, if_, false, want):
    res = ExprIf(if_.cond, if_.true, false)
    want.any.extend(if_.flow)
    return [ExprIf(if_.cond, if_.true, false), want, self]

@_visitor(FwdFlow, AndStart, Block, IfExprElse, WantPop, MaybeWantFlow, flag='has_jump_cond_fold')
def _visit_folded_if(self, deco, start, block, if_, _, want):
    if block.stmts:
        raise PythonError("extra and-if expr statements")
    want.false.extend(start.flow)
    return [IfExprElse(ExprBoolAnd(start.expr, if_.cond), if_.true, if_.flow), WantPop(), want, self]

@_visitor(FwdFlow, AndStart, Block, IfExprTrue)
def _visit_ifexpr(self, deco, start, block, true):
    if self.flow in start.flow:
        raise NoMatch
    if block.stmts:
        raise PythonError("extra if expr and statements")
    return [IfExprTrue(ExprBoolAnd(start.expr, true.expr), start.flow + true.flow), self]

@_visitor(FwdFlow, OrStart, Block, IfExprTrue)
def _visit_ifexpr(self, deco, start, block, true):
    if self.flow in start.flow:
        raise NoMatch
    if block.stmts:
        raise PythonError("extra if expr or statements")
    return [IfExprTrue(ExprBoolOr(start.expr, true.expr), start.flow + true.flow), self]

@_visitor(JumpSkipJunk, Expr)
def _visit_ifexpr_true(self, deco, expr):
    return [IfExprElse(ExprAnyTrue(), expr, self.flow), WantPop()]

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

@_visitor(FwdFlow, AndStart, Block, MaybeWantFlow)
def _visit_dead_if(self, deco, start, block, want):
    block = _process_dead_end(deco, block)
    if any(want):
        return [FinalElse(want.any + want.true + want.false, FinalIf(start.expr, block)), Block([]), WantPop(), WantFlow([], [], start.flow), self]
    else:
        return [StmtIfDead(start.expr, block), WantPop(), WantFlow([], [], start.flow), self]

@_visitor(FwdFlow, OrStart, Block, MaybeWantFlow)
def _visit_dead_if_not(self, deco, start, block, want):
    block = _process_dead_end(deco, block)
    if any(want):
        return [FinalElse(want.any + want.true + want.false, FinalIf(ExprNot(start.expr), block)), Block([]), WantPop(), WantFlow([], start.flow, []), self]
    else:
        return [StmtIfDead(ExprNot(start.expr), block), WantPop(), WantFlow([], start.flow, []), self]

# comparisons

@_visitor(OpcodeCompareOp, Expr, Expr)
def _visit_cmp(self, deco, e1, e2):
    if self.param is CmpOp.EXC_MATCH:
        raise NoMatch
    return [ExprCmp([e1, self.param, e2])]

# chained comparisons

# start #1
@_visitor(OpcodeCompareOp, Expr, Expr, DupTop, RotThree)
def _visit_cmp_start(self, deco, a, b, _dup, _rot):
    if self.param is CmpOp.EXC_MATCH:
        raise NoMatch
    return [CompareStart([a, self.param, b], [])]

# start #2 and middle #3
@_visitor(JumpIfFalse, CompareStart)
def _visit_cmp_jump(self, deco, cmp):
    return [Compare(cmp.items, cmp.flows + self.flow), WantPop()]

# middle #2
@_visitor(OpcodeCompareOp, Compare, Expr, DupTop, RotThree)
def _visit_cmp_next(self, deco, cmp, expr, _dup, _rot):
    if self.param is CmpOp.EXC_MATCH:
        raise NoMatch
    return [CompareStart(cmp.items + [self.param, expr], cmp.flows)]

# end #1
@_visitor(OpcodeCompareOp, Compare, Expr)
def _visit_cmp_last(self, deco, cmp, expr):
    if self.param is CmpOp.EXC_MATCH:
        raise NoMatch
    return [CompareLast(cmp.items + [self.param, expr], cmp.flows)]

# end #2
@_visitor(JumpUnconditional, CompareLast)
def _visit_cmp_last_jump(self, deco, cmp):
    return [
        ExprCmp(cmp.items),
        WantFlow(self.flow, [], []),
        WantRotPop(),
        WantFlow([], [], cmp.flows)
    ]

# $loop framing

@_visitor(OpcodeSetupLoop)
def _visit_setup_loop(self, deco):
    return [SetupLoop(self.flow), Block([])]

@_visitor(OpcodePopBlock, SetupLoop, Block)
def _visit_pop_loop(self, deco, setup, block):
    return [FinalElse([setup.flow], FinalLoop(block)), Block([])]

# actual loops

@_visitor(RevFlow, Loop, Block)
def _visit_cont_in(self, deco, loop, block):
    if block.stmts:
        raise NoMatch
    loop.flow.append(self.flow)
    return [loop, block]

@_visitor(RevFlow)
def _visit_loop(self, deco):
    return [Loop([self.flow]), Block([])]

# continue

@_visitor(JumpContinue, Loop, LoopDammit)
def _visit_continue(self, deco, loop, items):
    for item in items:
        if isinstance(item, (ForLoop, TopForLoop, Block, AndStart, OrStart, FinalElse, TryExceptMid, TryExceptMatch, TryExceptAny, TryExceptEndTry)):
            pass
        else:
            raise NoMatch
    if not all(flow in loop.flow for flow in self.flow):
        raise NoMatch
    for flow in self.flow:
        loop.flow.remove(flow)
    return [loop] + items + [StmtContinue()]

@_visitor(OpcodeContinueLoop, Loop, LoopDammit)
def _visit_continue(self, deco, loop, items):
    seen = False
    for item in items:
        if isinstance(item, (SetupExcept, SetupFinally, With)):
            seen = True
        elif isinstance(item, (ForLoop, Block, AndStart, OrStart, FinalElse, TryExceptMid, TryExceptMatch, TryExceptAny)):
            pass
        else:
            raise NoMatch
    if not seen:
        raise PythonError("got CONTINUE_LOOP where a JUMP_ABSOLUTE would suffice")
    if self.flow not in loop.flow:
        raise NoMatch
    loop.flow.remove(self.flow)
    return [loop] + items + [StmtContinue()]

# while loop

def _loopit(deco, block):
    if (len(block.stmts) == 1
        and isinstance(block.stmts[0], StmtIfDead)
    ):
        if_ = block.stmts[0]
        return Block([StmtWhileRaw(if_.cond, if_.body)])
    else:
        raise PythonError("weird while loop")

@_visitor(OpcodePopBlock, SetupLoop, Block, Loop, Block)
def _visit_while(self, deco, setup, empty, loop, body):
    if empty.stmts:
        raise PythonError("junk before while in loop")
    if loop.flow:
        raise PythonError("loop not dry in pop block")
    return [FinalElse([setup.flow], FinalLoop(_loopit(deco, body))), Block([])]


@_visitor(OpcodePopTop, Loop, Block)
def _visit_while_true(self, deco, loop, body, flag='!has_while_true_end_opt'):
    if loop.flow:
        raise PythonError("loop not dry in pop block")
    return [StmtWhileRaw(ExprAnyTrue(), _process_dead_end(deco, body))]


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


@_visitor(JumpUnconditional, SetupLoop, Block, Loop, Block)
@_visitor(FwdFlow, SetupLoop, Block, Loop, Block)
def _visit_while_true(self, deco, setup, block, loop, body, flag='has_while_true_end_opt'):
    if block.stmts:
        raise PythonError("junk in optimized infinite loop")
    if loop.flow:
        raise PythonError("loop not dry in fake pop block")
    return [_make_inf_loop(deco, body.stmts, True), WantFlow([setup.flow], [], []), self]


@_visitor(JumpUnconditional, SetupLoop, Block)
@_visitor(FwdFlow, SetupLoop, Block)
def _visit_while_true(self, deco, setup, body, flag=('has_while_true_end_opt', 'has_dead_return')):
    return [_make_inf_loop(deco, body.stmts, False), WantFlow([setup.flow], [], []), self]

@_visitor(JumpContinue, SetupLoop, Block, Loop, Block, LoopDammit)
def _visit_continue(self, deco, setup, block, loop, body, items):
    for item in items:
        if isinstance(item, (ForLoop, TopForLoop, Block, AndStart, OrStart, FinalElse, TryExceptMid, TryExceptMatch, TryExceptAny, TryExceptEndTry)):
            pass
        else:
            raise NoMatch
    if loop.flow:
        raise PythonError("got outer continue, but inner loop not dry yet")
    if block.stmts:
        raise PythonError("non-empty loop block in outer continue")
    body, else_ = _split_inf_loop(deco, body.stmts, True)
    return [
        FinalElse([setup.flow], FinalLoop(Block([StmtWhileRaw(ExprAnyTrue(), body)]))),
        else_
    ] + items + [self]

# for loop

@_visitor(OpcodeForLoop, Expr, ExprInt, Loop, Block)
def _visit_for_start(self, deco, expr, zero, loop, block):
    if block.stmts:
        raise PythonError("junk in for")
    if zero.val != 0:
        raise PythonError("funny for loop start")
    return [loop, ForStart(expr, self.flow)]

@_visitor(Store, ForStart)
def visit_store_multi_start(self, deco, start):
    return [
        ForLoop(start.expr, self.dst, start.flow),
        Block([])
    ]

@_visitor(FwdFlow, Loop, ForLoop, Block)
def _visit_for_end(self, deco, loop, for_, body):
    if self.flow != for_.flow:
        raise NoMatch
    if loop.flow:
        raise PythonError("mismatched for loop")
    body = _process_dead_end(deco, body)
    return [StmtForRaw(for_.expr, for_.dst, body)]

@_visitor(JumpContinue, Loop, ForLoop, Block)
def _visit_for_end(self, deco, loop, for_, body):
    if loop.flow:
        raise NoMatch
    body = _process_dead_end(deco, body)
    return [StmtForRaw(for_.expr, for_.dst, body), WantFlow([for_.flow], [], []), self]

@_visitor(JumpUnconditional, Loop, ForLoop, Block)
def _visit_for_end(self, deco, loop, for_, body):
    if loop.flow:
        raise NoMatch
    body = _process_dead_end(deco, body)
    return [StmtForRaw(for_.expr, for_.dst, body), WantFlow([for_.flow], [], []), self]

# new for loop

@_visitor(OpcodeGetIter, Expr)
def visit_get_iter(self, deco, expr):
    return [Iter(expr)]

@_visitor(OpcodeForIter, Iter, Loop, Block)
def _visit_for_iter(self, deco, iter_, loop, block):
    if block.stmts:
        raise PythonError("junk in for")
    return [loop, ForStart(iter_.expr, self.flow)]

@_visitor(OpcodeForIter, Iter, flag='has_dead_return')
def _visit_for_iter(self, deco, iter_):
    return [Loop([]), ForStart(iter_.expr, self.flow)]

@_visitor(OpcodeForIter, Expr, Loop, Block)
def _visit_for_iter(self, deco, expr, loop, block):
    if block.stmts:
        raise PythonError("junk in for")
    return [loop, TopForStart(expr, self.flow)]

@_visitor(Store, TopForStart)
def visit_store_multi_start(self, deco, start):
    return [
        TopForLoop(start.expr, self.dst, start.flow),
        Block([])
    ]

@_visitor(FwdFlow, Loop, TopForLoop, Block)
def _visit_for_end(self, deco, loop, top, body):
    if self.flow != top.flow:
        raise NoMatch
    if loop.flow:
        raise PythonError("mismatched for loop")
    body = _process_dead_end(deco, body)
    return [StmtForTop(top.expr, top.dst, body)]

# break

@_visitor(OpcodeBreakLoop)
def _visit_break(self, deco):
    return [StmtBreak()]

# access

@_visitor(OpcodeAccessMode, ExprInt)
def _visit_access(self, deco, mode):
    return [StmtAccess(self.param, mode.val)]

# try finally

# need block to make sure we're not inside with
@_visitor(OpcodeSetupFinally, Block)
def _visit_setup_finally(self, deco, block):
    return [block, SetupFinally(self.flow), Block([])]

@_visitor(OpcodePopBlock, SetupFinally, Block)
def _visit_finally_pop(self, deco, setup, block):
    return [TryFinallyPending(block, setup.flow)]

@_visitor(FwdFlow, TryFinallyPending, ExprNone)
def _visit_finally(self, deco, try_, _):
    if try_.flow != self.flow:
        raise PythonError("funny finally")
    return [TryFinally(try_.body), Block([])]

@_visitor(OpcodeEndFinally, TryFinally, Block)
def _visit_finally_end(self, deco, try_, inner):
    return [StmtFinally(try_.body, inner)]

# try except

# start try except - store address of except clause

@_visitor(OpcodeSetupExcept)
def _visit_setup_except(self, deco):
    return [SetupExcept(self.flow), Block([])]

# finish try clause - pop block & jump to else clause, start except clause

@_visitor(OpcodePopBlock, SetupExcept, Block)
def _visit_except_pop_try(self, deco, setup, block):
    return [TryExceptEndTry(setup.flow, block)]

@_visitor(JumpUnconditional, TryExceptEndTry)
def _visit_except_end_try(self, deco, try_):
    return [TryExceptMid(self.flow, try_.body, [], None, []), WantFlow([try_.flow], [], [])]

@_visitor(StmtContinue, TryExceptEndTry)
def _visit_except_end_try(self, deco, try_):
    return [TryExceptMid([], Block(try_.body.stmts + [StmtFinalContinue()]), [], None, []), WantFlow([try_.flow], [], [])]

# except match clause:
#
# - dup exception type
# - compare with expression
# - jump to next if unmatched
# - pop comparison result and type
# - either pop or store value
# - pop traceback

@_visitor(OpcodeCompareOp, TryExceptMid, DupTop, Expr)
def _visit_except_match_check(self, deco, try_, _, expr):
    if try_.any:
        raise PythonError("making an except match after blanket")
    if self.param != CmpOp.EXC_MATCH:
        raise PythonError("funny except match")
    return [try_, TryExceptMatchMid(expr)]

@_visitor(JumpIfFalse, TryExceptMatchMid)
def _visit_except_match_jump(self, deco, mid):
    return [
        TryExceptMatchOk(mid.expr, self.flow),
        WantPop(),
        WantPop()
    ]

@_visitor(OpcodePopTop, TryExceptMatchOk)
def _visit_except_match_pop(self, deco, try_):
    return [
        TryExceptMatch(try_.expr, None, try_.next),
        Block([]),
        WantPop()
    ]

@_visitor(Store, TryExceptMatchOk)
def _visit_except_match_store(self, deco, match):
    return [
        TryExceptMatch(match.expr, self.dst, match.next),
        Block([]),
        WantPop()
    ]

@_visitor(OpcodePopExcept)
def _visit_pop_except(self, deco):
    return [PopExcept()]

@_visitor(FwdFlow, TryExceptMid, TryExceptMatch, Block, MaybeWantFlow, PopExcept)
def _visit_except_match_end(self, deco, try_, match, block, want, _):
    return [
        TryExceptMid(
            try_.else_,
            try_.body,
            try_.items + [(match.expr, match.dst, _process_dead_end(deco, block))],
            None,
            try_.flows + want.any + want.true + want.false,
        ),
        WantPop(),
        WantFlow([], [], match.next),
        self
    ]

@_visitor(JumpUnconditional, TryExceptMid, TryExceptMatch, Block, PopExcept)
def _visit_except_match_end(self, deco, try_, match, block, _):
    return [
        TryExceptMid(
            try_.else_,
            try_.body,
            try_.items + [(match.expr, match.dst, block)],
            None,
            try_.flows + self.flow,
        ),
        WantPop(),
        WantFlow([], [], match.next)
    ]

@_visitor(JumpUnconditional, TryExceptMid, TryExceptMatch, Block, flag='!has_pop_except')
def _visit_except_match_end(self, deco, try_, match, block):
    return [
        TryExceptMid(
            try_.else_,
            try_.body,
            try_.items + [(match.expr, match.dst, block)],
            None,
            try_.flows + self.flow,
        ),
        WantPop(),
        WantFlow([], [], match.next)
    ]

@_visitor(FwdFlow, TryExceptMid, TryExceptMatch, Block, MaybeWantFlow, flag='!has_pop_except')
def _visit_except_match_end(self, deco, try_, match, block, want):
    block = _process_dead_end(deco, block)
    return [
        TryExceptMid(
            try_.else_,
            try_.body,
            try_.items + [(match.expr, match.dst, block)],
            None,
            try_.flows + want.any + want.true + want.false,
        ),
        WantPop(),
        WantFlow([], [], match.next),
        self
    ]

@_visitor(OpcodePopTop, TryExceptMid)
def _visit_except_any(self, deco, try_):
    if try_.any:
        raise PythonError("making a second except blanket")
    return [
        try_,
        TryExceptAny(),
        Block([]),
        WantPop(),
        WantPop()
    ]

@_visitor(JumpUnconditional, TryExceptMid, TryExceptAny, Block, PopExcept)
def _visit_except_any_end(self, deco, try_, _, block, _2):
    return [
        TryExceptMid(
            try_.else_,
            try_.body,
            try_.items,
            block,
            try_.flows + self.flow,
        )
    ]

@_visitor(JumpUnconditional, TryExceptMid, TryExceptAny, Block, flag='!has_pop_except')
def _visit_except_any_end(self, deco, try_, _, block):
    return [
        TryExceptMid(
            try_.else_,
            try_.body,
            try_.items,
            block,
            try_.flows + self.flow,
        )
    ]

@_visitor(OpcodeEndFinally, TryExceptMid, TryExceptAny, Block, MaybeWantFlow, flag='!has_pop_except')
def _visit_except_any_end(self, deco, try_, _, block, want):
    block = _process_dead_end(deco, block)
    return [
        TryExceptMid(
            try_.else_,
            try_.body,
            try_.items,
            block,
            try_.flows + want.any + want.true + want.false,
        ),
        self
    ]

@_visitor(OpcodeEndFinally, TryExceptMid, TryExceptAny, Block, MaybeWantFlow, PopExcept)
def _visit_except_any_end(self, deco, try_, _, block, want, _2):
    block = _process_dead_end(deco, block)
    return [
        TryExceptMid(
            try_.else_,
            try_.body,
            try_.items,
            block,
            try_.flows + want.any + want.true + want.false,
        ),
        self
    ]

@_visitor(OpcodeEndFinally, TryExceptMid)
def _visit_except_end(self, deco, try_):
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

@_visitor(OpcodeBuildFunction, Code)
def _visit_build_function(self, deco, code):
    return [ExprFunctionRaw(deco_code(code), [], {}, [])]

@_visitor(OpcodeSetFuncArgs, ExprTuple, ExprFunctionRaw)
def _visit_set_func_args(self, deco, args, fun):
    # bug alert: def f(a, b=1) is compiled as def f(a=1, b)
    return [ExprFunctionRaw(fun.code, args.exprs, {}, [])]

# make function - py 1.3+

@_visitor(OpcodeMakeFunction, Exprs('param', 1), Code)
def _visit_make_function(self, deco, args, code):
    return [ExprFunctionRaw(deco_code(code), args, {}, [])]

@_visitor(OpcodeMakeFunctionNew, Exprs('kwargs', 2), Exprs('args', 1), Code, flag='!has_qualname')
def _visit_make_function(self, deco, kwargs, args, code):
    return [ExprFunctionRaw(
        deco_code(code),
        args,
        {deco.string(name): arg for name, arg in kwargs},
        []
    )]

@_visitor(OpcodeMakeFunctionNew, Exprs('kwargs', 2), Exprs('args', 1), Code, ExprUnicode, flag=('has_qualname', 'has_reversed_def_kwargs'))
def _visit_make_function(self, deco, kwargs, args, code, qualname):
    # XXX qualname
    return [ExprFunctionRaw(
        deco_code(code),
        args,
        {deco.string(name): arg for name, arg in kwargs},
        []
    )]

@_visitor(OpcodeMakeFunctionNew, Exprs('args', 1), Exprs('kwargs', 2), Code, ExprUnicode, flag=('has_qualname', '!has_reversed_def_kwargs'))
def _visit_make_function(self, deco, args, kwargs, code, qualname):
    # XXX qualname
    return [ExprFunctionRaw(
        deco_code(code),
        args,
        {deco.string(name): arg for name, arg in kwargs},
        []
    )]

@_visitor(OpcodeBuildTuple, Closures)
def visit_closure_tuple(self, deco, closures):
    return [ClosuresTuple([closure.var for closure in closures])]

@_visitor(OpcodeMakeClosure, Exprs('param', 1), UglyClosures, Code, flag='!has_sane_closure')
def _visit_make_function(self, deco, args, closures, code):
    return [ExprFunctionRaw(deco_code(code), args, {}, closures)]

@_visitor(OpcodeMakeClosure, Exprs('param', 1), ClosuresTuple, Code, flag='has_sane_closure')
def _visit_make_function(self, deco, args, closures, code):
    return [ExprFunctionRaw(deco_code(code), args, {}, closures.vars)]

@_visitor(OpcodeMakeClosureNew, Exprs('kwargs', 2), Exprs('args', 1), ClosuresTuple, Code, flag='!has_qualname')
def _visit_make_function(self, deco, kwargs, args, closures, code):
    return [ExprFunctionRaw(
        deco_code(code),
        args,
        {deco.string(name): arg for name, arg in kwargs},
        closures.vars
    )]

@_visitor(OpcodeMakeClosureNew, Exprs('kwargs', 2), Exprs('args', 1), ClosuresTuple, Code, ExprUnicode, flag=('has_qualname', 'has_reversed_def_kwargs'))
def _visit_make_function(self, deco, kwargs, args, closures, code, qualname):
    # XXX qualname
    return [ExprFunctionRaw(
        deco_code(code),
        args,
        {deco.string(name): arg for name, arg in kwargs},
        closures.vars
    )]

@_visitor(OpcodeMakeClosureNew, Exprs('args', 1), Exprs('kwargs', 2), ClosuresTuple, Code, ExprUnicode, flag=('has_qualname', '!has_reversed_def_kwargs'))
def _visit_make_function(self, deco, args, kwargs, closures, code, qualname):
    # XXX qualname
    return [ExprFunctionRaw(
        deco_code(code),
        args,
        {deco.string(name): arg for name, arg in kwargs},
        closures.vars
    )]

@_visitor(OpcodeUnaryCall, ExprFunctionRaw)
def _visit_unary_call(self, deco, fun):
    if fun.defargs:
        raise PythonError("class call with a function with default arguments")
    return [UnaryCall(fun.code)]

@_visitor(OpcodeLoadClosure)
def visit_load_closure(self, deco):
    return [Closure(deco.deref(self.param))]

@_visitor(OpcodeBuildClass, Expr, ExprTuple, UnaryCall)
def _visit_build_class(self, deco, name, bases, call):
    return [ExprClassRaw(deco.string(name), CallArgs([('', expr) for expr in bases.exprs]), call.code, [])]

@_visitor(OpcodeBuildClass, Expr, ExprTuple, ExprCall, flag='has_kwargs')
def _visit_build_class(self, deco, name, bases, call):
    if call.args.args:
        raise PythonError("class call with args")
    fun = call.expr
    if not isinstance(fun, ExprFunctionRaw):
        raise PythonError("class call with non-function")
    if fun.defargs or fun.defkwargs:
        raise PythonError("class call with a function with default arguments")
    return [ExprClassRaw(deco.string(name), CallArgs([('', expr) for expr in bases.exprs]), fun.code, fun.closures)]

@_visitor(OpcodeLoadLocals)
def _visit_load_locals(self, deco):
    return [Locals()]

@_visitor(OpcodeReturnValue, Locals)
def _visit_return_locals(self, deco, _):
    return [StmtEndClass()]

@_visitor(OpcodeReserveFast)
def _visit_reserve_fast(self, deco):
    if deco.varnames is not None:
        raise PythonError("duplicate RESERVE_FAST")

    deco.varnames = self.param
    return []

@_visitor(OpcodeLoadBuildClass)
def _visit_load_build_class(self, deco):
    return [ExprBuildClass()]

@_visitor(OpcodeStoreLocals, ExprFast)
def _visit_load_build_class(self, deco, fast):
    if fast.idx != 0 or fast.name != '__locals__':
        raise PythonError("funny locals store")
    return [StmtStartClass()]

@_visitor(OpcodeReturnValue, Closure)
def _visit_return_locals(self, deco, closure):
    if closure.var.name != '__class__':
        raise PythonError("returning a funny closure")
    return [StmtReturnClass()]

# inplace assignments

def _register_inplace(otype, stype):
    @_visitor(otype)
    def _visit_inplace(self, deco):
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

@_visitor(Inplace, ExprName, Expr)
@_visitor(Inplace, ExprGlobal, Expr)
@_visitor(Inplace, ExprFast, Expr)
@_visitor(Inplace, ExprDeref, Expr)
def _visit_inplace_simple(self, deco, dst, src):
    return [InplaceSimple(dst, src, self.stmt)]

@_visitor(Inplace, DupAttr, Expr)
def _visit_inplace_attr(self, deco, dup, src):
    return [InplaceAttr(dup.expr, dup.name, src, self.stmt)]

@_visitor(Inplace, DupSubscr, Expr)
def _visit_inplace_subscr(self, deco, dup, src):
    return [InplaceSubscr(dup.expr, dup.index, src, self.stmt)]

@_visitor(Inplace, DupSliceNN, Expr)
def _visit_inplace_slice_nn(self, deco, dup, src):
    return [InplaceSliceNN(dup.expr, src, self.stmt)]

@_visitor(Inplace, DupSliceEN, Expr)
def _visit_inplace_slice_en(self, deco, dup, src):
    return [InplaceSliceEN(dup.expr, dup.start, src, self.stmt)]

@_visitor(Inplace, DupSliceNE, Expr)
def _visit_inplace_slice_ne(self, deco, dup, src):
    return [InplaceSliceNE(dup.expr, dup.end, src, self.stmt)]

@_visitor(Inplace, DupSliceEE, Expr)
def _visit_inplace_slice_ee(self, deco, dup, src):
    return [InplaceSliceEE(dup.expr, dup.start, dup.end, src, self.stmt)]

@_visitor(OpcodeLoadAttr, Expr, DupTop)
def _visit_load_attr_dup(self, deco, expr, _):
    return [DupAttr(expr, self.param)]

@_visitor(OpcodeBinarySubscr, Expr, Expr, DupTwo)
def _visit_load_subscr_dup(self, deco, a, b, _dup):
    return [DupSubscr(a, b)]

@_visitor(OpcodeSliceNN, Expr, DupTop)
def _visit_slice_nn_dup(self, deco, expr, _):
    return [DupSliceNN(expr)]

@_visitor(OpcodeSliceEN, Expr, Expr, DupTwo)
def _visit_slice_en_dup(self, deco, a, b, _dup):
    return [DupSliceEN(a, b)]

@_visitor(OpcodeSliceNE, Expr, Expr, DupTwo)
def _visit_slice_ne_dup(self, deco, a, b, _dup):
    return [DupSliceNE(a, b)]

@_visitor(OpcodeSliceEE, Expr, Expr, Expr, DupThree)
def _visit_slice_ee_dup(self, deco, a, b, c, _dup):
    return [DupSliceEE(a, b, c)]

@_visitor(Store, InplaceSimple)
def _visit_inplace_store_name(self, deco, inp):
    if inp.dst != self.dst:
        raise PythonError("simple inplace dest mismatch")
    return [inp.stmt(inp.dst, inp.src)]

@_visitor(OpcodeStoreAttr, InplaceAttr, RotTwo)
def _visit_inplace_store_attr(self, deco, inp, _):
    if inp.name != self.param:
        raise PythonError("inplace name mismatch")
    return [inp.stmt(ExprAttr(inp.expr, inp.name), inp.src)]

@_visitor(OpcodeStoreSubscr, InplaceSubscr, RotThree)
def _visit_inplace_store_subscr(self, deco, inp, _rot):
    return [inp.stmt(ExprSubscr(inp.expr, inp.index), inp.src)]

@_visitor(OpcodeStoreSliceNN, InplaceSliceNN, RotTwo)
def _visit_inplace_store_slice_nn(self, deco, inp, _rot):
    return [inp.stmt(ExprSubscr(inp.expr, ExprSlice(None, None)), inp.src)]

@_visitor(OpcodeStoreSliceEN, InplaceSliceEN, RotThree)
def _visit_inplace_store_slice_en(self, deco, inp, _rot):
    return [inp.stmt(ExprSubscr(inp.expr, ExprSlice(inp.start, None)), inp.src)]

@_visitor(OpcodeStoreSliceNE, InplaceSliceNE, RotThree)
def _visit_inplace_store_slice_ne(self, deco, inp, _rot):
    return [inp.stmt(ExprSubscr(inp.expr, ExprSlice(None, inp.end)), inp.src)]

@_visitor(OpcodeStoreSliceEE, InplaceSliceEE, RotFour)
def _visit_inplace_store_slice_ee(self, deco, inp, _rot):
    return [inp.stmt(ExprSubscr(inp.expr, ExprSlice(inp.start, inp.end)), inp.src)]

# list comprehensions

@_visitor(Store, DupAttr)
def visit_listcomp_start(self, deco, dup):
    if not isinstance(self.dst, (ExprName, ExprFast, ExprGlobal)):
        raise NoMatch
    return [TmpVarAttrStart(self.dst, dup.expr, dup.name)]

@_visitor(StmtForRaw, TmpVarAttrStart, flag='!has_list_append')
def _visit_listcomp(self, deco, start):
    if (not isinstance(start.expr, ExprList)
        or len(start.expr.exprs) != 0
        or start.name != 'append'):
        raise PythonError("weird listcomp start")
    stmt, items = uncomp(self, False, False)
    if not (isinstance(stmt, StmtSingle)
        and isinstance(stmt.val, ExprCall)
        and stmt.val.expr == start.tmp
        and len(stmt.val.args.args) == 1
        and not stmt.val.args.args[0][0]
    ):
        raise PythonError("weird old list comp")
    return [ExprListComp(Comp(stmt.val.args.args[0][1], items)), TmpVarCleanup(start.tmp)]

@_visitor(StmtForRaw, MultiAssign, flag='has_list_append')
def _visit_listcomp(self, deco, ass):
    if len(ass.dsts) != 1:
        raise PythonError("multiassign in list comp too long")
    if not isinstance(ass.src, ExprList) or ass.src.exprs:
        raise PythonError("comp should start with an empty list")
    tmp = ass.dsts[0]
    stmt, items = uncomp(self, False, False)
    if not (isinstance(stmt, StmtListAppend)
        and stmt.tmp == tmp
    ):
        raise PythonError("weird old list comp")
    return [ExprListComp(Comp(stmt.val, items)), TmpVarCleanup(tmp)]

@_visitor(StmtDel, TmpVarCleanup)
def visit_listcomp_end(self, deco, comp):
    if comp.tmp != self.val:
        raise PythonError("deleting a funny name")
    return []

@_visitor(OpcodeListAppend, Expr, Expr)
def visit_listcomp_item(self, deco, tmp, val):
    return [StmtListAppend(tmp, val)]

@_visitor(OpcodeSetAdd, Expr, Expr)
def visit_listcomp_item(self, deco, tmp, val):
    return [StmtSetAdd(tmp, val)]

@_visitor(OpcodeStoreSubscr, Expr, Expr, RotTwo, Expr)
def visit_listcomp_item(self, deco, tmp, val, _, key):
    return [StmtMapAdd(tmp, key, val)]

# new comprehensions

@_visitor(OpcodeCallFunction, ExprFunctionRaw, Iter)
def visit_call_function(self, deco, fun, arg):
    if (fun.defargs
        or fun.defkwargs
        or self.args != 1
        or self.kwargs != 0
    ):
        raise NoMatch
    return [ExprCallComp(fun, arg.expr)]

@_visitor(StmtForTop, MultiAssign, flag='has_setdict_comp')
def _visit_fun_comp(self, deco, ass):
    if len(ass.dsts) != 1:
        raise PythonError("too many dsts to be a comp")
    tmp = ass.dsts[0]
    if not isinstance(tmp, ExprFast):
        raise PythonError("funny tmp for new comp")
    stmt, items, (topdst, arg) = uncomp(self, False, True)
    if isinstance(ass.src, ExprList) and deco.version.has_fun_listcomp:
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

@_visitor(OpcodeYieldValue, Expr, flag='!has_yield_expr')
def _visit_yield_stmt(self, deco, expr):
    return [StmtSingle(ExprYield(expr))]

@_visitor(OpcodeYieldValue, Expr, flag='has_yield_expr')
def _visit_yield_stmt(self, deco, expr):
    return [ExprYield(expr)]

@_visitor(OpcodeYieldFrom, Iter, ExprNone)
def _visit_yield_from(self, deco, iter_, _):
    return [ExprYieldFrom(iter_.expr)]


# with

@_visitor(OpcodeLoadAttr, DupAttr, RotTwo, flag=('has_with', '!has_setup_with', '!has_exit_tmp'))
def _visit_with_exit(self, deco, dup, _):
    if dup.name != '__exit__' or self.param != '__enter__':
        raise PythonError("weird with start")
    return [WithEnter(None, dup.expr)]

@_visitor(OpcodeLoadAttr, TmpVarAttrStart, flag=('has_with', '!has_setup_with', 'has_exit_tmp'))
def _visit_with_exit(self, deco, start):
    if start.name != '__exit__' or self.param != '__enter__':
        raise PythonError("weird with start")
    return [WithEnter(start.tmp, start.expr)]

@_visitor(OpcodeCallFunction, WithEnter)
def _visit_with_enter(self, deco, enter):
    if self.args != 0 or self.kwargs != 0:
        raise NoMatch
    return [WithResult(enter.tmp, enter.expr)]

@_visitor(OpcodePopTop, WithResult)
def _visit_with_pop(self, deco, result):
    return [WithStart(result.tmp, result.expr)]

@_visitor(Store, WithResult)
def _visit_with_pop(self, deco, result):
    return [WithStartTmp(result.tmp, result.expr, self.dst)]

@_visitor(OpcodeSetupFinally, WithStartTmp)
def _visit_setup_finally(self, deco, start):
    return [WithTmp(start.tmp, start.expr, start.res, self.flow)]

@_visitor(StmtDel, WithTmp, Expr)
def _visit_finally(self, deco, with_, expr):
    if not (expr == self.val == with_.res):
        raise PythonError("funny with tmp")
    return [WithInnerResult(with_.tmp, with_.expr, with_.flow)]

@_visitor(Store, WithInnerResult)
def _visit_store_with(self, deco, start):
    return [With(start.tmp, start.expr, self.dst, start.flow), Block([])]

@_visitor(OpcodeSetupFinally, WithStart)
def _visit_setup_finally(self, deco, start):
    return [With(start.tmp, start.expr, None, self.flow), Block([])]

@_visitor(OpcodePopBlock, With, Block)
def _visit_with_pop(self, deco, with_, block):
    return [WithEndPending(with_.tmp, with_.flow, StmtWith(with_.expr, with_.dst, block))]

@_visitor(FwdFlow, WithEndPending, ExprNone)
def _visit_finally(self, deco, end, _):
    if end.flow != self.flow:
        raise PythonError("funny with end")
    return [WithEnd(end.tmp, end.stmt)]

@_visitor(StmtDel, WithEnd, Expr)
def _visit_finally(self, deco, end, expr):
    if not (expr == self.val == end.tmp):
        raise PythonError("funny with exit")
    return [WithExit(end.stmt)]

@_visitor(OpcodeWithCleanup, WithEnd, flag='!has_exit_tmp')
def _visit_with_exit(self, deco, exit):
    return [WithExitDone(exit.stmt)]

@_visitor(OpcodeWithCleanup, WithExit)
def _visit_with_exit(self, deco, exit):
    return [WithExitDone(exit.stmt)]

@_visitor(OpcodeEndFinally, WithExitDone)
def _visit_with_exit(self, deco, exit):
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
                for flow in reversed(inflow[op.pos]):
                    if flow.dst > flow.src:
                        flow = FwdFlow(flow)
                    else:
                        flow = RevFlow(flow)
                    self.process(flow)
            self.process(op)
        if len(self.stack) != 1:
            raise PythonError("stack non-empty at the end: {}".format(
                ', '.join(type(x).__name__ for x in self.stack)
            ))
        if not isinstance(self.stack[0], Block):
            raise PythonError("weirdness on stack at the end")
        self.res = DecoCode(self.stack[0], code, self.varnames)

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
                if isinstance(op, OpcodeJumpIfFalse):
                    after_jif[op.nextpos] = op.pos
                elif isinstance(op, OpcodeJumpIfTrue):
                    after_jit[op.nextpos] = op.pos
            newops = []
            for op in ops:
                if isinstance(op, OpcodeJumpIfFalse) and op.flow.dst in after_jit:
                    newops.append(OpcodeJumpIfFalse(op.pos, op.nextpos, Flow(op.pos, after_jit[op.flow.dst])))
                elif isinstance(op, OpcodeJumpIfTrue) and op.flow.dst in after_jif:
                    newops.append(OpcodeJumpIfTrue(op.pos, op.nextpos, Flow(op.pos, after_jif[op.flow.dst])))
                else:
                    newops.append(op)
            ops = newops
        # second pass: figure out the kinds of absolute jumps
        condflow = {op.nextpos: [] for op in ops}
        for op in ops:
            if isinstance(op, (OpcodeJumpIfTrue, OpcodeJumpIfFalse, OpcodeForLoop, OpcodeForIter, OpcodeSetupExcept)):
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
            elif isinstance(op, OpcodeJumpIfTrue):
                op = JumpIfTrue(op.pos, op.nextpos, [op.flow])
                newops.append(op)
            elif isinstance(op, OpcodeJumpIfFalse):
                op = JumpIfFalse(op.pos, op.nextpos, [op.flow])
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
                        if isinstance(item, Regurgitable):
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


def deco_code(code):
    return DecoCtx(code).res


class DecoCode:
    __slots__ = 'block', 'code', 'varnames'

    def __init__(self, block, code, varnames):
        self.block = block
        self.code = code
        self.varnames = varnames

    def subprocess(self, process):
        return DecoCode(process(self.block), self.code, self.varnames)

    def show(self):
        return self.block.show()
