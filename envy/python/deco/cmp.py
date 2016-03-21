from ..expr import *
from ..bytecode import *

from .visitor import visitor
from .stack import *

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
def _visit_cmp_last_jump_dead(
    self: 'has_dead_return',
    op: OpcodeReturnValue,
    cmp: CompareLast,
):
    return [
        WantReturn(ExprCmp(cmp.first, cmp.rest)),
        WantRotPop(),
        WantFlow([], [], cmp.flows),
    ]

# x in const set special

@visitor
def _visit_frozenset(
    self,
    op: OpcodeCompareOp,
    fset: Frozenset
):
    if op.param not in [CmpOp.IN, CmpOp.NOT_IN]:
        raise PythonError("funny place for frozenset")
    if not fset.exprs:
        raise PythonError("can't make empty set display out of frozenset")
    return [ExprSet(fset.exprs), op]
