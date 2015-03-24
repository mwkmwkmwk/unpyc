from collections import namedtuple

from .helpers import PythonError
from .stmt import *
from .expr import *
from .code import Code
from .bytecode import *

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
#   - optimizer
#
#     - LOAD_CONST truthy ; JUMP_IF_FALSE xxx ; POP_TOP ->
#       JUMP_FORWARD 4 ; JUMP_IF_FALSE xxx ; POP_TOP
#
#       Can be undone by a simple pre-process pass. However,
#       still has to be taken into account for its impact
#       on the following.
#
#     - any jump to JUMP_FORWARD/ABSOLUTE -> retarget
#
#       Impact:
#
#       forward @ forward
#       forward @ absolute
#       absolute @ forward
#       absolute @ absolute
#       absolute @ fake
#       conditional @ forward
#       conditional @ absolute
#
#   - encoding...
#   - SET_LINENO no more
#   - nofree flag
#
# - py 2.4:
#
#   - None is now a keyword
#   - genexp
#   - enter peephole:
#
#     - UNARY_NOT JUMP_IF_FALSE [POP] -> JUMP_IF_TRUE [POP]
#     - true const JUMP_IF_FALSE POP -> NOPs
#     - pack/unpack for 1, 2, 3 is folded to rots
#     - JUMP_IF_FALSE/TRUE chain shortening
#     - nukes redundant return None
#
# - py 2.5:
#
#   - relative imports
#   - with
#   - try / except / finally
#   - if/else expression
#   - the compiler has been rewritten. have fun, [TODO]
#
# - py 2.6:
#
#   - except a as b
#   - different with sequence
#
# - py 3.0 & 2.7:
#
#   - setcomp & dictcomp [different in 3.0]
#   - set displays. also the frozenset optimization. [different in 3.0]
#   - some opcodes gratuitously moved
#
# - py 3.0:
#
#   - yeah, well, unicode is everywhere
#   - extended unpack
#   - kwdefaults, annotations
#   - new build class
#   - real funny except
#   - make closure change?
#   - has some opcodes
#   - nonlocal
#   - ellipsis allowed everywhere
#   - list comprehensions are functions
#   - still new with sequence
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
#   - another EXTENDED_ARG move
#   - dup_topx/rot4 -> dup_top_two
#   - del deref
#   - from .
#
# - py 3.3:
#
#   - yield from
#   - qualnames
#
# - py 3.4:
#
#   - classderef
#   - store locals is gone
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

UnpackSlot = namedtuple('UnpackSlot', ['expr', 'idx'])
UnpackArgSlot = namedtuple('UnpackArgSlot', ['args', 'idx'])
UnpackVarargSlot = namedtuple('UnpackVarargSlot', ['args'])

JumpIfFalse = namedtuple('JumpIfFalse', ['expr', 'flow'])
JumpIfTrue = namedtuple('JumpIfTrue', ['expr', 'flow'])

AndStart = namedtuple('AndStart', ['expr', 'flow'])
IfStart = namedtuple('IfStart', ['expr', 'flow'])
WhileStart = namedtuple('WhileStart', ['expr', 'flow'])
CompIfStart = namedtuple('CompIfStart', ['expr', 'flow'])
OrStart = namedtuple('OrStart', ['expr', 'flow'])
IfElse = namedtuple('IfElse', ['expr', 'body', 'flow'])

CompareStart = namedtuple('CompareStart', ['items', 'flows'])
Compare = namedtuple('Compare', ['items', 'flows'])
CompareLast = namedtuple('CompareLast', ['items', 'flows'])
CompareNext = namedtuple('CompareNext', ['items', 'flows'])

WantPop = namedtuple('WantPop', [])
WantRotPop = namedtuple('WantRotPop', [])
WantFlow = namedtuple('WantFlow', ['flow'])

SetupLoop = namedtuple('SetupLoop', ['flow'])
SetupFinally = namedtuple('SetupFinally', ['flow'])
SetupExcept = namedtuple('SetupExcept', ['flow'])

LoopElse = namedtuple('LoopElse', ['flow', 'body'])

Loop = namedtuple('Loop', ['flow', 'cont'])
While = namedtuple('While', ['expr', 'end', 'block'])
ForStart = namedtuple('ForStart', ['expr', 'loop', 'flow'])
ForLoop = namedtuple('ForLoop', ['expr', 'dst', 'loop', 'flow'])
CompForLoop = namedtuple('CompForLoop', ['loop', 'flow'])

TryFinallyPending = namedtuple('TryFinallyPending', ['body', 'flow'])
TryFinally = namedtuple('TryFinally', ['body'])

TryExceptEndTry = namedtuple('TryExceptEndTry', ['flow', 'body'])
TryExceptMid = namedtuple('TryExceptMid', ['else_', 'body', 'items', 'any', 'flows'])
TryExceptMatchMid = namedtuple('TryExceptMatchMid', ['expr'])
TryExceptMatchOk = namedtuple('TryExceptMatchOk', ['expr', 'next'])
TryExceptMatch = namedtuple('TryExceptMatch', ['expr', 'dst', 'next'])
TryExceptAny = namedtuple('TryExceptAny', [])
TryExceptElse = namedtuple('TryExceptElse', ['body', 'items', 'any', 'flows'])

UnaryCall = namedtuple('UnaryCall', ['code'])
Locals = namedtuple('Locals', [])

DupAttr = namedtuple('DupAttr', ['expr', 'name'])
DupSubscr = namedtuple('DupSubscr', ['expr', 'index'])
DupSliceNN = namedtuple('DupSliceNN', ['expr'])
DupSliceEN = namedtuple('DupSliceEN', ['expr', 'start'])
DupSliceNE = namedtuple('DupSliceNE', ['expr', 'end'])
DupSliceEE = namedtuple('DupSliceEE', ['expr', 'start', 'end'])

