from ..helpers import PythonError
from ..bytecode import *
from ..expr import *
from ..stmt import *

from .visitor import visitor
from .stack import *

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
