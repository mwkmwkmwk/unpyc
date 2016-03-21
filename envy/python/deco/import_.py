from ..helpers import PythonError
from ..bytecode import *
from ..expr import *
from ..stmt import *

from .visitor import visitor
from .stack import *

# imports

@visitor
def _visit_import_name(
    self: '!has_import_as',
    op: OpcodeImportName,
):
    return [Import(op.param, [])]

@visitor
def _visit_store_name_import(
    self,
    op: Store,
    import_: Import,
):
    if import_.items:
        raise PythonError("non-empty items for plain import")
    return [StmtImport(-1, import_.name, [], op.dst)]

@visitor
def _visit_import_from_star(
    self: '!has_import_star',
    op: OpcodeImportFrom,
    import_: Import,
):
    if op.param != '*':
        raise NoMatch
    if import_.items:
        raise PythonError("non-empty items for star import")
    return [StmtImportStar(-1, import_.name), WantPop()]

@visitor
def _visit_import_from(
    self,
    op: OpcodeImportFrom,
    import_: Import,
):
    if op.param == '*':
        raise NoMatch
    import_.items.append(op.param)
    return [import_]

@visitor
def _visit_import_from_end(
    self,
    op: OpcodePopTop,
    import_: Import,
):
    return [StmtFromImport(-1, import_.name, [FromItem(x, None) for x in import_.items])]

# imports - v2

@visitor
def _visit_import_name(
    self: ('has_import_as', '!has_relative_import'),
    op: OpcodeImportName,
    _: ExprNone,
):
    return [Import2Simple(-1, op.param, [])]

@visitor
def _visit_import_name(
    self: 'has_relative_import',
    op: OpcodeImportName,
    level: ExprInt,
    _: ExprNone,
):
    return [Import2Simple(level.val, op.param, [])]

@visitor
def _visit_import_name_attr(
    self,
    op: OpcodeLoadAttr,
    import_: Import2Simple,
):
    import_.attrs.append(op.param)
    return [import_]

@visitor
def _visit_store_name_import(
    self,
    op: Store,
    import_: Import2Simple,
):
    return [StmtImport(import_.level, import_.name, import_.attrs, op.dst)]

@visitor
def _visit_import_name(
    self: ('has_import_as', '!has_relative_import'),
    op: OpcodeImportName,
    expr: ExprTuple,
):
    fromlist = [self.string(item) for item in expr.exprs]
    if fromlist == ['*']:
        return [Import2Star(-1, op.param)]
    else:
        return [Import2From(-1, fromlist, op.param, [])]

@visitor
def _visit_import_name(
    self: 'has_relative_import',
    op: OpcodeImportName,
    level: ExprInt,
    expr: ExprTuple,
):
    fromlist = [self.string(item) for item in expr.exprs]
    if fromlist == ['*']:
        return [Import2Star(level.val, op.param)]
    else:
        return [Import2From(level.val, fromlist, op.param, [])]

@visitor
def _visit_import_star(
    self,
    op: OpcodeImportStar,
    import_: Import2Star,
):
    return [StmtImportStar(import_.level, import_.name)]

@visitor
def _visit_import_from(
    self,
    op: OpcodeImportFrom,
    import_: Import2From,
):
    idx = len(import_.exprs)
    if (idx >= len(import_.fromlist) or import_.fromlist[idx] != op.param):
        raise PythonError("fromlist mismatch")
    return [import_, UnpackSlot(import_, idx)]

@visitor
def _visit_import_from_end(
    self,
    op: OpcodePopTop,
    import_: Import2From,
):
    return [StmtFromImport(import_.level, import_.name, [FromItem(a, b) for a, b in zip(import_.fromlist, import_.exprs)])]