InplaceName = namedtuple('InplaceName', ['name', 'src', 'stmt'])
InplaceGlobal = namedtuple('InplaceGlobal', ['name', 'src', 'stmt'])
InplaceFast = namedtuple('InplaceFast', ['idx', 'src', 'stmt'])
InplaceDeref = namedtuple('InplaceDeref', ['idx', 'src', 'stmt'])
InplaceAttr = namedtuple('InplaceAttr', ['expr', 'name', 'src', 'stmt'])
InplaceSubscr = namedtuple('InplaceSubscr', ['expr', 'index', 'src', 'stmt'])
InplaceSliceNN = namedtuple('InplaceSliceNN', ['expr', 'src', 'stmt'])
InplaceSliceEN = namedtuple('InplaceSliceEN', ['expr', 'start', 'src', 'stmt'])
InplaceSliceNE = namedtuple('InplaceSliceNE', ['expr', 'end', 'src', 'stmt'])
InplaceSliceEE = namedtuple('InplaceSliceEE', ['expr', 'start', 'end', 'src', 'stmt'])

OldListCompStart = namedtuple('OldListCompStart', ['expr', 'tmp'])
CompLevel = namedtuple('CompLevel', ['meat', 'items'])

Closure = namedtuple('Closure', ['var'])
ClosuresTuple = namedtuple('ClosuresTuple', ['vars'])

# a special marker to put in stack want lists - will match getattr(opcode, attr)
# expressions and pass a list
Exprs = namedtuple('Exprs', ['attr', 'factor'])
UglyClosures = object()
Closures = object()

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
            return False
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
                    return False
                code = deco.stack[-1]
                if not isinstance(code, Code):
                    return False
                closure_num = len(code.freevars)
                total += closure_num
            else:
                total += 1
        if len(deco.stack) < total:
            return False
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
                            return False
                        exprs.append(expr)
                    exprs.reverse()
                    arg.append(expr if want.factor == 1 else exprs)
                arg.reverse()
            elif want is Closures:
                arg = []
                for _ in range(opcode.param):
                    expr = stack.pop()
                    if not isinstance(expr, Closure):
                        return False
                    arg.append(expr)
                arg.reverse()
            elif want is UglyClosures:
                arg = []
                for _ in range(closure_num):
                    closure = stack.pop()
                    if not isinstance(closure, Closure):
                        return False
                    arg.append(closure.var)
                arg.reverse()
            else:
                arg = stack.pop()
                if not isinstance(arg, want):
                    return False
            args.append(arg)
        args.reverse()
        try:
            res = self.func(opcode, deco, *args)
        except NoMatch:
            return False
        else:
            if total:
                deco.stack[-total:] = []
            deco.stack += res
            return True


def _visitor(op, *stack, **kwargs):
    def inner(func):
        _VISITORS.setdefault(op, []).append(_Visitor(func, stack, **kwargs))
        return func
    return inner

def _stmt_visitor(op, *stack, **kwargs):
    def inner(func):
        @_visitor(op, Block, *stack, **kwargs)
        def visit_stmt(self, deco, block, *args):
            stmt, extra = func(self, deco, *args)
            block.stmts.append(stmt)
            return [block] + extra
        return func
    return inner

def _store_visitor(op, *stack):
    def inner(func):

        @_stmt_visitor(op, Expr, *stack)
        def visit_store_assign(self, deco, src, *args):
            dst, extra = func(self, deco, *args)
            return StmtAssign([dst], src), extra

        @_visitor(op, Block, Expr, DupTop, *stack)
        def visit_store_multi_start(self, deco, block, src, _, *args):
            dst, extra = func(self, deco, *args)
            return [block, MultiAssign(src, [dst])] + extra

        @_visitor(op, Block, MultiAssign, DupTop, *stack)
        def visit_store_multi_next(self, deco, block, multi, _, *args):
            dst, extra = func(self, deco, *args)
            multi.dsts.append(dst)
            return [block, multi] + extra

        @_stmt_visitor(op, MultiAssign, *stack)
        def visit_store_multi_end(self, deco, multi, *args):
            dst, extra = func(self, deco, *args)
            multi.dsts.append(dst)
            stmt = StmtAssign(multi.dsts, multi.src)
            return stmt, extra

        @_visitor(op, UnpackSlot, *stack)
        def visit_store_unpack(self, deco, slot, *args):
            dst, extra = func(self, deco, *args)
            slot.expr.exprs[slot.idx] = dst
            return extra

        @_visitor(op, UnpackArgSlot, *stack)
        def visit_store_unpack_arg(self, deco, slot, *args):
            dst, extra = func(self, deco, *args)
            slot.args.args[slot.idx] = dst
            return extra

        @_visitor(op, UnpackVarargSlot, *stack)
        def visit_store_unpack_vararg(self, deco, slot, *args):
            dst, extra = func(self, deco, *args)
            slot.args.vararg = dst
            return extra

        @_visitor(op, Block, ForStart, *stack)
        def visit_store_multi_start(self, deco, block, start, *args):
            dst, extra = func(self, deco, *args)
            return [
                block,
                ForLoop(start.expr, dst, start.loop, start.flow),
                Block([])
            ] + extra

        @_visitor(op, CompLevel, ForStart, *stack)
        def visit_store_multi_start(self, deco, comp, start, *args):
            dst, extra = func(self, deco, *args)
            return [
                comp,
                CompForLoop(start.loop, start.flow),
                CompLevel(comp.meat, comp.items + [CompFor(dst, start.expr)])
            ] + extra

        @_visitor(op, MultiAssign, ForStart, *stack, flag='has_list_append')
        def visit_store_multi_start(self, deco, ass, start, *args):
            dst, extra = func(self, deco, *args)
            if len(ass.dsts) != 1:
                raise PythonError("multiassign in list comp too long")
            if not isinstance(ass.src, ExprList) or ass.src.exprs:
                raise PythonError("comp should start with an empty list")
            expr = ExprListComp()
            meat = OldListCompStart(expr, ass.dsts[0])
            comp = CompLevel(meat, [])
            return [
                expr,
                meat,
                comp,
                CompForLoop(start.loop, start.flow),
                CompLevel(comp.meat, comp.items + [CompFor(dst, start.expr)])
            ] + extra

        @_visitor(op, TryExceptMatchOk, *stack)
        def _visit_except_match_store(self, deco, match, *args):
            dst, extra = func(self, deco, *args)
            return [
                TryExceptMatch(match.expr, dst, match.next),
                Block([]),
                WantPop()
            ] + extra

        @_stmt_visitor(op, Import, *stack)
        def _visit_store_name_import(self, deco, import_, *args):
            if import_.items:
                raise PythonError("non-empty items for plain import")
            dst, extra = func(self, deco, *args)
            return StmtImport(-1, import_.name, [], dst), extra

        @_stmt_visitor(op, Import2Simple, *stack)
        def _visit_store_name_import(self, deco, import_, *args):
            dst, extra = func(self, deco, *args)
            return StmtImport(import_.level, import_.name, import_.attrs, dst), extra

        return func
    return inner


