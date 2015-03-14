from envy.format.marshal import MarshalCode, MarshalDict, MarshalString, MarshalInt
from envy.python.bytecode import parse_lnotab, Bytecode
from envy.show import preindent, indent

from .expr import from_marshal
from .helpers import PythonError

from enum import Enum, IntEnum


class CodeType(Enum):
    """There are 9 kinds of code objects in Python.

    The most basic division is between modules, functions, and classes.

    Modules are the top-level code objects.  They are executed with globals
    equal to locals, have no parameters, return None, and are not optimized.
    They are easily recognised by being the top level.  They also always have
    a name of '<module>'.

    Classes are executed with an arbitrary object as locals, and are not
    optimized.  They are passed to MAKE_FUNCTION, and then to __build_class__.

    Functions have a dedicated local namespance, and are usually optimized
    (always in py3k).  They are passed to MAKE_FUNCTION.  They come in several
    subkinds.

    A generator is a function that has 'generator' set in flags.  As opposed
    to a normal function, it can use the yield expression.

    A genexp is a generator created from a generator expression.  It can be
    recognised by name equal to '<genexp>'.

    Likewise, list/set/dict comprehensions are compiled to functions (in py3k
    only).  They are named '<listcomp>', '<dictcomp>', or '<setcomp>'.

    Finally, lambdas are functions compiled from a lambda expression.  They
    have name equal to '<lambda>'.

    If one is sufficiently evil, it's also perfectly possible to make lambdas
    or comprehensions with yield expressions, thus turning them into
    generators.  This is godawfully ugly, but doesn't actually cause any
    problems for decompilation.

    If names are intact, all these types except function vs class can be
    recognised just by looking at the code object properties.

    The only reliable way to tell a class from a function in py2 is by looking
    whether the parent will pass it to __build_class__.  In py3k, optimization
    could be used instead.

    In the absence of names, it's trivial to tell apart module vs function/class
    vs generator only.  In such case, genexps and comprehensions can be
    recognized by whether they are immediately called after creation with
    result of GET_ITER as an argument.  However, there's no general way to tell
    lambdas apart from functions - a lambda cannot have complex code flow, while
    a function can only be transformed in limitted ways (ie. decorators) before
    being stored to a variable.

    The exact type of comprehension or genexp can be determined by looking
    at the source of the returned value.

    There are also two kinds of code objects that you won't find in pyc files:
    eval and single.  They are created by compile() function with mode set to
    'eval' and 'single, respectively (passing 'exec' as mode creates an ordinary
    module).  Confusingly, they all have name set to '<module>'.  Eval is like
    lambda for modules: it's an unoptimized code object, and basically consists
    of a single return statement (as opposed to normal modules, which always
    return None).  Single is used for interactive mode: it consists of a single
    source statement (though ; can be used to cheat that), and if the top-level
    statement(s) merely compute an expression, they're changed to special print
    statements (PRINT_EXPR opcode, impossible to come by in any other way).
    Otherwise, it behaves like 'exec' mode.

    If we were to support non-pyc sources of bytecode, eval is easy to tell
    apart from exec/single: exec has multiple statments and synthetic "return
    None" at the end, eval is single return statement.  The exception is that
    empty exec can't be distinguished from 'None' eval.  Exec can be
    distinguished from single iff there was a top-level expression statement
    (PRINT_EXPR vs POP_TOP), or if there are multiple top-level statements
    and they're not on the same line (can only happen for exec).
    """
    module = ()

    class_ = ()

    function = ()
    lambda_ = ()
    listcomp = ()
    dictcomp = ()
    setcomp = ()
    genexp = ()


class CodeFlag(IntEnum):
    optimized = 1 << 0
    newlocals = 1 << 1
    varargs = 1 << 2
    varkeywords = 1 << 3
    nested = 1 << 4
    generator = 1 << 5
    nofree = 1 << 6
    # future flags
    future_generator = 1 << 12
    future_division = 1 << 13
    future_absolute_import = 1 << 14
    future_with_statement = 1 << 15
    future_print_function = 1 << 16
    future_unicode_literals = 1 << 17
    future_barry_as_flufl = 1 << 18


class CodeDict:
    """Special class for dicts found in consts tab.

    They, as mutable objects, aren't ever emitted directly for user
    expressions - thus we don't map them to ExprDict.  However, ancient pythons
    use them as arguments for RESERVE_FAST.
    """
    __slots__ = 'val',

    def __init__(self, val):
        self.val = []
        for k, v in val:
            if not isinstance(k, MarshalString):
                raise PythonError("CodeDict key not string")
            if not isinstance(v, MarshalInt):
                raise PythonError("CodeDict value not int")
            self.val.append((k.val.decode('ascii'), v.val))

    def show(self):
        yield "DICT"
        for key, val in self.val:
            yield '\t{}: {}\n'.format(key, val)

