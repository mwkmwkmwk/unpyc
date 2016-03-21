from ..stmt import *
from ..bytecode import *
from ..expr import ExprInt

from .visitor import visitor
from .stack import *

# statements

@visitor
def _visit_stmt(
    self,
    op: Stmt,
    block: Block
):
    block.stmts.append(op)
    return [block]

# single expression statement

@visitor
def _visit_print_expr(
    self,
    op: OpcodePrintExpr,
    expr: Expr,
):
    return [StmtPrintExpr(expr)]

@visitor
def _visit_single_expr(
    self: '!always_print_expr',
    op: OpcodePopTop,
    block: Block,
    expr: Expr,
):
    return [block, StmtSingle(expr)]

# assignment

@visitor
def _visit_store_assign(
    self,
    op: Store,
    src: Expr,
):
    return [StmtAssign([op.dst], src)]

@visitor
def _visit_store_multi_start(
    self,
    op: Store,
    src: Expr,
    _: DupTop,
):
    return [MultiAssign(src, [op.dst])]

@visitor
def _visit_store_multi_next(
    self,
    op: Store,
    multi: MultiAssign,
    _: DupTop,
):
    multi.dsts.append(op.dst)
    return [multi]

@visitor
def _visit_store_multi_end(
    self,
    op: Store,
    multi: MultiAssign,
):
    multi.dsts.append(op.dst)
    return [StmtAssign(multi.dsts, multi.src)]

# print statement

@visitor
def _visit_print_item(
    self,
    op: OpcodePrintItem,
    expr: Expr,
):
    return [StmtPrint([expr], False)]

@visitor
def _visit_print_newline(
    self,
    op: OpcodePrintNewline,
):
    return [StmtPrint([], True)]

# print to

@visitor
def _visit_print_item_to_start(
    self,
    op: OpcodePrintItemTo,
    to: Expr,
    _dup: DupTop,
    expr: Expr,
    _rot: RotTwo,
):
    return [PrintTo(to, [expr])]

@visitor
def _visit_print_item_to_next(
    self,
    op: OpcodePrintItemTo,
    print: PrintTo,
    _dup: DupTop,
    expr: Expr,
    _rot: RotTwo,
):
    print.vals.append(expr)
    return [print]

@visitor
def _visit_print_to_end(
    self,
    op: OpcodePopTop,
    print: PrintTo,
):
    return [StmtPrintTo(print.expr, print.vals, False)]

@visitor
def _visit_print_newline_to_start(
    self,
    op: OpcodePrintNewlineTo,
    print: PrintTo,
):
    return [StmtPrintTo(print.expr, print.vals, True)]

@visitor
def _visit_print_newline_to_next(
    self,
    op: OpcodePrintNewlineTo,
    expr: Expr,
):
    return [StmtPrintTo(expr, [], True)]

# return statement

@visitor
def _visit_return(self, op: OpcodeReturnValue, expr: Expr):
    return [StmtReturn(expr)]

@visitor
def _visit_want_return(self, op: OpcodeReturnValue, want: WantReturn):
    return [StmtReturn(want.expr)]

# exec statement

@visitor
def _visit_exec_2(
    self,
    op: OpcodeExecStmt,
    code: Expr,
    env: Expr,
    _: DupTop,
):
    if isinstance(env, ExprNone):
        return [StmtExec(code, None, None)]
    else:
        return [StmtExec(code, env, None)]

@visitor
def _visit_exec_3(
    self,
    op: OpcodeExecStmt,
    code: Expr,
    globals: Expr,
    locals: Expr,
):
    return [StmtExec(code, globals, locals)]

# access

@visitor
def _visit_access(self, op: OpcodeAccessMode, mode: ExprInt):
    return [StmtAccess(op.param, mode.val)]