def _lsd_visitor(op_load, op_store, op_delete, *stack):
    def inner(func):

        @_visitor(op_load, *stack)
        def visit_lsd_load(self, deco, *args):
            dst = func(self, deco, *args)
            return [dst]

        @_store_visitor(op_store, *stack)
        def visit_lsd_store(self, deco, *args):
            dst = func(self, deco, *args)
            return dst, []

        @_stmt_visitor(op_delete, *stack)
        def visit_lsd_delete(self, deco, *args):
            dst = func(self, deco, *args)
            return StmtDel(dst), []

        return func
    return inner

# visitors

# line numbers

@_visitor(OpcodeSetLineno)
def visit_set_lineno(self, deco):
    deco.lineno = self.param
    return []

# special stuff

@_visitor(OpcodeDupTop)
def visit_dup_top(self, deco):
    return [DupTop()]

@_visitor(OpcodeDupTopTwo)
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

@_visitor(OpcodeRotThree)
def visit_rot_three(self, deco):
    return [RotThree()]


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
    OpcodeBinarySubstract: ExprSub,
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
    return [ExprCall(expr, [('', arg) for arg in params.exprs])]

@_visitor(OpcodeCallFunction, Expr, Exprs('args', 1), Exprs('kwargs', 2))
def visit_call_function(self, deco, fun, args, kwargs):
    return [ExprCall(fun, [('', arg) for arg in args] + [(deco.string(name), arg) for name, arg in kwargs])]

@_visitor(OpcodeCallFunctionVar, Expr, Exprs('args', 1), Exprs('kwargs', 2), Expr)
def visit_call_function(self, deco, fun, args, kwargs, vararg):
    return [ExprCall(fun, [('', arg) for arg in args] + [(deco.string(name), arg) for name, arg in kwargs] + [('*', vararg)])]

@_visitor(OpcodeCallFunctionKw, Expr, Exprs('args', 1), Exprs('kwargs', 2), Expr)
def visit_call_function(self, deco, fun, args, kwargs, varkw):
    return [ExprCall(fun, [('', arg) for arg in args] + [(deco.string(name), arg) for name, arg in kwargs] + [('**', varkw)])]

@_visitor(OpcodeCallFunctionVarKw, Expr, Exprs('args', 1), Exprs('kwargs', 2), Expr, Expr)
def visit_call_function(self, deco, fun, args, kwargs, vararg, varkw):
    return [ExprCall(fun, [('', arg) for arg in args] + [(deco.string(name), arg) for name, arg in kwargs] + [('*', vararg), ('**', varkw)])]

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

@_stmt_visitor(OpcodeUnpackArg)
def visit_unpack_arg(self, deco):
    res = FunArgs([None for _ in range(self.param)], [], None, [], None)
    extra = [UnpackArgSlot(res, idx) for idx in reversed(range(self.param))]
    return StmtArgs(res), extra

@_stmt_visitor(OpcodeUnpackVararg)
def visit_unpack_arg(self, deco):
    res = FunArgs([None for _ in range(self.param)], [], None, [], None)
    extra = [UnpackVarargSlot(res)] + [UnpackArgSlot(res, idx) for idx in reversed(range(self.param))]
    return StmtArgs(res), extra

@_store_visitor(OpcodeUnpackTuple)
def visit_unpack_tuple(self, deco):
    res = ExprTuple([None for _ in range(self.param)])
    extra = [UnpackSlot(res, idx) for idx in reversed(range(self.param))]
    return res, extra

@_store_visitor(OpcodeUnpackSequence)
def visit_unpack_sequence(self, deco):
    res = ExprTuple([None for _ in range(self.param)])
    extra = [UnpackSlot(res, idx) for idx in reversed(range(self.param))]
    return res, extra

@_store_visitor(OpcodeUnpackList)
def visit_unpack_list(self, deco):
    res = ExprList([None for _ in range(self.param)])
    extra = [UnpackSlot(res, idx) for idx in reversed(range(self.param))]
    return res, extra

# single expression statement

@_stmt_visitor(OpcodePrintExpr, Expr)
def _visit_print_expr(self, deco, expr):
    return StmtPrintExpr(expr), []

@_stmt_visitor(OpcodePopTop, Expr, flag='!always_print_expr')
def _visit_single_expr(self, deco, expr):
    return StmtSingle(expr), []

# print statement

@_stmt_visitor(OpcodePrintItem, Expr)
def visit_print_item(self, deco, expr):
    return StmtPrint([expr], False), []

@_stmt_visitor(OpcodePrintNewline)
def visit_print_newline(self, deco):
    return StmtPrint([], True), []

# print to

@_visitor(OpcodePrintItemTo, Expr, DupTop, Expr, RotTwo)
def visit_print_item_to(self, deco, to, _dup, expr, _rot):
    return [StmtPrintTo(to, [expr], False)]

@_visitor(OpcodePrintItemTo, StmtPrintTo, DupTop, Expr, RotTwo)
def visit_print_item_to(self, deco, stmt, _dup, expr, _rot):
    stmt.vals.append(expr)
    return [stmt]

@_stmt_visitor(OpcodePopTop, StmtPrintTo)
def visit_print_to_end(self, deco, stmt):
    return stmt, []

@_stmt_visitor(OpcodePrintNewlineTo, StmtPrintTo)
def visit_print_newline_to(self, deco, stmt):
    stmt.nl = True
    return stmt, []

@_stmt_visitor(OpcodePrintNewlineTo, Expr)
def visit_print_newline_to(self, deco, expr):
    return StmtPrintTo(expr, [], True), []

# return statement

@_stmt_visitor(OpcodeReturnValue, Expr)
def _visit_return(self, deco, expr):
    return StmtReturn(expr), []

# raise statement

