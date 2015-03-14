from collections import namedtuple

from .helpers import PythonError
from .stmt import *
from .expr import *
from .bytecode import *

# TODO:
#
# - validate inflows
# - nuke version from exprs
# - clean expr
# - clean up the stack item mess
# - contexts for expressions dammit
# - access
# - try except
# - figure out function/class descend
# - simplify if
# - do something about fast
# - class body decompilation
# - function body decompilation
# - lambda body decompilation
# - bump as many versions as easily possible
# - figure out what to do about line numbers
#
# and for prettifier:
#
# - punt exec/raise None detection?
# - merge print statements
# - merge import statements
# - deal with name types
# - create elifs
# - get rid of $loop [XXX: or move it?]
# - decide same/different line
# - get rid of return None
# - stuff 'global' somewhere

# dummy opcode for inflow

Inflow = namedtuple('Inflow', ['src', 'dst'])

# funny intermediate stuff to put on stack

Dup = namedtuple('Dup', ['expr'])
ABA = namedtuple('ABA', ['a', 'b'])
BAB = namedtuple('ABA', ['a', 'b'])
Import = namedtuple('Import', ['name'])
FromImport = namedtuple('FromImport', ['name', 'items'])
MultiAssign = namedtuple('MultiAssign', ['src', 'dsts'])
MultiAssignDup = namedtuple('MultiAssignDup', ['src', 'dsts'])
UnpackSlot = namedtuple('UnpackSlot', ['expr', 'idx'])
JumpIfFalse = namedtuple('JumpIfFalse', ['expr', 'target'])
JumpIfTrue = namedtuple('JumpIfTrue', ['expr', 'target'])
IfStart = namedtuple('IfStart', ['expr', 'target'])
If = namedtuple('If', ['items', 'end'])
OrStart = namedtuple('OrStart', ['expr', 'target'])
CompareStart = namedtuple('CompareStart', ['items'])
Compare = namedtuple('Compare', ['items', 'target'])
CompareLast = namedtuple('CompareLast', ['items', 'target'])
CompareNext = namedtuple('CompareNext', ['items', 'target'])
CompareContinue = namedtuple('CompareContinue', ['items', 'target', 'next'])
WantPop = namedtuple('WantPop', [])
WantPopBlock = namedtuple('WantPopBlock', [])
WantRotTwo = namedtuple('WantRotTwo', [])
WantInflow = namedtuple('WantInflow', [])
SetupLoop = namedtuple('SetupLoop', ['end'])
SetupFinally = namedtuple('SetupFinally', ['pos', 'end'])
Loop = namedtuple('Loop', ['src', 'dst'])
While = namedtuple('While', ['expr', 'end', 'block'])
ForStart = namedtuple('ForStart', ['expr', 'loop', 'end'])
ForLoop = namedtuple('ForLoop', ['expr', 'dst', 'loop', 'end'])
TryFinallyPending = namedtuple('TryFinallyPending', ['body', 'pos', 'end'])
TryFinally = namedtuple('TryFinally', ['body'])

# visitors

class NoMatch(Exception):
    pass

_VISITORS = {}

class _Visitor:
    __slots__ = 'func', 'stack'

    def __init__(self, func, stack):
        self.func = func
        self.stack = stack

    def visit(self, opcode, deco):
        if len(deco.stack) < len(self.stack):
            return False
        current = deco.stack[-len(self.stack):] if self.stack else []
        for have, want in zip(current, self.stack):
            if not isinstance(have, want):
                return False
        try:
            res = self.func(opcode, deco, *current)
        except NoMatch:
            return False
        for _ in current:
            deco.stack.pop()
        deco.stack.extend(res)
        return True


def _visitor(op, *stack):
    def inner(func):
        _VISITORS.setdefault(op, []).append(_Visitor(func, stack))
        return func
    return inner

def _stmt_visitor(op, *stack):
    def inner(func):
        @_visitor(op, Block, *stack)
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
            return StmtAssign(deco.version, [dst], src), extra

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
            stmt = StmtAssign(deco.version, multi.dsts, multi.src)
            return stmt, extra

        @_visitor(op, UnpackSlot, *stack)
        def visit_store_multi_start(self, deco, slot, *args):
            dst, extra = func(self, deco, *args)
            slot.expr.exprs[slot.idx] = dst
            return extra

        @_visitor(op, ForStart, *stack)
        def visit_store_multi_start(self, deco, start, *args):
            dst, extra = func(self, deco, *args)
            return [ForLoop(start.expr, dst, start.loop, start.end), Block([])] + extra

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
            return StmtDel(deco.version, dst), []

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
        return [etype(deco.version, expr)]

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
        return [etype(deco.version, expr1, expr2)]

