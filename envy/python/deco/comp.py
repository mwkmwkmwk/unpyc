from ..helpers import PythonError
from ..bytecode import *
from ..expr import *
from ..stmt import *
from ..postproc import uncomp

from .visitor import visitor
from .stack import *

# list comprehensions

@visitor
def _visit_listcomp_start(
    self,
    op: Store,
    dup: DupAttr,
):
    if not isinstance(op.dst, (ExprName, ExprFast, ExprGlobal)):
        raise NoMatch
    return [TmpVarAttrStart(op.dst, dup.expr, dup.name)]

@visitor
def _visit_listcomp_attr_append(
    self: '!has_list_append',
    op: StmtForRaw,
    start: TmpVarAttrStart,
):
    if (not isinstance(start.expr, ExprList)
        or len(start.expr.exprs) != 0
        or start.name != 'append'):
        raise PythonError("weird listcomp start")
    stmt, items = uncomp(op, False, False)
    if not (isinstance(stmt, StmtSingle)
        and isinstance(stmt.val, ExprCall)
        and stmt.val.expr == start.tmp
        and len(stmt.val.args.args) == 1
        and isinstance(stmt.val.args.args[0], CallArgPos)
    ):
        raise PythonError("weird old list comp")
    return [ExprListComp(Comp(stmt.val.args.args[0].expr, items)), TmpVarCleanup(start.tmp)]

@visitor
def _visit_listcomp_op_append(
    self: 'has_list_append',
    op: StmtForRaw,
    ass: MultiAssign,
):
    if len(ass.dsts) != 1:
        raise PythonError("multiassign in list comp too long")
    if not isinstance(ass.src, ExprList) or ass.src.exprs:
        raise PythonError("comp should start with an empty list")
    tmp = ass.dsts[0]
    stmt, items = uncomp(op, False, False)
    if not (isinstance(stmt, StmtListAppend)
        and stmt.tmp == tmp
    ):
        raise PythonError("weird old list comp")
    return [ExprListComp(Comp(stmt.val, items)), TmpVarCleanup(tmp)]

@visitor
def _visit_listcomp_end(
    self,
    op: StmtDel,
    comp: TmpVarCleanup,
):
    if comp.tmp != op.val:
        raise PythonError("deleting a funny name")
    return []

@visitor
def _visit_comp_item_list(
    self,
    op: OpcodeListAppend,
    tmp: Expr,
    val: Expr,
):
    return [StmtListAppend(tmp, val)]

@visitor
def _visit_comp_item_set(
    self,
    op: OpcodeSetAdd,
    tmp: Expr,
    val: Expr,
):
    return [StmtSetAdd(tmp, val)]

@visitor
def visit_comp_item_dict(
    self,
    op: OpcodeStoreSubscr,
    tmp: Expr,
    val: Expr,
    _: RotTwo,
    key: Expr,
):
    return [StmtMapAdd(tmp, key, val)]

# new comprehensions

@visitor
def visit_call_function(
    self,
    op: OpcodeCallFunction,
    fun: ExprFunctionRaw,
    arg: Iter
):
    if (fun.defargs
        or fun.defkwargs
        or fun.ann
        or op.args != 1
        or op.kwargs != 0
    ):
        raise NoMatch
    return [ExprCallComp(fun, arg.expr)]

@visitor
def _visit_fun_comp(
    self: 'has_setdict_comp',
    op: StmtForTop,
    ass: MultiAssign
):
    if len(ass.dsts) != 1:
        raise PythonError("too many dsts to be a comp")
    tmp = ass.dsts[0]
    if not isinstance(tmp, ExprFast):
        raise PythonError("funny tmp for new comp")
    stmt, items, (topdst, arg) = uncomp(op, False, True)
    if isinstance(ass.src, ExprList) and self.version.has_fun_listcomp:
        if not (isinstance(stmt, StmtListAppend)
            and stmt.tmp == tmp
            and len(ass.src.exprs) == 0
        ):
            raise PythonError("funny list comp")
        return [ExprNewListCompRaw(
            stmt.val,
            topdst,
            items,
            arg,
        )]
    elif isinstance(ass.src, ExprSet):
        if not (isinstance(stmt, StmtSetAdd)
            and stmt.tmp == tmp
            and len(ass.src.exprs) == 0
        ):
            raise PythonError("funny set comp")
        return [ExprNewSetCompRaw(
            stmt.val,
            topdst,
            items,
            arg,
        )]
    elif isinstance(ass.src, ExprDict):
        if not (isinstance(stmt, StmtMapAdd)
            and stmt.tmp == tmp
            and len(ass.src.items) == 0
        ):
            raise PythonError("funny dict comp")
        return [ExprNewDictCompRaw(
            stmt.key,
            stmt.val,
            topdst,
            items,
            arg,
        )]
    else:
        raise PythonError("weird comp")
