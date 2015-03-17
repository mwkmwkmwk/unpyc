from envy.show import indent

class FunArgs:
    __slots__ = 'args', 'defargs', 'vararg', 'kwargs', 'varkw'

    def __init__(self, args, defargs, vararg, kwargs, varkw):
        self.args = args
        if len(defargs) < len(args):
            defargs = [None] * (len(args) - len(defargs)) + defargs
        self.defargs = defargs
        self.vararg = vararg
        self.kwargs = kwargs
        self.varkw = varkw

    def subprocess(self, process):
        return FunArgs(
            [process(arg) for arg in self.args],
            [process(arg) if arg else None for arg in self.defargs],
            process(self.vararg) if self.vararg else None,
            [process(arg) for arg in self.kwargs],
            process(self.varkw) if self.varkw else None,
        )

    def setdefs(self, defargs):
        return FunArgs(
            self.args,
            defargs,
            self.vararg,
            self.kwargs,
            self.varkw
        )

    def show(self):
        chunks = [
            ('', arg, defarg)
            for arg, defarg in zip(self.args, self.defargs)
        ]
        if self.vararg:
            chunks.append(('*', self.vararg, None))
        elif self.kwargs:
            chunks.append(('*', None, None))
        chunks.extend([('', arg, None) for arg in self.kwargs])
        if self.varkw:
            chunks.append(('**', self.varkw, None))
        return ', '.join(
            '{}{}{}'.format(
                pref,
                arg.show(None) if arg else '',
                "={}".format(defarg.show(None)) if defarg else ''
            )
            for pref, arg, defarg in chunks
        )


class Block:
    __slots__ = 'stmts',

    def __init__(self, stmts):
        self.stmts = stmts

    def subprocess(self, process):
        return Block([process(stmt) for stmt in self.stmts])

    def show(self):
        for stmt in self.stmts:
            yield from stmt.show()
        if not self.stmts:
            yield 'pass'


class Stmt:
    __slots__ = ()


class StmtReturn(Stmt):
    __slots__ = 'val',

    def __init__(self, val):
        self.val = val

    def subprocess(self, process):
        return StmtReturn(process(self.val))

    def show(self):
        yield "return {}".format(self.val.show(None))


class StmtPrint(Stmt):
    __slots__ = 'vals', 'nl'

    def __init__(self, vals, nl=True):
        self.vals = vals
        self.nl = nl

    def subprocess(self, process):
        return StmtPrint([process(expr) for expr in self.vals], self.nl)

    def show(self):
        if self.vals:
            yield "print {}{}".format(', '.join(val.show(None) for val in self.vals), '' if self.nl else ',')
        else:
            assert self.nl
            yield "print"


class StmtSingle(Stmt):
    __slots__ = 'val',

    def __init__(self, val):
        self.val = val

    def subprocess(self, process):
        return StmtSingle(process(self.val))

    def show(self):
        yield self.val.show(None)


class StmtPrintExpr(Stmt):
    __slots__ = 'val',

    def __init__(self, val):
        self.val = val

    def subprocess(self, process):
        return StmtPrintExpr(process(self.val))

    def show(self):
        yield "$print {}".format(self.val.show(None))


class StmtAssign(Stmt):
    __slots__ = 'dests', 'expr'

    def __init__(self, dests, expr):
        self.dests = dests
        self.expr = expr

    def subprocess(self, process):
        return StmtAssign([process(dst) for dst in self.dests], process(self.expr))

    def show(self):
        yield '{}{}'.format(
            ''.join(
                '{} = '.format(dest.show(None))
                for dest in self.dests
            ),
            self.expr.show(None)
        )


class StmtDel(Stmt):
    __slots__ = 'val',

    def __init__(self, val):
        self.val = val

    def subprocess(self, process):
        return StmtDel(process(self.val))

    def show(self):
        yield "del {}".format(self.val.show(None))


