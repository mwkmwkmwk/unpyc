from .helpers import PythonError

from .stmt import *
from .expr import *

class RootExec:
    __slots__ = 'block',

    def __init__(self, block):
        self.block = block

    def show(self):
        return self.block.show()

class RootEval:
    __slots__ = 'expr',

    def __init__(self, expr):
        self.expr = expr

    def show(self):
        yield self.expr.show(None)


def ast_process(deco, version):

    # processing stage one:
    #
    # - makes class/function expressions, and cleans their bodies from relevant stuff
    # - cleans if statements: empty else suites are discarded, else suites consisting
    #   of a single if statement are changed into elif
    # - get rid of empty else suites on try except statements
    # - converts $loop and $for/$while into proper for/while
    # - for Python 1.0, convert all $print to expression statements

    def process_class_body(code, name):
        if code.code.name != name:
            raise PythonError("class name doesn't match code object")
        block = code.block
        if code.varnames:
            raise PythonError("class has fast vars")
        if not block.stmts or not isinstance(block.stmts[-1], StmtEndClass):
            raise PythonError("no $endclass in class def")
        return Block(block.stmts[:-1])

    def process_fun_body(node):
        block = node.code.block
        if not block.stmts or not isinstance(block.stmts[0], StmtArgs):
            raise PythonError("no $args in function def")
        return ExprFunction(
            node.code.code.name,
            block.stmts[0].args.setdefs(node.defargs),
            Block(block.stmts[1:])
        )

    def isfunction(subnode):
        return isinstance(subnode, ExprFunction)

    def isclass(subnode):
        return isinstance(subnode, ExprClass)

    def process_def(node):
        if len(node.dests) != 1:
            return node
        dst = node.dests[0]
        fun = node.expr

        # TODO allow only ExprName, punt it before name resolve
        if not isinstance(dst, (ExprName, ExprGlobal, ExprFast)):
            return node
        name = dst.name

        if isfunction(fun):
            if not fun.name or fun.name != name:
                return node
            stmts = fun.block.stmts
            if stmts and isinstance(stmts[-1], StmtReturn) and isinstance(stmts[-1].val, ExprNone):
                stmts.pop()
            else:
                raise PythonError("function not terminated by return None")
            return StmtDef(fun.name, fun.args, fun.block)
        elif isclass(fun):
            if fun.name != name:
                return node
            return StmtClass(fun.name, fun.bases, fun.body)
        else:
            return node

    def process_if(node):
        if not node.else_ or not node.else_.stmts:
            return StmtIf(node.items, None)
        elif len(node.else_.stmts) == 1:
            subif = node.else_.stmts[0]
            if isinstance(subif, StmtIf):
                return StmtIf(node.items + subif.items, subif.else_)
        return node

    def process_except(node):
        if not node.else_ or not node.else_.stmts:
            return StmtExcept(node.try_, node.items, node.any, None)
        return node

    def process_loop(node):
        stmts = node.body.stmts
        if not stmts:
            raise PythonError("empty $loop")
        raw = stmts[0]
        if len(stmts) == 1:
            else_ = None
        else:
            else_ = Block(stmts[1:])
        if isinstance(raw, StmtWhileRaw):
            return StmtWhile(raw.expr, raw.body, else_)
        elif isinstance(raw, StmtForRaw):
            return StmtFor(raw.expr, raw.dst, raw.body, else_)
        else:
            raise PythonError("$loop with funny contents")

    def process_one(node):
        node = node.subprocess(process_one)
        if isinstance(node, ExprClassRaw):
            return ExprClass(node.name, node.bases, process_class_body(node.code, node.name))
        if isinstance(node, ExprFunctionRaw):
            return process_fun_body(node)
        if isinstance(node, StmtAssign):
            return process_def(node)
        if isinstance(node, StmtIf):
            return process_if(node)
        if isinstance(node, StmtExcept):
            return process_except(node)
        if isinstance(node, StmtLoop):
            return process_loop(node)
        if version.always_print_expr and isinstance(node, StmtPrintExpr):
            return StmtSingle(node.val)
        return node

    deco = process_one(deco)

    # processing stage two
    #
    # - makes lambdas
    # - makes sure function/class-related junk is gone

    def process_lambda(node):
        stmts = node.block.stmts
        if node.name is not None and node.name != '<lambda>':
            raise PythonError("lambda with a name: {}".format(node.name))
        if len(stmts) != 1:
            raise PythonError("lambda body too long")
        if not isinstance(stmts[0], StmtReturn):
            raise PythonError("lambda body has no return")
        return ExprLambda(node.args, stmts[0].val)

    def process_two(node):
        node = node.subprocess(process_two)
        if isinstance(node, ExprFunction):
            return process_lambda(node)
        elif isinstance(node, ExprClass):
            raise PythonError("$class still alive")
        elif isinstance(node, StmtArgs):
            raise PythonError("$args still alive")
        elif isinstance(node, StmtEndClass):
            raise PythonError("$endclass still alive")
        return node

    deco = process_two(deco)

    # wrap the top level
    stmts = deco.block.stmts
    if not stmts:
        raise PythonError("empty top")
    ret = stmts[-1]
    if deco.varnames and not version.has_closure:
        raise PythonError("top has fast vars")
    if not isinstance(ret, StmtReturn):
        raise PythonError("top doesn't end in return")
    if not isinstance(ret.val, ExprNone):
        if len(stmts) != 1:
            raise PythonError("top has non-None return and long body")
        return RootEval(ret.expr)
    else:
        return RootExec(Block(stmts[:-1]))