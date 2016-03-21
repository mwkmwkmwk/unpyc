from ..helpers import PythonError
from ..bytecode import *
from ..expr import *
from ..stmt import *

from .visitor import visitor
from .want import *
from .stack import *

# assert. ouch. has to be before raise.

@visitor
def _visit_assert_1(
    self: ('has_assert', '!has_short_assert'),
    op: OpcodeRaiseVarargs,
    ifstart: IfStart,
    block: Block,
    orstart: IfStart,
    block2: Block,
    exprs: Exprs('param', 1),
):
    if ifstart.neg or not orstart.neg or ifstart.pop or orstart.pop:
        raise NoMatch
    if block.stmts or block2.stmts:
        raise PythonError("extra assert statements")
    if not isinstance(exprs[0], ExprGlobal) or exprs[0].name != 'AssertionError':
        raise PythonError("hmm, I wanted an assert...")
    if not isinstance(ifstart.expr, ExprGlobal) or ifstart.expr.name != '__debug__':
        raise PythonError("hmm, I wanted an assert...")
    if op.param == 1:
        return [StmtAssert(orstart.expr), WantPop(), WantFlow([], orstart.flow, ifstart.flow)]
    elif op.param == 2:
        return [StmtAssert(orstart.expr, exprs[1]), WantPop(), WantFlow([], orstart.flow, ifstart.flow)]
    else:
        raise PythonError("funny assert params")

@visitor
def _visit_assert_2(
    self: ('has_short_assert', '!has_raise_from'),
    op: FwdFlow,
    start: IfStart,
    body: Block,
):
    if not start.neg or start.pop:
        raise NoMatch
    if (len(body.stmts) != 1
        or not isinstance(body.stmts[0], StmtRaise)
        or not isinstance(body.stmts[0].cls, ExprGlobal)
        or body.stmts[0].cls.name != 'AssertionError'
        or body.stmts[0].tb is not None
    ):
        raise NoMatch
    return [AssertJunk(start.expr, body.stmts[0].val), WantFlow([], start.flow, []), op]

@visitor
def _visit_assert_2(
    self: ('has_short_assert', 'has_raise_from'),
    op: FwdFlow,
    start: IfStart,
    body: Block,
):
    if not start.neg or start.pop:
        raise NoMatch
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
        return [AssertJunk(start.expr, val.args.args[0][1]), WantFlow([], start.flow, []), op]
    else:
        raise PythonError("that's still not an assert")

@visitor
def _visit_assert_junk(
    self,
    op: OpcodePopTop,
    junk: AssertJunk,
):
    return [StmtAssert(*junk)]

@visitor
def _visit_assert_or(
    self: 'has_jump_cond_fold',
    op: FwdFlow,
    start: IfStart,
    block: Block,
    junk: AssertJunk,
):
    if not start.neg or start.pop:
        raise NoMatch
    if block.stmts:
        raise NoMatch
    return [AssertJunk(ExprBoolOr(start.expr, junk.expr), junk.msg), WantFlow([], start.flow, []), op]

# raise statement

# Python 1.0 - 1.2
@visitor
def _visit_raise_1(
    self,
    op: OpcodeRaiseException,
    cls: Expr,
    _: ExprNone,
):
    return [StmtRaise(cls)]

@visitor
def _visit_raise_2(
    self,
    op: OpcodeRaiseException,
    cls: Expr,
    val: Expr,
):
    return [StmtRaise(cls, val)]

# Python 1.3-2.7
@visitor
def _visit_raise_varargs(
    self: '!has_raise_from',
    op: OpcodeRaiseVarargs,
    exprs: Exprs('param', 1),
):
    if len(exprs) > 3:
        raise PythonError("too many args to raise")
    if len(exprs) == 0 and not self.version.has_reraise:
        raise PythonError("too few args to raise")
    return [StmtRaise(*exprs)]

# Python 3
@visitor
def _visit_raise_from(
    self: 'has_raise_from',
    op: OpcodeRaiseVarargs,
    exprs: Exprs('param', 1),
):
    if len(exprs) < 2:
        return [StmtRaise(*exprs)]
    elif len(exprs) == 2:
        return [StmtRaise(exprs[0], None, exprs[1])]
    else:
        raise PythonError("too many args to raise")
