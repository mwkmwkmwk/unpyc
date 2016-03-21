from ..helpers import PythonError
from ..bytecode import *
from ..expr import *
from ..stmt import *
from ..postproc import unreturn

from .visitor import visitor
from .want import *
from .stack import *

def _maybe_want_pop(flag):
    if flag:
        return None
    else:
        return WantPop()

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

@visitor
def _visit_dead_if(
    self,
    op: FwdFlow,
    start: IfStart,
    block: Block,
    want: MaybeWantFlow,
):
    block = self.process_dead_end(block)
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