# Python 1.0 - 1.2
@_stmt_visitor(OpcodeRaiseException, Expr, ExprNone)
def _visit_raise_1(self, deco, cls, _):
    return StmtRaise(cls), []

@_stmt_visitor(OpcodeRaiseException, Expr, Expr)
def _visit_raise_2(self, deco, cls, val):
    return StmtRaise(cls, val), []

# Python 1.3-2.7
@_stmt_visitor(OpcodeRaiseVarargs, Exprs('param', 1), flag='!has_raise_from')
def _visit_raise_varargs(self, deco, exprs):
    if len(exprs) > 3:
        raise PythonError("too many args to raise")
    if len(exprs) == 0 and not deco.version.has_reraise:
        raise PythonError("too few args to raise")
    return StmtRaise(*exprs), []

# Python 3
@_stmt_visitor(OpcodeRaiseVarargs, Exprs('param', 1), flag='has_raise_from')
def _visit_raise_from(self, deco, exprs):
    if len(exprs) < 2:
        return StmtRaise(*exprs), []
    elif len(exprs) == 2:
        return StmtRaise(exprs[0], None, exprs[1]), []
    else:
        raise PythonError("too many args to raise")

# exec statement

@_stmt_visitor(OpcodeExecStmt, Expr, Expr, DupTop)
def _visit_exec_3(self, deco, code, env, _):
    if isinstance(env, ExprNone):
        return StmtExec(code), []
    else:
        return StmtExec(code, env), []

@_stmt_visitor(OpcodeExecStmt, Expr, Expr, Expr)
def _visit_exec_3(self, deco, code, globals, locals):
    return StmtExec(code, globals, locals), []

# imports

@_visitor(OpcodeImportName, flag='!has_import_as')
def _visit_import_name(self, deco):
    return [Import(self.param, [])]

@_stmt_visitor(OpcodeImportFrom, Import)
def _visit_import_from_star(self, deco, import_, flag="!has_import_star"):
    if self.param != '*':
        raise NoMatch
    if import_.items:
        raise PythonError("non-empty items for star import")
    return StmtImportStar(-1, import_.name), [WantPop()]

@_visitor(OpcodeImportFrom, Import)
def _visit_import_from(self, deco, import_):
    if self.param == '*':
        raise NoMatch
    import_.items.append(self.param)
    return [import_]

@_stmt_visitor(OpcodePopTop, Import)
def _visit_import_from_end(self, deco, import_):
    return StmtFromImport(-1, import_.name, [(x, None) for x in import_.items]), []

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

@_stmt_visitor(OpcodeImportStar, Import2Star)
def _visit_import_star(self, deco, import_):
    return StmtImportStar(import_.level, import_.name), []

@_visitor(OpcodeImportFrom, Import2From)
def _visit_import_from(self, deco, import_):
    idx = len(import_.exprs)
    import_.exprs.append(None)
    if (idx >= len(import_.fromlist) or import_.fromlist[idx] != self.param):
        raise PythonError("fromlist mismatch")
    return [import_, UnpackSlot(import_, idx)]

@_stmt_visitor(OpcodePopTop, Import2From)
def _visit_import_from_end(self, deco, import_):
    return StmtFromImport(import_.level, import_.name, list(zip(import_.fromlist, import_.exprs))), []

# if

@_visitor(OpcodeJumpIfFalse, Expr)
def _visit_jump_if_false(self, deco, expr):
    return [JumpIfFalse(expr, self.flow)]

@_visitor(OpcodeJumpIfTrue, Expr)
def _visit_jump_if_false(self, deco, expr):
    return [JumpIfTrue(expr, self.flow)]

@_visitor(OpcodePopTop, Block, JumpIfFalse)
def _visit_if(self, deco, block, jump):
    return [block, IfStart(jump.expr, jump.flow), Block([])]

@_visitor(OpcodePopTop, Loop, JumpIfFalse)
def _visit_if(self, deco, loop, jump):
    return [loop, WhileStart(jump.expr, jump.flow), Block([])]

@_visitor(OpcodePopTop, CompLevel, JumpIfFalse)
def _visit_if(self, deco, comp, jump):
    return [comp, CompIfStart(jump.expr, jump.flow), CompLevel(comp.meat, comp.items + [CompIf(jump.expr)])]

@_visitor(OpcodePopTop, JumpIfFalse)
def _visit_if(self, deco, jump):
    return [AndStart(jump.expr, jump.flow)]

@_visitor(OpcodePopTop, JumpIfTrue)
def _visit_if(self, deco, jump):
    return [OrStart(jump.expr, jump.flow)]

@_visitor(OpcodeJumpForward, Block, IfStart, Block)
def _visit_if_else(self, deco, block, if_, body):
    if if_.flow.dst != self.nextpos:
        raise PythonError("missing if code")
    return [block, IfElse(if_.expr, body, self.flow), Block([]), WantPop(), WantFlow(if_.flow)]

@_visitor(OpcodeJumpForward, CompLevel, CompIfStart)
def _visit_if_else(self, deco, comp, if_):
    if if_.flow.dst != self.nextpos:
        raise PythonError("missing if code")
    return [WantFlow(self.flow), WantPop(), WantFlow(if_.flow)]

@_visitor(Flow, WantFlow)
def _visit_flow(self, deco, want):
    if self != want.flow:
        raise NoMatch
    return []

@_visitor(OpcodePopTop, WantPop)
def _visit_want_pop(self, deco, want):
    return []

@_visitor(OpcodeRotTwo)
def _visit_rot_two(self, deco):
    return [RotTwo()]

@_visitor(OpcodePopTop, WantRotPop, RotTwo)
def _visit_want_rot_two(self, deco, want, _):
    return []

@_visitor(OpcodeRotFour)
def _visit_rot_four(self, deco):
    return [RotFour()]

@_stmt_visitor(Flow, IfElse, Block)
def _visit_if_end(self, deco, if_, inner):
    if self != if_.flow:
        raise PythonError("mismatch else flow")
    return StmtIf([(if_.expr, if_.body)], inner), []

@_visitor(Flow, WhileStart, Block, Expr)
def _visit_and(self, deco, start, block, expr):
    if self != start.flow:
        raise PythonError("funny and flow")
    if block.stmts:
        raise PythonError("extra and statements")
    return [ExprBoolAnd(start.expr, expr)]

