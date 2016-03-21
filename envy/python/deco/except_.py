from ..stmt import *
from ..bytecode import *

from .visitor import visitor
from .stack import *
from .want import MaybeWantFlow

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
            try_.items + [ExceptClause(match.expr, match.dst, self.process_dead_end(block))],
            None,
            try_.flows + want.any + want.true + want.false,
        ),
        None if self.version.has_new_jump else WantPop(),
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
        None if self.version.has_new_jump else WantPop(),
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
        None if self.version.has_new_jump else WantPop(),
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
    block = self.process_dead_end(block)
    return [
        TryExceptMid(
            try_.else_,
            try_.body,
            try_.items + [ExceptClause(match.expr, match.dst, block)],
            None,
            try_.flows + want.any + want.true + want.false,
        ),
        None if self.version.has_new_jump else WantPop(),
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
    block = self.process_dead_end(block)
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
    block = self.process_dead_end(block)
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
