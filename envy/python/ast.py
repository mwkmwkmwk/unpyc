from envy.meta import Node, Field, ListField, DictField


class Expr(Node, abstract=True):
    pass


class Stmt(Node, abstract=True):
    pass


class Block(Node):
    stmts = ListField(Stmt, volatile=True)

    def show(self):
        for stmt in self.stmts:
            yield from stmt.show()
        if not self.stmts:
            yield 'pass'


class FunArgs(Node):
    args = ListField(Expr)
    defargs = ListField(Expr)
    vararg = Field(Expr, optional=True)
    kwargs = ListField(Expr)
    defkwargs = DictField(str, Expr)
    varkw = Field(Expr, optional=True)
    ann = DictField(str, Expr)

    def setdefs(self, defargs, defkwargs, ann):
        return FunArgs(
            self.args,
            defargs,
            self.vararg,
            self.kwargs,
            defkwargs,
            self.varkw,
            ann
        )

    def show(self):
        from .expr import ExprFast
        def _ann(arg):
            if not isinstance(arg, ExprFast):
                return None
            return self.ann.get(arg.name)
        chunks = [
            ('', arg, defarg, _ann(arg))
            for arg, defarg in zip(self.args, [None] * (len(self.args) - len(self.defargs)) + list(self.defargs))
        ]
        if self.vararg:
            chunks.append(('*', self.vararg, None, _ann(self.vararg)))
        elif self.kwargs:
            chunks.append(('*', None, None, None))
        chunks.extend([('', arg, self.defkwargs.get(arg.name), _ann(arg)) for arg in self.kwargs])
        if self.varkw:
            chunks.append(('**', self.varkw, None, _ann(self.varkw)))
        return ', '.join(
            '{}{}{}{}'.format(
                pref,
                arg.show(None) if arg else '',
                ": {}".format(ann.show(None)) if ann else '',
                "={}".format(defarg.show(None)) if defarg else ''
            )
            for pref, arg, defarg, ann in chunks
        )


class CallArg(Node, abstract=True):
    expr = Field(Expr)

class CallArgPos(CallArg):
    def show(self):
        return self.expr.show(None)

class CallArgKw(CallArg):
    name = Field(str)
    def show(self):
        return '{}={}'.format(self.name, self.expr.show(None))

class CallArgVar(CallArg):
    def show(self):
        return '*{}'.format(self.expr.show(None))

class CallArgVarKw(CallArg):
    def show(self):
        return '**{}'.format(self.expr.show(None))

class CallArgs(Node):
    args = ListField(CallArg)

    def show(self):
        return ', '.join(x.show() for x in self.args)
