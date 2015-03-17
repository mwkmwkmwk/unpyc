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
# - access prettyprint modes
# - make a test suite
# - find a way to print nested code objects after stage 3
# - clean up import mess
# - make sure signed/unsigned numbers are right
# - py 1.3:
#
#   - tuple arguments
#
# - py 1.4:
#
#   - new slices
#   - mangling
#
# - py 1.5:
#
#   - assert
#
# - py 1.6:
#
#   - var calls
#   - unicode
#
# - py 2.0:
#
#   - inplace
#   - print to
#   - import star
#   - unpack sequence
#   - wide
#   - import as
#   - list comprehensions
#
# - py 2.1:
#
#   - closures
#   - proper continue
#   - future
#
# - py 2.2:
#
#   - floor/true divide
#   - iterator-based for
#   - generators
#
# - py 2.3:
#
#   - deal with optimizer
#   - encoding...
#   - SET_LINENO no more
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

Dup = namedtuple('Dup', ['expr'])
ABA = namedtuple('ABA', ['a', 'b'])
BAB = namedtuple('BAB', ['a', 'b'])
Import = namedtuple('Import', ['name'])
FromImport = namedtuple('FromImport', ['name', 'items'])
MultiAssign = namedtuple('MultiAssign', ['src', 'dsts'])
MultiAssignDup = namedtuple('MultiAssignDup', ['src', 'dsts'])
UnpackSlot = namedtuple('UnpackSlot', ['expr', 'idx'])
UnpackArgSlot = namedtuple('UnpackArgSlot', ['args', 'idx'])
UnpackVarargSlot = namedtuple('UnpackVarargSlot', ['args'])
JumpIfFalse = namedtuple('JumpIfFalse', ['expr', 'flow'])
JumpIfTrue = namedtuple('JumpIfTrue', ['expr', 'flow'])
IfStart = namedtuple('IfStart', ['expr', 'flow'])
IfElse = namedtuple('IfElse', ['expr', 'body', 'flow'])
OrStart = namedtuple('OrStart', ['expr', 'flow'])
CompareStart = namedtuple('CompareStart', ['items', 'flows'])
Compare = namedtuple('Compare', ['items', 'flows'])
CompareLast = namedtuple('CompareLast', ['items', 'flows'])
CompareNext = namedtuple('CompareNext', ['items', 'flows'])
CompareContinue = namedtuple('CompareContinue', ['items', 'flows', 'next'])
WantPop = namedtuple('WantPop', [])
WantPopBlock = namedtuple('WantPopBlock', [])
WantRotTwo = namedtuple('WantRotTwo', [])
WantFlow = namedtuple('WantFlow', ['flow'])
SetupLoop = namedtuple('SetupLoop', ['flow'])
SetupFinally = namedtuple('SetupFinally', ['flow'])
SetupExcept = namedtuple('SetupExcept', ['flow'])
Loop = namedtuple('Loop', ['flow', 'cont'])
While = namedtuple('While', ['expr', 'end', 'block'])
ForStart = namedtuple('ForStart', ['expr', 'loop', 'flow'])
ForLoop = namedtuple('ForLoop', ['expr', 'dst', 'loop', 'flow'])
TryFinallyPending = namedtuple('TryFinallyPending', ['body', 'flow'])
TryFinally = namedtuple('TryFinally', ['body'])
TryExceptEndTry = namedtuple('TryExceptEndTry', ['flow', 'body'])
TryExceptMid = namedtuple('TryExceptMid', ['else_', 'body', 'items', 'any', 'flows'])
TryExceptMatchStart = namedtuple('TryExceptMatchStart', [])
TryExceptMatchMid = namedtuple('TryExceptMatchMid', ['expr'])
TryExceptMatchOk = namedtuple('TryExceptMatchOk', ['expr', 'next'])
TryExceptMatch = namedtuple('TryExceptMatch', ['expr', 'dst', 'next'])
TryExceptAny = namedtuple('TryExceptAny', [])
TryExceptElse = namedtuple('TryExceptElse', ['body', 'items', 'any', 'flows'])
UnaryCall = namedtuple('UnaryCall', ['code'])
Locals = namedtuple('Locals', [])

