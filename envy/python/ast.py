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


# processing stage one - makes class defs, cleans function bodies

def process_class_body(code, name):
    if code.code.name != name:
        raise PythonError("class name doesn't match code object")
    block = code.block
    if not block.stmts or not isinstance(block.stmts[-1], StmtEndClass):
        raise PythonError("no $endclass in class def")
    return Block(block.stmts[:-1])

def process_fun_body(code):
    block = code.block
    if not block.stmts or not isinstance(block.stmts[0], StmtArgs):
        raise PythonError("no $args in function def")
    return ExprFunction(code.code.name, block.stmts[0].args, Block(block.stmts[1:]))

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
        return StmtDef(fun.name, fun.args, fun.block)
    elif isclass(fun):
        if fun.name != name:
            return node
        return StmtClass(fun.name, fun.bases, fun.body)
    else:
        return node

def process_one(node):
    node = node.subprocess(process_one)
    if isinstance(node, ExprClassRaw):
        return ExprClass(node.name, node.bases, process_class_body(node.code, node.name))
    if isinstance(node, ExprFunctionRaw):
        return process_fun_body(node.code)
    if isinstance(node, StmtAssign):
        return process_def(node)
    return node

def make_top(deco):
    stmts = deco.block.stmts
    if not stmts:
        raise PythonError("empty top")
    ret = stmts[-1]
    if not isinstance(ret, StmtReturn):
        raise PythonError("top doesn't end in return")
    if not isinstance(ret.val, ExprNone):
        if len(stmts) != 1:
            raise PythonError("top has non-None return and long body")
        return RootEval(ret.expr)
    else:
        res = RootExec(Block(stmts[:-1]))
        return res


# processing stage two - makes lambdas

def process_lambda(node):
    stmts = node.block.stmts
    if node.name is not None:
        raise PythonError("lambda with a name")
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


# put it all together

def ast_process(deco):
    deco = process_one(deco)
    deco = process_two(deco)
    top = make_top(deco)
    return top