@_visitor(Flow, IfStart, Block, Expr)
def _visit_and(self, deco, start, block, expr):
    if self != start.flow:
        raise PythonError("funny and flow")
    if block.stmts:
        raise PythonError("extra and statements")
    return [ExprBoolAnd(start.expr, expr)]

@_visitor(Flow, CompIfStart, Comp, Expr)
def _visit_and(self, deco, start, comp, expr):
    if self != start.flow:
        raise PythonError("funny and flow")
    if block.stmts:
        raise PythonError("extra and statements")
    return [ExprBoolAnd(start.expr, expr)]

@_visitor(Flow, AndStart, Expr)
def _visit_and(self, deco, start, expr):
    if self != start.flow:
        raise PythonError("funny and flow")
    return [ExprBoolAnd(start.expr, expr)]

@_visitor(Flow, OrStart, Expr)
def _visit_or(self, deco, start, expr):
    if self != start.flow:
        raise PythonError("funny or flow")
    return [ExprBoolOr(start.expr, expr)]

# assert. ouch.

@_stmt_visitor(OpcodeRaiseVarargs, IfStart, Block, OrStart, Exprs('param', 1), flag=('has_assert', '!has_short_assert'))
def _visit_assert_1(self, deco, ifstart, block, orstart, exprs):
    if block.stmts:
        raise PythonError("extra assert statements")
    if not isinstance(exprs[0], ExprGlobal) or exprs[0].name != 'AssertionError':
        raise PythonError("hmm, I wanted an assert...")
    if not isinstance(ifstart.expr, ExprGlobal) or ifstart.expr.name != '__debug__':
        raise PythonError("hmm, I wanted an assert...")
    if self.param == 1:
        return StmtAssert(orstart.expr), [WantPop(), WantFlow(orstart.flow), WantFlow(ifstart.flow)]
    elif self.param == 2:
        return StmtAssert(orstart.expr, exprs[1]), [WantPop(), WantFlow(orstart.flow), WantFlow(ifstart.flow)]
    else:
        raise PythonError("funny assert params")

@_stmt_visitor(OpcodeRaiseVarargs, OrStart, Exprs('param', 1), flag='has_short_assert')
def _visit_assert_1(self, deco, orstart, exprs):
    if not isinstance(exprs[0], ExprGlobal) or exprs[0].name != 'AssertionError':
        raise PythonError("hmm, I wanted an assert...")
    if self.param == 1:
        return StmtAssert(orstart.expr), [WantPop(), WantFlow(orstart.flow)]
    elif self.param == 2:
        return StmtAssert(orstart.expr, exprs[1]), [WantPop(), WantFlow(orstart.flow)]
    else:
        raise PythonError("funny assert params")

# comparisons

@_visitor(OpcodeCompareOp, Expr, Expr)
def _visit_cmp(self, deco, e1, e2):
    if self.mode is CmpOp.EXC_MATCH:
        raise NoMatch
    return [ExprCmp([e1, self.mode, e2])]

# chained comparisons

# start #1
@_visitor(OpcodeCompareOp, Expr, Expr, DupTop, RotThree)
def _visit_cmp_start(self, deco, a, b, _dup, _rot):
    if self.mode is CmpOp.EXC_MATCH:
        raise NoMatch
    return [CompareStart([a, self.mode, b], [])]

# start #2 and middle #3
@_visitor(OpcodeJumpIfFalse, CompareStart)
def _visit_cmp_jump(self, deco, cmp):
    return [Compare(cmp.items, cmp.flows + [self.flow]), WantPop()]

# middle #2
@_visitor(OpcodeCompareOp, Compare, Expr, DupTop, RotThree)
def _visit_cmp_next(self, deco, cmp, expr, _dup, _rot):
    if self.mode is CmpOp.EXC_MATCH:
        raise NoMatch
    return [CompareStart(cmp.items + [self.mode, expr], cmp.flows)]

# end #1
@_visitor(OpcodeCompareOp, Compare, Expr)
def _visit_cmp_last(self, deco, cmp, expr):
    if self.mode is CmpOp.EXC_MATCH:
        raise NoMatch
    return [CompareLast(cmp.items + [self.mode, expr], cmp.flows)]

# end #2
@_visitor(OpcodeJumpForward, CompareLast)
def _visit_cmp_last_jump(self, deco, cmp):
    return [
        ExprCmp(cmp.items),
        WantFlow(self.flow),
        WantRotPop(),
    ] + [WantFlow(flow) for flow in cmp.flows]

# $loop framing

@_visitor(OpcodeSetupLoop)
def _visit_setup_loop(self, deco):
    return [SetupLoop(self.flow), Block([])]

@_visitor(OpcodePopBlock, SetupLoop, Block)
def _visit_pop_loop(self, deco, setup, block):
    return [LoopElse(setup.flow, block), Block([])]

@_stmt_visitor(Flow, LoopElse, Block)
def _visit_end_loop(self, deco, loop, inner):
    if self != loop.flow:
        raise NoMatch
    return StmtLoop(loop.body, inner), []

# actual loops

@_visitor(Flow, Loop)
def _visit_cont_in(self, deco, loop):
    if self.src <= self.dst:
        raise NoMatch
    loop.cont.append(self)
    return [loop]

@_visitor(Flow)
def _visit_loop(self, deco):
    if self.src <= self.dst:
        raise NoMatch
    return [Loop(self, [])]

# continue

@_stmt_visitor(OpcodeJumpAbsolute)
def _visit_continue(self, deco):
    for item in reversed(deco.stack):
        if isinstance(item, Loop):
            loop = item
            break
        elif isinstance(item, ForLoop):
            loop = item.loop
            break
        elif isinstance(item, (Block, WhileStart, IfStart, IfElse, LoopElse, TryExceptMid, TryExceptMatch, TryExceptAny, TryExceptElse)):
            pass
        else:
            raise NoMatch
    if not loop.cont:
        raise NoMatch
    if loop.cont[-1] != self.flow:
        raise NoMatch
    loop.cont.pop()
    return StmtContinue(), []