# a special marker to put in stack want lists - will match getattr(opcode, attr)
# expressions and pass a list
Exprs = namedtuple('Exprs', ['attr', 'factor'])

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
        stack = deco.stack[:]
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
            else:
                arg = stack.pop()
                if not isinstance(arg, want):
                    return False
            args.append(arg)
        args.reverse()
        try:
            stack += self.func(opcode, deco, *args)
            deco.stack = stack
            return True
        except NoMatch:
            return False


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

        @_visitor(op, Block, Dup, *stack)
        def visit_store_multi_start(self, deco, block, dup, *args):
            dst, extra = func(self, deco, *args)
            return [block, MultiAssign(dup.expr, [dst])] + extra

        @_visitor(op, Block, MultiAssignDup, *stack)
        def visit_store_multi_next(self, deco, block, multidup, *args):
            dst, extra = func(self, deco, *args)
            multidup.dsts.append(dst)
            return [block, MultiAssign(multidup.src, multidup.dsts)] + extra

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

        @_visitor(op, ForStart, *stack)
        def visit_store_multi_start(self, deco, start, *args):
            dst, extra = func(self, deco, *args)
            return [
                ForLoop(start.expr, dst, start.loop, start.flow),
                Block([])
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
            dst, extra = func(self, deco, *args)
            return StmtImport(import_.name, dst), extra

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

@_visitor(OpcodeDupTop, Expr)
def visit_dup_top(self, deco, expr):
    return [Dup(expr)]

@_visitor(OpcodeDupTop, MultiAssign)
def visit_dup_top(self, deco, multi):
    return [MultiAssignDup(multi.src, multi.dsts)]

@_visitor(OpcodeRotTwo, Dup, Expr)
def visit_dup_top(self, deco, dup, expr):
    return [ABA(dup.expr, expr)]

@_visitor(OpcodeRotThree, Expr, Dup)
def visit_dup_top(self, deco, expr, dup):
    return [BAB(expr, dup.expr)]


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
    if self.param:
        raise PythonError("Non-zero param for BUILD_MAP")
    return [ExprDict([])]

@_visitor(OpcodeStoreSubscr, ABA, Expr)
def visit_build_map_step(self, deco, aba, expr):
    dict_ = aba.a
    if not isinstance(dict_, ExprDict):
        raise NoMatch
    dict_.items.append((expr, aba.b))
    return [dict_]

# expressions - function call

@_visitor(OpcodeBinaryCall, Expr, ExprTuple)
def visit_binary_call(self, deco, expr, params):
    return [ExprCall(expr, [('', arg) for arg in params.exprs])]

@_visitor(OpcodeCallFunction, Expr, Exprs('args', 1), Exprs('kwargs', 2))
def visit_call_function(self, deco, fun, args, kwargs):
    for name, arg in kwargs:
        if not isinstance(name, ExprString):
            raise PythonError("kwarg not a string")
    return [ExprCall(fun, [('', arg) for arg in args] + [(name.val.decode('ascii'), arg) for name, arg in kwargs])]

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
    if deco.varnames is None:
        raise PythonError("no fast variables")
    if self.param not in range(len(deco.varnames)):
        raise PythonError("fast var out of range")
    return ExprFast(self.param, deco.varnames[self.param])

@_lsd_visitor(OpcodeLoadAttr, OpcodeStoreAttr, OpcodeDeleteAttr, Expr)
def visit_store_attr(self, deco, expr):
    return ExprAttr(expr, self.param)

@_lsd_visitor(OpcodeBinarySubscr, OpcodeStoreSubscr, OpcodeDeleteSubscr, Expr, Expr)
def visit_store_subscr(self, deco, expr, idx):
    return ExprSubscr(expr, idx)

@_lsd_visitor(OpcodeSliceNN, OpcodeStoreSliceNN, OpcodeDeleteSliceNN, Expr)
def visit_store_slice_nn(self, deco, expr):
    return ExprSlice(expr, None, None)

@_lsd_visitor(OpcodeSliceEN, OpcodeStoreSliceEN, OpcodeDeleteSliceEN, Expr, Expr)
def visit_store_slice_en(self, deco, expr, start):
    return ExprSlice(expr, start, None)

@_lsd_visitor(OpcodeSliceNE, OpcodeStoreSliceNE, OpcodeDeleteSliceNE, Expr, Expr)
def visit_store_slice_ne(self, deco, expr, end):
    return ExprSlice(expr, None, end)

@_lsd_visitor(OpcodeSliceEE, OpcodeStoreSliceEE, OpcodeDeleteSliceEE, Expr, Expr, Expr)
def visit_store_slice_ee(self, deco, expr, start, end):
    return ExprSlice(expr, start, end)

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

# Python 1.3+
@_stmt_visitor(OpcodeRaiseVarargs, Exprs('param', 1))
def _visit_raise_varargs(self, deco, exprs):
    if len(exprs) > 3:
        raise PythonError("too many args to raise")
    if len(exprs) == 0 and not deco.version.has_reraise:
        raise PythonError("too few args to raise")
    return StmtRaise(*exprs), []

# exec statement

@_stmt_visitor(OpcodeExecStmt, Expr, Dup)
def _visit_exec_3(self, deco, code, dup):
    if isinstance(dup.expr, ExprNone):
        return StmtExec(code), []
    else:
        return StmtExec(code, dup.expr), []

@_stmt_visitor(OpcodeExecStmt, Expr, Expr, Expr)
def _visit_exec_3(self, deco, code, globals, locals):
    return StmtExec(code, globals, locals), []

# imports

@_visitor(OpcodeImportName)
def _visit_import_name(self, deco):
    return [Import(self.param)]

@_visitor(OpcodeImportFrom, Import)
def _visit_import_from_first(self, deco, import_):
    return [FromImport(import_.name, [self.param])]

@_visitor(OpcodeImportFrom, FromImport)
def _visit_import_from_next(self, deco, from_import):
    from_import.items.append(self.param)
    return [from_import]

@_stmt_visitor(OpcodePopTop, FromImport)
def _visit_import_from_end(self, deco, from_import):
    return StmtFromImport(from_import.name, from_import.items), []

# if

@_visitor(OpcodeJumpIfFalse, Expr)
def _visit_jump_if_false(self, deco, expr):
    return [JumpIfFalse(expr, self.flow)]

@_visitor(OpcodeJumpIfTrue, Expr)
def _visit_jump_if_false(self, deco, expr):
    return [JumpIfTrue(expr, self.flow)]

@_visitor(OpcodePopTop, JumpIfFalse)
def _visit_if(self, deco, jump):
    return [IfStart(jump.expr, jump.flow), Block([])]

@_visitor(OpcodePopTop, JumpIfTrue)
def _visit_if(self, deco, jump):
    return [OrStart(jump.expr, jump.flow)]

@_visitor(OpcodeJumpForward, IfStart, Block)
def _visit_if_else(self, deco, if_, block):
    if if_.flow.dst != self.nextpos:
        raise PythonError("missing if code")
    return [IfElse(if_.expr, block, self.flow), Block([]), WantPop(), WantFlow(if_.flow)]

@_visitor(Flow, WantFlow)
def _visit_flow(self, deco, want):
    if self != want.flow:
        raise NoMatch
    return []

@_visitor(OpcodePopTop, WantPop)
def _visit_want_pop(self, deco, want):
    return []

@_visitor(OpcodePopBlock, WantPopBlock)
def _visit_want_pop_block(self, deco, want):
    return []

@_visitor(OpcodeRotTwo, WantRotTwo)
def _visit_want_rot_two(self, deco, want):
    return []

@_stmt_visitor(Flow, IfElse, Block)
def _visit_if_end(self, deco, if_, inner):
    if self != if_.flow:
        raise PythonError("mismatch else flow")
    return StmtIf([(if_.expr, if_.body)], inner), []

@_visitor(Flow, IfStart, Block, Expr)
def _visit_and(self, deco, start, block, expr):
    if self != start.flow:
        raise PythonError("funny and flow")
    if block.stmts:
        raise PythonError("extra and statements")
    return [ExprBoolAnd(start.expr, expr)]

@_visitor(Flow, OrStart, Expr)
def _visit_or(self, deco, start, expr):
    if self != start.flow:
        raise PythonError("funny or flow")
    return [ExprBoolOr(start.expr, expr)]

# comparisons

@_visitor(OpcodeCompareOp, Expr, Expr)
def _visit_cmp(self, deco, e1, e2):
    if self.mode is CmpOp.EXC_MATCH:
        raise NoMatch
    return [ExprCmp([e1, self.mode, e2])]

# chained comparisons

# start #1
@_visitor(OpcodeCompareOp, BAB)
def _visit_cmp_start(self, deco, bab):
    if self.mode is CmpOp.EXC_MATCH:
        raise NoMatch
    return [CompareStart([bab.a, self.mode, bab.b], [])]

# start #2 and middle #3
@_visitor(OpcodeJumpIfFalse, CompareStart)
def _visit_cmp_jump(self, deco, cmp):
    return [Compare(cmp.items, cmp.flows + [self.flow]), WantPop()]

# middle #1
@_visitor(OpcodeRotThree, Compare, Dup)
def _visit_cmp_rot(self, deco, cmp, dup):
    return [CompareContinue(cmp.items, cmp.flows, dup.expr)]

# middle #2
@_visitor(OpcodeCompareOp, CompareContinue)
def _visit_cmp_next(self, deco, cmp):
    if self.mode is CmpOp.EXC_MATCH:
        raise NoMatch
    return [CompareStart(cmp.items + [self.mode, cmp.next], cmp.flows)]

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
        WantPop(),
        WantRotTwo()
    ] + [WantFlow(flow) for flow in cmp.flows]