class Code:
    __slots__ = (
        'version',

        'name',
        'filename',

        'flags',

        'varnames',

        'args',
        'kwargs',
        'varargs',
        'varkw',

        'freevars',
        'cellvars',

        'stacksize',
        'consts',
        'names',

        'rawcode',
        'code',
        'firstlineno',
        'lnotab',
    )

    def __init__(self, obj, version):
        if not isinstance(obj, MarshalCode):
            raise PythonError("code expected")
        self.version = version
        # name & filename
        self.name = obj.name
        self.filename = obj.filename
        # flags
        reflags = 0
        self.flags = set()
        for flag in CodeFlag:
            if obj.flags & flag:
                self.flags.add(flag)
                reflags |= flag
        if reflags != obj.flags:
            raise PythonError("Unk flags {:x}".format(obj.flags & ~reflags))
        # varnames
        self.varnames = obj.varnames
        # XXX flag behavior noticed on 2.1.3 - wtf?
        if CodeFlag.newlocals in self.flags and obj.nlocals != len(obj.varnames):
            raise PythonError("Strange nlocals: {} {}".format(obj.nlocals, obj.varnames))
        # args
        self._init_args(obj)
        # freevars & cellvars
        self.freevars = obj.freevars
        self.cellvars = obj.cellvars
        # stacksize
        self.stacksize = obj.stacksize
        # consts
        self.consts = []
        for const in obj.consts:
            if isinstance(const, MarshalCode):
                self.consts.append(Code(const, version))
            elif isinstance(const, MarshalDict):
                self.consts.append(CodeDict(const.val))
            else:
                self.consts.append(from_marshal(const, version))
        # names
        self.names = obj.names
        # firstlineno is not the same as the first line of code, store it separately
        self.firstlineno = obj.firstlineno
        # line numbers
        if self.firstlineno is None:
            self.lnotab = None
        else:
            self.lnotab = parse_lnotab(obj.firstlineno, obj.lnotab, len(obj.code))
        # code
        self.rawcode = obj.code
        self.code = Bytecode(version, self)

    def _init_args(self, obj):
        if obj.argcount is None:
            # python < 1.3
            self.args = []
            self.kwargs = []
            self.varargs = None
            self.varkw = None
        else:
            if obj.argcount + obj.kwonlyargcount > obj.nlocals:
                raise PythonError("More args than locals")
            argidx = 0
            self.args = self.varnames[argidx:argidx + obj.argcount]
            argidx += obj.argcount
            self.kwargs = self.varnames[argidx:argidx + obj.kwonlyargcount]
            argidx += obj.kwonlyargcount
            if CodeFlag.varargs in self.flags:
                if argidx == obj.nlocals:
                    raise PythonError("More args than locals")
                self.varargs = self.varnames[argidx]
                argidx += 1
            else:
                self.varargs = None
            if CodeFlag.varkeywords in self.flags:
                if argidx == obj.nlocals:
                    raise PythonError("More args than locals")
                self.varkw = self.varnames[argidx]
                argidx += 1
            else:
                self.varkw = None

    def show(self):
        yield 'CODE'
        # name
        yield 'name: {} from {}'.format(self.name, self.filename)
        # flags
        yield 'flags: {}'.format(', '.join(flag.name for flag in self.flags))
        # args
        args = self.args[:]
        if self.varargs is not None:
            args.append('*{}'.format(self.varargs))
        elif self.kwargs:
            args.append('*')
        if self.kwargs:
            args += self.kwargs
        if self.varkw is not None:
            args.append('**{}'.format(self.varkw))
        if args:
            yield 'args: {}'.format(', '.join(args))
        # vars
        if self.varnames:
            yield 'vars: {}'.format(', '.join(self.varnames))
        if self.freevars:
            yield 'freevars: {}'.format(', '.join(self.freevars))
        if self.cellvars:
            yield 'cellvars: {}'.format(', '.join(self.cellvars))
        # consts
        yield 'consts:'
        for idx, const in enumerate(self.consts):
            if isinstance(const, (Code, CodeDict)):
                yield from indent(preindent(idx, const.show()))
            else:
                yield '\t{}: {}'.format(idx, const.show(None))
        # and the actual bytecode
        import binascii
        if self.names:
            yield 'names: {}'.format(', '.join(self.names))
        if self.stacksize is not None:
            yield "stacksize: {}".format(self.stacksize)
        yield "code:"
        for op in self.code.ops:
            yield "\t{}".format(op)
        if self.firstlineno is not None:
            yield "line: {} {}".format(self.firstlineno, self.lnotab)