@_stmt_visitor(OpcodeContinueLoop)
def _visit_continue(self, deco):
    seen = False
    for item in reversed(deco.stack):
        if isinstance(item, Loop):
            loop = item
            break
        elif isinstance(item, ForLoop):
            loop = item.loop
            break
        elif isinstance(item, SetupExcept):
            seen = True
        elif isinstance(item, (Block, WhileStart, IfStart, IfElse, LoopElse, TryExceptMid, TryExceptMatch, TryExceptAny, TryExceptElse)):
            pass
        else:
            raise NoMatch
    if not seen:
        raise PythonError("got CONTINUE_LOOP where a JUMP_ABSOLUTE would suffice")
    if not loop.cont:
        raise NoMatch
    if loop.cont[-1] != self.flow:
        raise NoMatch
    loop.cont.pop()
    return StmtContinue(), []

# while loop

@_stmt_visitor(OpcodeJumpAbsolute, Loop, WhileStart, Block)
def _visit_while(self, deco, loop, start, inner):
    if loop.cont:
        raise NoMatch
    # TODO validate flow
    if loop.flow != self.flow or start.flow.dst != self.nextpos:
        raise PythonError("funny while loop")
    return StmtWhileRaw(start.expr, inner), [WantPop(), WantFlow(start.flow)]

# for loop

@_visitor(OpcodeForLoop, Expr, ExprInt, Loop)
def _visit_for_start(self, deco, expr, zero, loop):
    if zero.val != 0:
        raise PythonError("funny for loop start")
    return [ForStart(expr, loop, self.flow)]

@_stmt_visitor(OpcodeJumpAbsolute, ForLoop, Block)
def _visit_for(self, deco, loop, inner):
    if loop.loop.cont:
        raise NoMatch
    if loop.loop.flow != self.flow or loop.flow.dst != self.nextpos:
        raise PythonError("mismatched for loop")
    return StmtForRaw(loop.expr, loop.dst, inner), [WantFlow(loop.flow)]

@_visitor(OpcodeJumpAbsolute, CompLevel, CompForLoop)
def _visit_for(self, deco, _, loop):
    if loop.loop.cont:
        raise NoMatch
    if loop.loop.flow != self.flow or loop.flow.dst != self.nextpos:
        raise PythonError("mismatched for loop")
    return [WantFlow(loop.flow)]

# new for loop

@_visitor(OpcodeGetIter, Expr)
def visit_get_iter(self, deco, expr):
    return [Iter(expr)]

@_visitor(OpcodeForIter, Iter, Loop)
def _visit_for_iter(self, deco, iter_, loop):
    return [ForStart(iter_.expr, loop, self.flow)]

# break

@_stmt_visitor(OpcodeBreakLoop)
def _visit_break(self, deco):
    return StmtBreak(), []

# access

@_stmt_visitor(OpcodeAccessMode, ExprInt)
def _visit_access(self, deco, mode):
    return StmtAccess(self.param, mode.val), []

# try finally

@_visitor(OpcodeSetupFinally)
def _visit_setup_finally(self, deco):
    return [SetupFinally(self.flow), Block([])]

@_visitor(OpcodePopBlock, SetupFinally, Block)
def _visit_finally_pop(self, deco, setup, block):
    return [TryFinallyPending(block, setup.flow)]

@_visitor(Flow, TryFinallyPending, ExprNone)
def _visit_finally(self, deco, try_, _):
    if try_.flow != self:
        raise PythonError("funny finally")
    return [TryFinally(try_.body), Block([])]

@_stmt_visitor(OpcodeEndFinally, TryFinally, Block)
def _visit_finally_end(self, deco, try_, inner):
    return StmtFinally(try_.body, inner), []

# try except

# start try except - store address of except clause

@_visitor(OpcodeSetupExcept)
def _visit_setup_except(self, deco):
    return [SetupExcept(self.flow), Block([])]

# finish try clause - pop block & jump to else clause, start except clause

@_visitor(OpcodePopBlock, SetupExcept, Block)
def _visit_except_pop_try(self, deco, setup, block):
    return [TryExceptEndTry(setup.flow, block)]

@_visitor(OpcodeJumpForward, TryExceptEndTry)
def _visit_except_end_try(self, deco, try_):
    return [TryExceptMid(self.flow, try_.body, [], None, []), WantFlow(try_.flow)]

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
    if self.mode != CmpOp.EXC_MATCH:
        raise PythonError("funny except match")
    return [try_, TryExceptMatchMid(expr)]

@_visitor(OpcodeJumpIfFalse, TryExceptMatchMid)
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