# $loop framing

@_visitor(OpcodeSetupLoop)
def _visit_setup_loop(self, deco):
    return [SetupLoop(self.flow), Block([])]

@_stmt_visitor(Flow, SetupLoop, Block)
def _visit_end_loop(self, deco, loop, inner):
    if self != loop.flow:
        raise NoMatch
    return StmtLoop(inner), []

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
        elif isinstance(item, (Block, IfStart, IfElse, TryExceptMid, TryExceptMatch, TryExceptAny, TryExceptElse)):
            pass
        else:
            raise NoMatch
    if not loop.cont:
        raise NoMatch
    if loop.cont[-1] != self.flow:
        raise NoMatch
    loop.cont.pop()
    return StmtContinue(), []

# while loop

@_stmt_visitor(OpcodeJumpAbsolute, Loop, IfStart, Block)
def _visit_while(self, deco, loop, start, inner):
    if loop.cont:
        raise NoMatch
    # TODO validate flow
    if loop.flow != self.flow or start.flow.dst != self.nextpos:
        raise PythonError("funny while loop")
    return StmtWhileRaw(start.expr, inner), [WantPopBlock(), WantPop(), WantFlow(start.flow)]

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
    return StmtForRaw(loop.expr, loop.dst, inner), [WantPopBlock(), WantFlow(loop.flow)]

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

