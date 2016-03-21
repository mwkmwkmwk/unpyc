from ..helpers import PythonError
from ..bytecode import *
from ..expr import *
from ..stmt import *

from .visitor import visitor
from .stack import *

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
    body = self.process_dead_end(body)
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
    body = self.process_dead_end(body)
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
    body = self.process_dead_end(body)
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
    body = self.process_dead_end(body)
    return [StmtForTop(top.expr, top.dst, body)]