class StmtRaise(Stmt):
    __slots__ = 'cls', 'val', 'tb'

    def __init__(self, cls=None, val=None, tb=None):
        self.cls = cls
        self.val = val
        self.tb = tb

    def subprocess(self, process):
        return StmtRaise(
            process(self.cls) if self.cls else None,
            process(self.val) if self.val else None,
            process(self.tb) if self.tb else None,
        )

    def show(self):
        if self.cls is None:
            yield "raise"
        elif self.val is None:
            yield "raise {}".format(self.cls.show(None))
        elif self.tb is None:
            yield "raise {}, {}".format(self.cls.show(None), self.val.show(None))
        else:
            yield "raise {}, {}, {}".format(self.cls.show(None), self.val.show(None), self.tb.show(None))


class StmtImport(Stmt):
    __slots__ = 'name', 'as_'

    def __init__(self, name, as_):
        self.name = name
        self.as_ = as_

    def subprocess(self, process):
        return StmtImport(
            self.name,
            process(self.as_)
        )

    def show(self):
        yield "import {} as {}".format(self.name, self.as_.show(None))


class StmtFromImport(Stmt):
    __slots__ = 'name', 'items'

    def __init__(self, name, items):
        self.name = name
        self.items = items

    def subprocess(self, process):
        return self

    def show(self):
        yield "from {} import {}".format(
            self.name,
            ', '.join(self.items)
        )


class StmtExec(Stmt):
    __slots__ = 'code', 'globals', 'locals'

    def __init__(self, code, globals=None, locals=None):
        self.code = code
        self.globals = globals
        self.locals = locals

    def subprocess(self, process):
        return StmtExec(
            process(self.code),
            process(self.globals) if self.globals else None,
            process(self.locals) if self.locals else None,
        )

    def show(self):
        if self.globals is None:
            yield "exec {}".format(
                self.code.show(None)
            )
        elif self.locals is None:
            yield "exec {} in {}".format(
                self.code.show(None),
                self.globals.show(None)
            )
        else:
            yield "exec {} in {}, {}".format(
                self.code.show(None),
                self.globals.show(None),
                self.locals.show(None)
            )


class StmtIf(Stmt):
    __slots__ = 'items', 'else_'

    def __init__(self, items, else_):
        self.items = items
        self.else_ = else_

    def subprocess(self, process):
        return StmtIf(
            [
                (process(expr), process(block))
                for expr, block in self.items
            ],
            process(self.else_) if self.else_ else None
        )

    def show(self):
        for idx, (expr, block) in enumerate(self.items):
            yield "{} {}:".format('if' if idx == 0 else 'elif', expr.show(None))
            yield from indent(block.show())
        if self.else_:
            yield "else:"
            yield from indent(self.else_.show())


class StmtLoop(Stmt):
    __slots__ = 'body'

    def __init__(self, body):
        self.body = body

    def subprocess(self, process):
        return StmtLoop(process(self.body))

    def show(self):
        yield "$loop:"
        yield from indent(self.body.show())


class StmtWhileRaw(Stmt):
    __slots__ = 'expr', 'body'

    def __init__(self, expr, body):
        self.expr = expr
        self.body = body

    def subprocess(self, process):
        return StmtWhileRaw(process(self.expr), process(self.body))

    def show(self):
        yield "$while {}:".format(self.expr.show(None))
        yield from indent(self.body.show())


class StmtWhile(Stmt):
    __slots__ = 'expr', 'body', 'else_'

    def __init__(self, expr, body, else_):
        self.expr = expr
        self.body = body
        self.else_ = else_

    def subprocess(self, process):
        return StmtWhile(
            process(self.expr),
            process(self.body),
            process(self.else_) if self.else_ else None
        )

    def show(self):
        yield "while {}:".format(self.expr.show(None))
        yield from indent(self.body.show())
        if self.else_ is not None:
            yield "else:"
            yield from indent(self.else_.show())


class StmtForRaw(Stmt):
    __slots__ = 'expr', 'dst', 'body'

    def __init__(self, expr, dst, body):
        self.expr = expr
        self.dst = dst
        self.body = body

    def subprocess(self, process):
        return StmtForRaw(process(self.expr), process(self.dst), process(self.body))

    def show(self):
        yield "$for {} in {}:".format(self.dst.show(None), self.expr.show(None))
        yield from indent(self.body.show())


