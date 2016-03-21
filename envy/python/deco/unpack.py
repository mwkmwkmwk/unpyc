from ..bytecode import *
from ..expr import *
from ..stmt import *

from .visitor import visitor
from .stack import *

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