@_visitor(OpcodeJumpForward, TryExceptMid, TryExceptMatch, Block)
def _visit_except_match_end(self, deco, try_, match, block):
    return [
        TryExceptMid(
            try_.else_,
            try_.body,
            try_.items + [(match.expr, match.dst, block)],
            None,
            try_.flows + [self.flow]
        ),
        WantPop(),
        WantFlow(match.next)
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

@_visitor(OpcodeJumpForward, TryExceptMid, TryExceptAny, Block)
def _visit_except_any_end(self, deco, try_, _, block):
    return [
        TryExceptMid(
            try_.else_,
            try_.body,
            try_.items,
            block,
            try_.flows + [self.flow]
        )
    ]

@_visitor(OpcodeEndFinally, TryExceptMid)
def _visit_except_end(self, deco, try_):
    return [
        TryExceptElse(try_.body, try_.items, try_.any, try_.flows),
        Block([]),
        WantFlow(try_.else_)
    ]

@_stmt_visitor(Flow, TryExceptElse, Block)
def _visit_except_end(self, deco, try_, block):
    if self != try_.flows[-1]:
        raise NoMatch
    return StmtExcept(try_.body, try_.items, try_.any, block), [
        WantFlow(flow) for flow in try_.flows[:-1]
    ]

# functions & classes

# make function - py 1.0 - 1.2

@_visitor(OpcodeBuildFunction, Code)
def _visit_build_function(self, deco, code):
    return [ExprFunctionRaw(deco_code(code), [], [])]

@_visitor(OpcodeSetFuncArgs, ExprTuple, ExprFunctionRaw)
def _visit_set_func_args(self, deco, args, fun):
    # bug alert: def f(a, b=1) is compiled as def f(a=1, b)
    return [ExprFunctionRaw(fun.code, args.exprs, [])]

# make function - py 1.3+

@_visitor(OpcodeMakeFunction, Exprs('param', 1), Code)
def _visit_make_function(self, deco, args, code):
    return [ExprFunctionRaw(deco_code(code), args, [])]

@_visitor(OpcodeBuildTuple, Closures)
def visit_closure_tuple(self, deco, closures):
    return [ClosuresTuple([closure.var for closure in closures])]

@_visitor(OpcodeMakeClosure, UglyClosures, Exprs('param', 1), Code, flag='!has_sane_closure')
def _visit_make_function(self, deco, closures, args, code):
    return [ExprFunctionRaw(deco_code(code), args, closures)]

@_visitor(OpcodeMakeClosure, ClosuresTuple, Exprs('param', 1), Code, flag='has_sane_closure')
def _visit_make_function(self, deco, closures, args, code):
    return [ExprFunctionRaw(deco_code(code), args, closures.vars)]

@_visitor(OpcodeUnaryCall, ExprFunctionRaw)
def _visit_unary_call(self, deco, fun):
    if fun.defargs:
        raise PythonError("class call with a function with default arguments")
    return [UnaryCall(fun.code)]

@_visitor(OpcodeLoadClosure)
def visit_load_closure(self, deco):
    return [Closure(deco.deref(self.param))]

@_visitor(OpcodeBuildClass, Expr, ExprTuple, UnaryCall)
def _visit_build_class(self, deco, name, expr, call):
    return [ExprClassRaw(deco.string(name), expr.exprs, call.code)]

@_visitor(OpcodeBuildClass, Expr, ExprTuple, ExprCall, flag='has_new_code')
def _visit_build_class(self, deco, name, expr, call):
    if call.params:
        raise PythonError("class call with params")
    fun = call.expr
    if not isinstance(fun, ExprFunctionRaw):
        raise PythonError("class call with non-function")
    if fun.closures:
        raise PythonError("class call with a function with closures")
    if fun.defargs:
        raise PythonError("class call with a function with default arguments")
    return [ExprClassRaw(deco.string(name), expr.exprs, fun.code)]

@_visitor(OpcodeLoadLocals)
def _visit_load_locals(self, deco):
    return [Locals()]

@_stmt_visitor(OpcodeReturnValue, Locals)
def _visit_return_locals(self, deco, _):
    return StmtEndClass(), []

@_visitor(OpcodeReserveFast)
def _visit_reserve_fast(self, deco):
    if deco.varnames is not None:
        raise PythonError("duplicate RESERVE_FAST")

    deco.varnames = self.names
    return []

# inplace assignments

INPLACE_OPS = [
    (OpcodeInplaceAdd, StmtInplaceAdd),
    (OpcodeInplaceSubstract, StmtInplaceSubstract),
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
    @_visitor(op, ExprName, Expr)
    def _visit_inplace_name(self, deco, name, src, stmt=stmt):
        return [InplaceName(name.name, src, stmt)]

    @_visitor(op, ExprGlobal, Expr)
    def _visit_inplace_global(self, deco, name, src, stmt=stmt):
        return [InplaceGlobal(name.name, src, stmt)]

    @_visitor(op, ExprFast, Expr)
    def _visit_inplace_fast(self, deco, fast, src, stmt=stmt):
        return [InplaceFast(fast.idx, src, stmt)]

    @_visitor(op, ExprDeref, Expr)
    def _visit_inplace_deref(self, deco, deref, src, stmt=stmt):
        return [InplaceDeref(deref.idx, src, stmt)]

    @_visitor(op, DupAttr, Expr)
    def _visit_inplace_attr(self, deco, dup, src, stmt=stmt):
        return [InplaceAttr(dup.expr, dup.name, src, stmt)]

    @_visitor(op, DupSubscr, Expr)
    def _visit_inplace_subscr(self, deco, dup, src, stmt=stmt):
        return [InplaceSubscr(dup.expr, dup.index, src, stmt)]

    @_visitor(op, DupSliceNN, Expr)
    def _visit_inplace_slice_nn(self, deco, dup, src, stmt=stmt):
        return [InplaceSliceNN(dup.expr, src, stmt)]

    @_visitor(op, DupSliceEN, Expr)
    def _visit_inplace_slice_en(self, deco, dup, src, stmt=stmt):
        return [InplaceSliceEN(dup.expr, dup.start, src, stmt)]

    @_visitor(op, DupSliceNE, Expr)
    def _visit_inplace_slice_ne(self, deco, dup, src, stmt=stmt):
        return [InplaceSliceNE(dup.expr, dup.end, src, stmt)]

    @_visitor(op, DupSliceEE, Expr)
    def _visit_inplace_slice_ee(self, deco, dup, src, stmt=stmt):
        return [InplaceSliceEE(dup.expr, dup.start, dup.end, src, stmt)]

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

@_stmt_visitor(OpcodeStoreName, InplaceName)
def _visit_inplace_store_name(self, deco, inp):
    if inp.name != self.param:
        raise PythonError("inplace name mismatch")
    return inp.stmt(ExprName(inp.name), inp.src), []

@_stmt_visitor(OpcodeStoreGlobal, InplaceGlobal)
def _visit_inplace_store_global(self, deco, inp):
    if inp.name != self.param:
        raise PythonError("inplace name mismatch")
    return inp.stmt(ExprGlobal(inp.name), inp.src), []

@_stmt_visitor(OpcodeStoreFast, InplaceFast)
def _visit_inplace_store_fast(self, deco, inp):
    if inp.idx != self.param:
        raise PythonError("inplace name mismatch")
    return inp.stmt(deco.fast(inp.idx), inp.src), []

@_stmt_visitor(OpcodeStoreDeref, InplaceDeref)
def _visit_inplace_store_deref(self, deco, inp):
    if inp.idx != self.param:
        raise PythonError("inplace name mismatch")
    return inp.stmt(deco.deref(inp.idx), inp.src), []

@_stmt_visitor(OpcodeStoreAttr, InplaceAttr, RotTwo)
def _visit_inplace_store_attr(self, deco, inp, _):
    if inp.name != self.param:
        raise PythonError("inplace name mismatch")
    return inp.stmt(ExprAttr(inp.expr, inp.name), inp.src), []

@_stmt_visitor(OpcodeStoreSubscr, InplaceSubscr, RotThree)
def _visit_inplace_store_subscr(self, deco, inp, _rot):
    return inp.stmt(ExprSubscr(inp.expr, inp.index), inp.src), []

@_stmt_visitor(OpcodeStoreSliceNN, InplaceSliceNN, RotTwo)
def _visit_inplace_store_slice_nn(self, deco, inp, _rot):
    return inp.stmt(ExprSubscr(inp.expr, ExprSlice(None, None)), inp.src), []

@_stmt_visitor(OpcodeStoreSliceEN, InplaceSliceEN, RotThree)
def _visit_inplace_store_slice_en(self, deco, inp, _rot):
    return inp.stmt(ExprSubscr(inp.expr, ExprSlice(inp.start, None)), inp.src), []

@_stmt_visitor(OpcodeStoreSliceNE, InplaceSliceNE, RotThree)
def _visit_inplace_store_slice_ne(self, deco, inp, _rot):
    return inp.stmt(ExprSubscr(inp.expr, ExprSlice(None, inp.end)), inp.src), []

@_stmt_visitor(OpcodeStoreSliceEE, InplaceSliceEE, RotFour)
def _visit_inplace_store_slice_ee(self, deco, inp, _rot):
    return inp.stmt(ExprSubscr(inp.expr, ExprSlice(inp.start, inp.end)), inp.src), []

# list comprehensions

@_visitor(OpcodeStoreName, DupAttr, flag='!has_list_append')
def visit_listcomp_start(self, deco, dup):
    if (not isinstance(dup.expr, ExprList)
        or len(dup.expr.exprs) != 0
        or dup.name != 'append'):
        raise PythonError("weird listcomp start")
    expr = ExprListComp()
    meat = OldListCompStart(expr, ExprName(self.param))
    return [expr, meat, CompLevel(meat, [])]

# you have to go out of your way to hit that one.
@_visitor(OpcodeStoreGlobal, DupAttr, flag='has_listcomp_collide')
def visit_listcomp_start(self, deco, dup):
    if (not isinstance(dup.expr, ExprList)
        or len(dup.expr.exprs) != 0
        or dup.name != 'append'):
        raise PythonError("weird listcomp start")
    expr = ExprListComp()
    meat = OldListCompStart(expr, ExprGlobal(self.param))
    return [expr, meat, CompLevel(meat, [])]

@_visitor(OpcodeStoreFast, DupAttr, flag='!has_list_append')
def visit_listcomp_start(self, deco, dup):
    if (not isinstance(dup.expr, ExprList)
        or len(dup.expr.exprs) != 0
        or dup.name != 'append'):
        raise PythonError("weird listcomp start")
    expr = ExprListComp()
    meat = OldListCompStart(expr, deco.fast(self.param))
    return [expr, meat, CompLevel(meat, [])]

@_visitor(OpcodePopTop, CompLevel, ExprCall, flag='!has_list_append')
def visit_listcomp_item(self, deco, comp, call):
    if not isinstance(comp.meat, OldListCompStart):
        raise PythonError("not an old list comp...")
    if comp.meat.tmp != call.expr:
        raise PythonError("list.append temp doesn't match")
    if len(call.params) != 1 or call.params[0][0] != '':
        raise PythonError("funny args to list.append")
    arg = call.params[0][1]
    comp.meat.expr.comp = Comp(arg, comp.items)
    return []

@_visitor(OpcodeListAppend, CompLevel, Expr, Expr, flag='has_list_append')
def visit_listcomp_item(self, deco, comp, tmp, val):
    if not isinstance(comp.meat, OldListCompStart):
        raise PythonError("not an old list comp...")
    if comp.meat.tmp != tmp:
        raise PythonError("list.append temp doesn't match")
    comp.meat.expr.comp = Comp(val, comp.items)
    return []

@_visitor(OpcodeDeleteName, OldListCompStart)
def visit_listcomp_end(self, deco, comp):
    if comp.tmp != ExprName(self.param):
        raise PythonError("deleting a funny name")
    return []

@_visitor(OpcodeDeleteGlobal, OldListCompStart)
def visit_listcomp_end(self, deco, comp):
    if comp.tmp != ExprGlobal(self.param):
        raise PythonError("deleting a funny name")
    return []

@_visitor(OpcodeDeleteFast, OldListCompStart)
def visit_listcomp_end(self, deco, comp):
    if comp.tmp != deco.fast(self.param):
        raise PythonError("deleting a funny name")
    return []

# yield

@_stmt_visitor(OpcodeYieldValue, Expr, flag='!has_yield_expr')
def _visit_yield_stmt(self, deco, expr):
    return StmtSingle(ExprYield(expr)), []

@_visitor(OpcodeYieldValue, Expr, flag='has_yield_expr')
def _visit_yield_stmt(self, deco, expr):
    return [ExprYield(expr)]


class DecoCtx:
    def __init__(self, code):
        self.version = code.version
        self.stack = [Block([])]
        self.bytecode = code.code
        self.code = code
        self.lineno = None
        if self.version.has_new_code:
            self.varnames = code.varnames
        else:
            self.varnames = None
        for op in self.bytecode.ops:
            flows = [Flow(inflow, op.pos) for inflow in reversed(op.inflow)]
            while flows:
                for idx, flow in enumerate(flows):
                    try:
                        self.process(flow)
                    except NoMatch:
                        continue
                    flows.pop(idx)
                    break
                else:
                    raise PythonError("no visitors matched for {}, [{}]".format(
                        ', '.join(str(flow) for flow in flows),
                        ', '.join(type(x).__name__ for x in self.stack)
                    ))
            try:
                self.process(op)
            except NoMatch:
                raise PythonError("no visitors matched: {}, [{}]".format(
                    type(op).__name__,
                    ', '.join(type(x).__name__ for x in self.stack)
                ))
        if len(self.stack) != 1:
            raise PythonError("stack non-empty at the end")
        if not isinstance(self.stack[0], Block):
            raise PythonError("weirdness on stack at the end")
        self.res = DecoCode(self.stack[0], code, self.varnames)

    def process(self, op):
        for visitor in _VISITORS.get(type(op), []):
            if visitor.visit(op, self):
                break
        else:
            raise NoMatch

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
                raise PythonError("wanted a string")
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