class StmtFor(Stmt):
    __slots__ = 'expr', 'dst', 'body', 'else_'

    def __init__(self, expr, dst, body, else_):
        self.expr = expr
        self.dst = dst
        self.body = body
        self.else_ = else_

    def subprocess(self, process):
        return StmtFor(
            process(self.expr),
            process(self.dst),
            process(self.body),
            process(self.else_) if self.else_ else None
        )

    def show(self):
        yield "for {} in {}:".format(self.dst.show(None), self.expr.show(None))
        yield from indent(self.body.show())
        if self.else_ is not None:
            yield "else:"
            yield from indent(self.else_.show())


class StmtFinally(Stmt):
    __slots__ = 'try_', 'finally_'

    def __init__(self, try_, finally_):
        self.try_ = try_
        self.finally_ = finally_

    def subprocess(self, process):
        return StmtFinally(
            process(self.try_),
            process(self.finally_),
        )

    def show(self):
        yield "try:"
        yield from indent(self.try_.show())
        yield "finally:"
        yield from indent(self.finally_.show())


class StmtExcept(Stmt):
    __slots__ = 'try_', 'items', 'any', 'else_'

    def __init__(self, try_, items, any, else_):
        self.try_ = try_
        self.items = items
        self.any = any
        self.else_ = else_

    def subprocess(self, process):
        return StmtExcept(
            process(self.try_),
            [
                (
                    process(expr),
                    process(dst) if dst else None,
                    process(body),
                )
                for expr, dst, body in self.items
            ],
            process(self.any) if self.any else None,
            process(self.else_) if self.else_ else None,
        )

    def show(self):
        yield "try:"
        yield from indent(self.try_.show())
        for expr, dst, body in self.items:
            if dst is None:
                yield 'except {}:'.format(expr.show(None))
            else:
                # TODO as
                yield 'except {}, {}:'.format(expr.show(None), dst.show(None))
            yield from indent(body.show())
        if self.any is not None:
            yield "except:"
            yield from indent(self.any.show())
        if self.else_ is not None:
            yield "else:"
            yield from indent(self.else_.show())


class StmtBreak(Stmt):
    __slots__ = ()

    def subprocess(self, process):
        return self

    def show(self):
        yield 'break'


class StmtContinue(Stmt):
    __slots__ = ()

    def subprocess(self, process):
        return self

    def show(self):
        yield 'continue'


class StmtAccess(Stmt):
    __slots__ = 'name', 'mode'

    # TODO: decode that crap
    def __init__(self, name, mode):
        self.name = name
        self.mode = mode

    def subprocess(self, process):
        return self

    def show(self):
        yield 'access {}: {:o}'.format(self.name, self.mode)


class StmtArgs(Stmt):
    __slots__ = 'args'

    def __init__(self, args):
        self.args = args

    def subprocess(self, process):
        return StmtArgs(process(self.args))

    def show(self):
        yield "$args {}".format(self.args.show())


class StmtClass(Stmt):
    __slots__ = 'name', 'bases', 'body'

    def __init__(self, name, bases, body):
        self.name = name
        self.bases = bases
        self.body = body

    def subprocess(self, process):
        return StmtClass(
            self.name,
            [process(base) for base in self.bases],
            process(self.body)
        )

    def show(self):
        if self.bases:
            yield 'class {}({}):'.format(
                self.name,
                ', '.join(
                    base.show(None)
                    for base in self.bases
                )
            )
        else:
            yield 'class {}:'.format(self.name)
        yield from indent(self.body.show())


class StmtEndClass(Stmt):
    __slots__ = ()

    def subprocess(self, process):
        return self

    def show(self):
        yield '$endclass'


class StmtDef(Stmt):
    __slots__ = 'name', 'args', 'body'

    def __init__(self, name, args, body):
        self.name = name
        self.args = args
        self.body = body

    def subprocess(self, process):
        return StmtDef(
            self.name,
            process(self.args),
            process(self.body)
        )

    def show(self):
        yield 'def {}({}):'.format(
            self.name,
            self.args.show()
        )
        yield from indent(self.body.show())