@_visitor(OpcodeDupTop, TryExceptMid)
def _visit_except_match_start(self, deco, try_):
    if try_.any:
        raise PythonError("making an except match after blanket")
    return [try_, TryExceptMatchStart()]

@_visitor(OpcodeCompareOp, TryExceptMatchStart, Expr)
def _visit_except_match_check(self, deco, start, expr):
    if self.mode != CmpOp.EXC_MATCH:
        raise PythonError("funny except match")
    return [TryExceptMatchMid(expr)]

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
    return [ExprFunctionRaw(deco_code(code), [])]

@_visitor(OpcodeSetFuncArgs, ExprTuple, ExprFunctionRaw)
def _visit_set_func_args(self, deco, args, fun):
    # bug alert: def f(a, b=1) is compiled as def f(a=1, b)
    return [ExprFunctionRaw(fun.code, args.exprs)]

# make function - py 1.3+

@_visitor(OpcodeMakeFunction, Exprs('param', 1), Code)
def _visit_make_function(self, deco, args, code):
    return [ExprFunctionRaw(deco_code(code), args)]

@_visitor(OpcodeUnaryCall, ExprFunctionRaw)
def _visit_unary_call(self, deco, fun):
    if fun.defargs:
        raise PythonError("class call with a function with default arguments")
    return [UnaryCall(fun.code)]

@_visitor(OpcodeBuildClass, ExprString, ExprTuple, UnaryCall)
def _visit_build_class(self, deco, name, expr, call):
    return [ExprClassRaw(name.val.decode('ascii'), expr.exprs, call.code)]

@_visitor(OpcodeBuildClass, ExprString, ExprTuple, ExprCall, flag='has_new_code')
def _visit_build_class(self, deco, name, expr, call):
    if call.params:
        raise PythonError("class call with params")
    fun = call.expr
    if not isinstance(fun, ExprFunctionRaw):
        raise PythonError("class call with non-function")
    if fun.defargs:
        raise PythonError("class call with a function with default arguments")
    return [ExprClassRaw(name.val.decode('ascii'), expr.exprs, fun.code)]

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


class DecoCtx:
    def __init__(self, code):
        self.version = code.version
        self.stack = [Block([])]
        self.bytecode = code.code
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