for otype, etype in {
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

@_visitor(OpcodeBuildTuple)
@_visitor(OpcodeBuildList)
def visit_build_tuple(self, deco):
    if len(deco.stack) < self.param:
        raise NoMatch
    for i in range(-self.param, 0):
        if not isinstance(deco.stack[i], Expr):
            raise NoMatch
    if isinstance(self, OpcodeBuildTuple):
        typ = ExprTuple
    elif isinstance(self, OpcodeBuildList):
        typ = ExprList
    else:
        assert False
    if self.param:
        res = typ(deco.version, deco.stack[-self.param:])
        for i in range(self.param):
            deco.stack.pop()
        return [res]
    else:
        return [typ(deco.version, [])]

@_visitor(OpcodeBuildMap)
def visit_build_map(self, deco):
    if self.param:
        raise PythonError("Non-zero param for BUILD_MAP")
    return [ExprDict(deco.version, [])]

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
    return [ExprCall(deco.version, expr, params.exprs)]

# expressions - load const

@_visitor(OpcodeLoadConst)
def visit_load_const(self, deco):
    return [self.const]

# expressions - storable

@_lsd_visitor(OpcodeLoadName, OpcodeStoreName, OpcodeDeleteName)
def visit_store_name(self, deco):
    return ExprName(deco.version, self.param)

@_lsd_visitor(OpcodeLoadAttr, OpcodeStoreAttr, OpcodeDeleteAttr, Expr)
def visit_store_attr(self, deco, expr):
    return ExprAttr(deco.version, expr, self.param)

@_lsd_visitor(OpcodeBinarySubscr, OpcodeStoreSubscr, OpcodeDeleteSubscr, Expr, Expr)
def visit_store_subscr(self, deco, expr, idx):
    return ExprSubscr(deco.version, expr, idx)

@_lsd_visitor(OpcodeSliceNN, OpcodeStoreSliceNN, OpcodeDeleteSliceNN, Expr)
def visit_store_slice_nn(self, deco, expr):
    return ExprSlice(deco.version, expr, None, None)

@_lsd_visitor(OpcodeSliceEN, OpcodeStoreSliceEN, OpcodeDeleteSliceEN, Expr, Expr)
def visit_store_slice_en(self, deco, expr, start):
    return ExprSlice(deco.version, expr, start, None)

@_lsd_visitor(OpcodeSliceNE, OpcodeStoreSliceNE, OpcodeDeleteSliceNE, Expr, Expr)
def visit_store_slice_ne(self, deco, expr, end):
    return ExprSlice(deco.version, expr, None, end)

@_lsd_visitor(OpcodeSliceEE, OpcodeStoreSliceEE, OpcodeDeleteSliceEE, Expr, Expr, Expr)
def visit_store_slice_ee(self, deco, expr, start, end):
    return ExprSlice(deco.version, expr, start, end)

# list & tuple unpacking

@_store_visitor(OpcodeUnpackTuple)
def visit_unpack_tuple(self, deco):
    res = ExprTuple(deco.version, [None for _ in range(self.param)])
    extra = [UnpackSlot(res, idx) for idx in reversed(range(self.param))]
    return res, extra

@_store_visitor(OpcodeUnpackList)
def visit_unpack_list(self, deco):
    res = ExprList(deco.version, [None for _ in range(self.param)])
    extra = [UnpackSlot(res, idx) for idx in reversed(range(self.param))]
    return res, extra

# single expression statement

@_stmt_visitor(OpcodePrintExpr, Expr)
def _visit_print_expr(self, deco, expr):
    return StmtSingle(deco.version, expr), []

# print statement

@_stmt_visitor(OpcodePrintItem, Expr)
def visit_print_item(self, deco, expr):
    return StmtPrint(deco.version, [expr], False), []

@_stmt_visitor(OpcodePrintNewline)
def visit_print_newline(self, deco):
    return StmtPrint(deco.version, [], True), []

# return statement

@_stmt_visitor(OpcodeReturnValue, Expr)
def _visit_return(self, deco, expr):
    return StmtReturn(deco.version, expr), []

# raise statement

@_stmt_visitor(OpcodeRaise, Expr, ExprNone)
def _visit_raise_1(self, deco, cls, _):
    return StmtRaise(deco.version, cls), []

@_stmt_visitor(OpcodeRaise, Expr, Expr)
def _visit_raise_2(self, deco, cls, val):
    return StmtRaise(deco.version, cls, val), []

# exec statement

@_stmt_visitor(OpcodeExecStmt, Expr, Dup)
def _visit_exec_3(self, deco, code, dup):
    if isinstance(dup.expr, ExprNone):
        return StmtExec(deco.version, code), []
    else:
        return StmtExec(deco.version, code, dup.expr), []

@_stmt_visitor(OpcodeExecStmt, Expr, Expr, Expr)
def _visit_exec_3(self, deco, code, globals, locals):
    return StmtExec(deco.version, code, globals, locals), []

# imports

@_visitor(OpcodeImportName)
def _visit_import_name(self, deco):
    return [Import(self.param)]

@_stmt_visitor(OpcodeStoreName, Import)
def _visit_store_name_import(self, deco, import_):
    return StmtImport(deco.version, import_.name), []

@_visitor(OpcodeImportFrom, Import)
def _visit_import_from_first(self, deco, import_):
    return [FromImport(import_.name, [self.param])]

@_visitor(OpcodeImportFrom, FromImport)
def _visit_import_from_next(self, deco, from_import):
    from_import.items.append(self.param)
    return [from_import]

@_stmt_visitor(OpcodePopTop, FromImport)
def _visit_import_from_end(self, deco, from_import):
    return StmtFromImport(deco.version, from_import.name, from_import.items), []

# if

@_visitor(OpcodeJumpIfFalse, Expr)
def _visit_jump_if_false(self, deco, expr):
    return [JumpIfFalse(expr, self.target)]

@_visitor(OpcodeJumpIfTrue, Expr)
def _visit_jump_if_false(self, deco, expr):
    return [JumpIfTrue(expr, self.target)]

@_visitor(OpcodePopTop, JumpIfFalse)
def _visit_if(self, deco, jump):
    return [IfStart(jump.expr, jump.target), Block([])]

@_visitor(OpcodePopTop, JumpIfTrue)
def _visit_if(self, deco, jump):
    return [OrStart(jump.expr, jump.target)]

@_visitor(OpcodeJumpForward, IfStart, Block)
def _visit_if_else(self, deco, if_, block):
    if if_.target != self.nextpos:
        raise PythonError("missing if code")
    return [If([(if_.expr, block)], self.target), Block([]), WantPop(), WantInflow()]

@_visitor(Inflow, WantInflow)
def _visit_inflow(self, deco, want):
    # TODO validate inflow
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

@_stmt_visitor(Inflow, If, Block)
def _visit_if_end(self, deco, if_, inner):
    # TODO validate inflow
    return StmtIf(if_.items, inner), []

@_visitor(Inflow, IfStart, Block, Expr)
def _visit_and(self, deco, if_, block, expr):
    # TODO validate inflow
    if block.stmts:
        raise PythonError("extra and statements")
    return [ExprBoolAnd(deco.version, if_.expr, expr)]

@_visitor(Inflow, OrStart, Expr)
def _visit_or(self, deco, if_, expr):
    # TODO validate inflow
    return [ExprBoolOr(deco.version, if_.expr, expr)]

# comparisons

@_visitor(OpcodeCompareOp, Expr, Expr)
def _visit_cmp(self, deco, e1, e2):
    if self.mode is CmpOp.EXC_MATCH:
        raise NoMatch
    return [ExprCmp(deco.version, [e1, self.mode, e2])]

@_visitor(OpcodeCompareOp, BAB)
def _visit_cmp_start(self, deco, bab):
    if self.mode is CmpOp.EXC_MATCH:
        raise NoMatch
    return [CompareStart([bab.a, self.mode, bab.b])]

@_visitor(OpcodeCompareOp, CompareContinue)
def _visit_cmp_next(self, deco, cmp):
    if self.mode is CmpOp.EXC_MATCH:
        raise NoMatch
    return [CompareNext(cmp.items + [self.mode, cmp.next], cmp.target)]

@_visitor(OpcodeJumpIfFalse, CompareStart)
def _visit_cmp_jump(self, deco, cmp):
    return [Compare(cmp.items, self.target), WantPop()]

@_visitor(OpcodeJumpIfFalse, CompareNext)
def _visit_cmp_jump(self, deco, cmp):
    if cmp.target != self.target:
        raise PythonError("funny chained compare")
    return [Compare(cmp.items, cmp.target), WantPop()]

@_visitor(OpcodeCompareOp, Compare, Expr)
def _visit_cmp_last(self, deco, cmp, expr):
    if self.mode is CmpOp.EXC_MATCH:
        raise NoMatch
    return [CompareLast(cmp.items + [self.mode, expr], cmp.target)]

@_visitor(OpcodeJumpForward, CompareLast)
def _visit_cmp_last_jump(self, deco, cmp):
    return [ExprCmp(deco.version, cmp.items), WantInflow(), WantPop(), WantRotTwo()] + [WantInflow() for x in range((len(cmp.items) - 3) // 2)]

@_visitor(OpcodeRotThree, Compare, Dup)
def _visit_cmp_rot(self, deco, cmp, dup):
    return [CompareContinue(cmp.items, cmp.target, dup.expr)]

# loop framing

@_visitor(OpcodeSetupLoop)
def _visit_setup_loop(self, deco):
    return [SetupLoop(self.target), Block([])]

@_stmt_visitor(Inflow, SetupLoop, Block)
def _visit_end_loop(self, deco, loop, inner):
    if self.dst != loop.end:
        raise NoMatch
    return StmtLoop(inner), []

@_visitor(Inflow)
def _visit_loop(self, deco):
    if self.src <= self.dst:
        raise NoMatch
    return [Loop(self.src, self.dst)]

# while loop

@_stmt_visitor(OpcodeJumpAbsolute, Loop, IfStart, Block)
def _visit_while(self, deco,  loop, start, inner):
    if loop.src != self.pos or loop.dst != self.target or start.target != self.nextpos:
        raise PythonError("funny while loop")
    return StmtWhile(start.expr, inner), [WantPopBlock(), WantPop(), WantInflow()]

# for loop

@_visitor(OpcodeForLoop, Expr, ExprInt, Loop)
def _visit_for_start(self, deco, expr, zero, loop):
    if zero.val != 0:
        raise PythonError("funny for loop start")
    return [ForStart(expr, loop, self.target)]

@_stmt_visitor(OpcodeJumpAbsolute, ForLoop, Block)
def _visit_while(self, deco, loop, inner):
    if loop.loop.src != self.pos or loop.loop.dst != self.target or loop.end != self.nextpos:
        raise PythonError("funny for loop")
    return StmtFor(loop.expr, loop.dst, inner), [WantPopBlock(), WantInflow()]

# break

@_stmt_visitor(OpcodeBreakLoop)
def _visit_break(self, deco):
    return StmtBreak(deco.version), []

# try finally

@_visitor(OpcodeSetupFinally)
def _visit_setup_finally(self, deco):
    return [SetupFinally(self.pos, self.target), Block([])]

@_visitor(OpcodePopBlock, SetupFinally, Block)
def _visit_finally_pop(self, deco, setup, block):
    return [TryFinallyPending(block, setup.pos, setup.end)]

@_visitor(Inflow, TryFinallyPending, ExprNone)
def _visit_finally(self, deco, try_, _):
    if try_.pos != self.src or try_.end != self.dst:
        raise PythonError("funny finally")
    return [TryFinally(try_.body), Block([])]

@_stmt_visitor(OpcodeEndFinally, TryFinally, Block)
def _visit_finally_end(self, deco, try_, inner):
    return StmtFinally(try_.body, inner), []


class DecoCode:
    def __init__(self, code):
        self.version = code.version
        self.stack = [Block([])]
        self.bytecode = code.code
        self.lineno = None
        for op in self.bytecode.ops:
            for inflow in reversed(op.inflow):
                self.process(Inflow(inflow, op.pos))
            self.process(op)
        if len(self.stack) != 1:
            raise PythonError("stack non-empty at the end")
        if not isinstance(self.stack[0], Block):
            raise PythonError("weirdness on stack at the end")
        self.block = self.stack[0]


    def process(self, op):
        for visitor in _VISITORS.get(type(op), []):
            if visitor.visit(op, self):
                break
        else:
            raise PythonError("no visitors matched: {}, [{}]".format(
                type(op).__name__,
                ', '.join(type(x).__name__ for x in self.stack)
            ))


    def show(self):
        return self.block.show()
