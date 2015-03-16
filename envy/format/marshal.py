"""Reads the marshal format.

Marshal is a schizophrenic serialization format.  On one hand, it's explicitely
meant to handle pyc file serialization only.  On the other, it has certain
features that are never used in pyc files, or used in very limitted ways.

For pyc serialization, there's only one thing that marshal has to do: store
python code objects.  Since code objects are not standalone, but reference
other objects, marshal also has to support all types that could possibly be
referenced from a code object.

The code object consists of the following fields that reference other objects:

- the bytecode itself and the line number table: byte strings
- various name lists: lists/tuples of native strings (ie. unicode on py3k,
  byte strings otherwise)
- const list: a list/tuple

For reasons unknown, where list/tuple is mentioned above, python 1.0 uses
a list and python 1.1+ uses a tuple.

The following kinds of const can appear in the const list:

- an actual const object appearing directly in the source, ie. one of:

  - int/long/float/complex from a literal
  - string from a literal, whether byte or unicode
  - None
  - Ellipsis
  - in py3k only, True and False (before py3k, True and False were builtin
    names that could be overriden just fine, not literals)
  - a tuple consisting only of const objects

  List, dict and set displays in the source, as well as tuple displays
  with non-const contents, are compiled to bytecodes constructing the
  relevant object.  There is one exception to that, described below.

- a frozenset of const objects, emitted by the compiler when it optimizes
  an 'in' expression where the second argument is a set display of const
  objects.  For example, when "abc in {1, 2, 3}" is compiled, the set is
  internally converted to a frozenset (since it can never be modified) and
  dumped like a normal const object.

- in python < 1.3 only, a dict mapping local variable names
  to their fast slot IDs, referenced by RESERVE_FAST opcode.

- code objects corresponding to embedded functions, classes, lamdas,
  comprehensions, etc.  Passed to MAKE_FUNCTION or __build_class__.

This makes for the following marshalable types you can meet in .pyc:

- code
- NoneType/ellipsis/int/long/float/complex
- bool, for py3k+
- bytes/str/unicode (in addition, some of these may be marked as interned
  in the marshal file, and they will be interned when being loaded)
- tuple
- list, for code object attributes in python 1.0 only
- dict, for python < 1.3 only (for RESERVE_FAST)
- frozenset (for py3k only)
- references to objects mentioned earlier as ref-generating.  In py3k,
  supported for arbitrary objects and used for CSE.  Before py3k, used only
  for interned strings.

In addition, marshal supports the following features you won't ever see in
a pyc file:

- bool type (in python 2)
- list type (in python 1.1+)
- dict type (in python 1.3+)
- set type
- StopIteration singleton (I have no idea what it is for.)
- recursive structure support (ie. a = []; a.append(a); a can be marshaled) -
  only supported in py3k

In addition, there's an encoding artifact: the NULL object type.
It corresponds to a C-level NULL, ie. an unfilled slot.  The only place where
it can occur in a proper marshal stream is as an end marker for dict.

Fun fact: marshal.loads can be used to make a recursive tuple, and it's likely
the only way to ever get one:

    >>> a = marshal.loads(b'\xa8\x01\x00\x00\x00r\x00\x00\x00\x00')
    >>> a
    ((...),)
    >>> a[0] is a
    True
    >>> type(a)
    <class 'tuple'>

Now, continuing with the schizophrenia theme, marshal documentation claims
the format is extremely volatile and may change between Python versions
in non-backwards compatible way.  However, it also defines a dump function
that has a "version" parameter, selecting which of the historical versions
it should dump to, with no corresponding parameter on load function (it's
supposed to accept all format versions).  The format itself is extensible
by adding new type codes, and that is exactly what happened over time.
The versions supposedly are:

- 0: original format
- 1 (python 2.4): supports interned byte strings
- 2 (python 2.5): float/complex are stored in binary format instead of text
- 3 (python 3.4 prereleases): supports references (ie. object sharing and
  recursive data structures) and interned unicode strings
- 4 (python 3.4): has a few optimized storage modes (for ascii-only unicode
  strings and short tuples)

The new versions only add type codes and thus there's no need for a version
tag on the serialized data.  You can just get the newest python and read
any marshal object ever created.

The problem is, it doesn't really work that way.

The first (minor) issue is interned byte strings.  The support for these has
been removed in py3k - the type codes are no longer recognised by load, and
dump will emit the non-interned code regardless of version.  This alone
wouldn't be that bad, but they re-used the type code for interned *unicode*
strings in marshal version 3.  So you can make a marshal stream that will
be loaded differently by py2 and py3 - stuff will be loaded as byte strings
in py2, and as unicode strings in py3k.  Further, the 'R' code used for
deduplication of interned strings in py2 is not supported by py3k, being
replaced by generic references ('r' code).

The second, much bigger issue is that the code format keeps changing between
python versions.  It's not about the bytecode format: while it changes too
(and much more often), the problem is in code type growing new fields and
desyncing the reader.  The first time such change happened, the type code
was changed from 'C' to 'c'.  However, on later changes, nothing like that
was done.  The complete list of such changes is:

- python 1.3: added argcount, nlocals, flags, varnames - to support keyword
  parameters and new local variable storage.  Changes type code from 'C'
  to 'c'.
- python 1.5: added stacksize, firstlineno, lnotab.
- python 2.1: added cellvars and freevars (for closure support).
- python 2.3: bumped a bunch of fields from 16-bit to 32-bit.
- python 3.0: added kwonlyargcount.

So, to properly read a marshal stream containing code objects, you need to
know the Python version that emitted it.  We get this information from the
pyc file signature.  This is why we have our own marshal implementation,
instead of using the marshal module: it'd tie us to the python version
we're running on, and perhaps a few more using the same format.

This implementation is only meant to support marshal streams found in pyc
files.  To avoid surprises in later stages, it heavily validates the input
matches what the corresponding python version would really emit.
"""

# TODO: check the signedness of le4/le2 everywhere

import struct
import binascii

from .helpers import read_byte, read_le, read_bytes, FormatError
from envy.show import preindent, indent

class MarshalError(FormatError):
    pass


# nodes

class MarshalNode:
    """A marshal object.  Does not include the NULL type - it's represented
    by a None instead."""
    __slots__ = ()

    def show(self):
        yield str(self)


# singletons

class MarshalNone(MarshalNode):
    """A marshal None singleton."""
    __slots__ = ()

    def __str__(self):
        return 'None'


class MarshalBool(MarshalNode):
    """A marshal bool value."""
    __slots__ = 'val',

    def __init__(self, val):
        self.val = val

    def __str__(self):
        return str(self.val)


class MarshalEllipsis(MarshalNode):
    """A marshal ellipsis singleton."""
    __slots__ = ()

    def __str__(self):
        return "..."


# primitive types

class MarshalInt(MarshalNode):
    """A marshal int value.  It's used for Python-level ints, no matter how
    they were represented in marshal stream - it includes INT64 for python 2
    and LONG for python 3."""
    __slots__ = 'val',

    def __init__(self, val):
        self.val = val

    def __str__(self):
        return str(self.val)


class MarshalLong(MarshalNode):
    """A marshal long value.  Only used for py2 - py3k TYPE_LONG is instead
    loaded as MarshalInt."""
    __slots__ = 'val',

    def __init__(self, val):
        self.val = val

    def __str__(self):
        return str(self.val) + 'L'


class MarshalFloat(MarshalNode):
    """A marshal float value, loaded from text or binary format."""
    __slots__ = 'val',

    def __init__(self, val):
        self.val = val

    def __str__(self):
        return str(self.val)


class MarshalComplex(MarshalNode):
    """A marshal complex value, loaded from text or binary format."""
    __slots__ = 'val',

    def __init__(self, val):
        self.val = val

    def __str__(self):
        return str(self.val)


class MarshalString(MarshalNode):
    # TODO: should we remember whether string is interned?
    """A marshal byte string value.  Corresponds to py2 str and py3k bytes.
    Information on interning is lost."""
    __slots__ = 'val',

    def __init__(self, val):
        self.val = val

    def __str__(self):
        return repr(self.val)


class MarshalUnicode(MarshalNode):
    # TODO: should we remember whether string is interned?
    """A marshal unicode string value.  Corresponds to py2 unicode and py3k
    str.  Information on interning is lost."""
    __slots__ = 'val',

    def __init__(self, val):
        self.val = val

    def __str__(self):
        return repr(self.val)


# containers

class MarshalTuple(MarshalNode):
    """A marshal tuple.  val is actually a list."""
    __slots__ = 'val'

    def __init__(self, val):
        self.val = val

    def __str__(self):
        return '({}{})'.format(', '.join(str(v) for v in self.val), ',' if len(self.val) == 1 else '')


class MarshalList(MarshalNode):
    """A marshal list.  Should only occur in Python 1.0."""
    __slots__ = 'val'

    def __init__(self, val):
        self.val = val

    def __str__(self):
        return '[{}]'.format(', '.join(str(v) for v in self.val))


class MarshalDict(MarshalNode):
    """A marshal dict.  Should only occur before Python 1.3.  val is actually
    a list of (k, v) pairs."""
    __slots__ = 'val'

    def __init__(self, val):
        self.val = val

    def __str__(self):
        return '{{{}}}'.format(', '.join('{}: {}'.format(k, v) for k, v in self.val))


class MarshalFrozenset(MarshalNode):
    """A marshal frozenset.  val is actualy a list."""
    __slots__ = 'val'

    def __init__(self, val):
        self.val = val

    def __str__(self):
        return 'frozenset([{}])'.format(', '.join(str(v) for v in self.val))


# code

class MarshalCode(MarshalNode):
    # TODO: figure out when ?/None names were changed to <module>/<lambda>
    # TODO: don't decode filename to unicode on py2, that's recipe for disaster
    """A marshal code object.  Fields are:

    - argcount (int or None): filled with None if not present (old argument
      passing conventions are used in this case, so the field doesn't make
      sense)
    - kwonlyargcount (int): filled with 0 if not present
    - nlocals (int or None): filled with None if not present (get this
      information from RESERVE_FAST instead)
    - stacksize (int or None): filled with None if not present
    - flags (int): filled with 0 if not present
    - code (bytes): the bytecode
    - consts (list of MarshalNode): the consts used by the bytecode
    - names (list of str): the names used by the bytecode
    - varnames (None or list of str): the fast variable names, filled with None
      if not present (get this information from RESERVE_FAST instead)
    - freevars (list of str): filled with [] if not present
    - cellvars (list of str): filled with [] if not present
    - filename (str)
    - name(str or None): can be None on ancient python versions for lambdas
    - firstlineno (int or None): filled with None if not present
    - lnotab (bytes or None): filled with None if not present (get this
      information from SET_LINE instead)

    For python 2, the strings corresponding to source-level identifiers are
    converted to unicode through ascii decoding, to make handling uniform in
    further stages (py2 doesn't support non-ascii in identifiers anyway).
    """
    __slots__ = (
        'argcount',
        'kwonlyargcount',
        'nlocals',
        'stacksize',
        'flags',
        'code',
        'consts',
        'names',
        'varnames',
        'freevars',
        'cellvars',
        'filename',
        'name',
        'firstlineno',
        'lnotab',
    )

    def __str__(self):
        return '<code>'

    def show(self):
        yield "CODE"
        yield "args: {} + {}, locals: {}, stacksize: {}".format(self.argcount, self.kwonlyargcount, self.nlocals, self.stacksize)
        yield "flags: {:x}".format(self.flags)
        yield "code: {}".format(binascii.b2a_hex(self.code))
        yield "consts:"
        for idx, const in enumerate(self.consts):
            yield from indent(preindent(idx, const.show()))
        yield "names: {}".format(', '.join(self.names))
        if self.varnames is not None:
            yield "\tvarnames: {}".format(', '.join(self.varnames))
        yield "freevars: {}".format(', '.join(self.freevars))
        yield "cellvars: {}".format(', '.join(self.cellvars))
        yield "filename: {}".format(self.filename)
        yield "name: {}".format(self.name)
        if self.firstlineno is not None:
            yield "lines: {} then {}".format(self.firstlineno, binascii.b2a_hex(self.lnotab))

# A marshal stream is basically a tree of objects: you read a single object
# from the stream, and each object can contain inner objects.  Every object
# starts with a byte containing the type code and the reference flag.  Further
# data stored for the object, if any, is determined by the type code.  There
# is no framing, no way to "jump" across objects, nor an ending marker: you
# end reading when you got enough data to deserialize the object.
#
# The reference flag (introduced in version 3) determines whether the object
# should be stored in the reference pool, to be used later by the 'reference'
# type (to represent non-tree object graphs).  The reference pool is just
# a list, filled as you start loading the objects, and the references are by
# index in this list.  Not all types support being added to the reference pool.
#
# Python 2, since marshal version 1, also has a reference pool using the same
# rules, but it's used only for interned strings, and the type code is used
# to mark referencable objects instead of the reference flag.  Also, it uses
# a different type code for the actual references.

# reader functions

MARSHAL_CODES = {}

def _code(code, flag=None):
    """Register a reader function. code is the type code, passed as string
    for clarity.  flag is the attribute of version that determines whether
    the function will be considered for execution.  If it's None,
    the function is always active.  If it's prefixed with '!' (eg. '!py3k'),
    the function is active if the flag is false.  Otherwise, the function
    is active if the flag is True."""
    def inner(function):
        MARSHAL_CODES.setdefault(ord(code), []).append((function, flag))
        return function
    return inner

# all these functions take the reference flag as the second argument

# singletons - nothing interesting.

@_code('0')
def load_null(ctx, flag):
    return None

@_code('N')
def load_none(ctx, flag):
    return MarshalNone()

@_code('.', 'has_ellipsis')
def load_ellipsis(ctx, flag):
    return MarshalEllipsis()

# bool - actually supported since 2.2 by marshal, but can only happen in pyc
# on py3k, since otherwise True and False are compiled to LOAD_GLOBAL.

@_code('T', 'has_bool_literal')
def load_true(ctx, flag):
    return MarshalBool(True)

@_code('F', 'has_bool_literal')
def load_false(ctx, flag):
    return MarshalBool(False)

# 'S' not supported (StopIteration)

# ints and longs.  This is somewhat complex.
#
# For Python 2:
#
# - ints that fit in 32 bits are represented by 'i'.  This covers all ints
#   on 32-bit builds.
#
# - ints that fit in 64 bits (but not 32) are represented by 'I'.  This is
#   only possible on 64-bit builds.
#
# - larger ints are not possible.  If you attempt to use them in the source,
#   you get a compile error (pre 2.2), or they're automatically promoted
#   to long and stored as such.
#
# - longs are represented by 'l'.
#
# - 'l' is deserialized as long
#
# - 'i' is deserialized as int
#
# - 'I' is deserialized as follows:
#
#   - as int on 64-bit builds
#   - as int (with a warning and a truncation) on 32-bit builds pre 2.2
#   - as long on 32-bit builds on 2.2+
#
# This slightly violates version-independence of pyc files for 2.2 and above:
# 2**32 will be stored as LONG by a 32-bit build (and deserialized as long),
# but a 64-bit build will store it as INT64 (and deserialize as int).  So, if
# a 64-bit build loads a pyc file compiled by a 32-bit build, it'll see a long
# where it would normally have an int.  We deserialize them as ints, since
# that's definitely what the compiler has seen if we come across one.
#
# For Python 3:
#
# - ints that fit in 32 bits are represented by 'i'
# - larger ints are represented by 'l'
# - 'I' is gone, and so is long
# - both 'i' and 'l' are deserialized as int
#
# Life is good.

@_code('i')
def load_int(ctx, flag):
    return ctx.ref(MarshalInt(ctx.le4s()), flag)

@_code('I', '!py3k')
def load_int64(ctx, flag):
    return ctx.ref(MarshalInt(ctx.le8s()), flag)

@_code('l')
def load_long(ctx, flag):
    n = ctx.le4s()
    res = 0
    for x in range(abs(n)):
        res |= ctx.le2() << x * 15
    if n < 0:
        res = -res
    if ctx.version.py3k:
        type_ = MarshalInt
    else:
        type_ = MarshalLong
    return ctx.ref(type_(res), flag)

# float and complex.  There are two formats: old text one and new binary one.
# The new ones are used since marshal version 1, which is Python 2.5.

@_code('f', '!has_bin_float')
def load_float(ctx, flag):
    len_ = ctx.byte()
    res = float(ctx.bytes(len_).decode('ascii'))
    return ctx.ref(MarshalFloat(res), flag)

@_code('x', ('has_complex', '!has_bin_float'))
def load_complex(ctx, flag):
    len_ = ctx.byte()
    re = float(ctx.bytes(len_).decode('ascii'))
    len_ = ctx.byte()
    im = float(ctx.bytes(len_).decode('ascii'))
    return ctx.ref(MarshalComplex(complex(re, im)), flag)

@_code('g', 'has_bin_float')
def load_bin_float(ctx, flag):
    res, = struct.unpack('<d', ctx.bytes(8))
    return ctx.ref(MarshalFloat(res), flag)

@_code('y', 'has_bin_float')
def load_bin_complex(ctx, flag):
    re, im = struct.unpack('<dd', ctx.bytes(16))
    return ctx.ref(MarshalComplex(complex(re, im)), flag)

# A byte string.

@_code('s')
def load_string(ctx, flag):
    len_ = ctx.le4()
    res = MarshalString(ctx.bytes(len_))
    return ctx.ref(res, flag)

# A unicode string.

@_code('u')
@_code('t', 'has_marshal_ref')
def load_unicode(ctx, flag):
    n = ctx.le4()
    b = ctx.bytes(n)
    res = b.decode('utf-8', 'surrogatepass')
    return ctx.ref(MarshalUnicode(res), flag)

# An interned string.  In py2, this works like 's' and also adds the string
# to the reference pool, which is otherwise unused.  In py3k, it works like
# 'u'.

@_code('t', 'has_str_intern')
def load_intern(ctx, flag):
    return load_string(ctx, True)

# ascii strings - optimized storage of unicode strings on py3k.  Nothing
# to see here, move along.

def _load_ascii(ctx, flag, len_):
    s = ctx.bytes(len_)
    res = MarshalUnicode(s.decode('ascii'))
    return ctx.ref(res, flag)

@_code('z', 'has_marshal_opt')
@_code('Z', 'has_marshal_opt') # interned version
def load_short_ascii(ctx, flag):
    return _load_ascii(ctx, flag, ctx.byte())

@_code('a', 'has_marshal_opt')
@_code('A', 'has_marshal_opt') # interned version
def load_ascii(ctx, flag):
    return _load_ascii(ctx, flag, ctx.le4())

# tuple. There are two versions: original one, and short one (added in marshal
# version 4). Short is limitted to 255 items.

def _load_raw_tuple(ctx, flag, len_):
    res = MarshalTuple([])
    ctx.ref(res, flag)
    for x in range(len_):
        res.val.append(ctx.load_object())
    return res

@_code('(')
def load_tuple(ctx, flag):
    return _load_raw_tuple(ctx, flag, ctx.le4())

@_code(')', 'has_marshal_opt')
def load_small_tuple(ctx, flag):
    return _load_raw_tuple(ctx, flag, ctx.byte())

# list

@_code('[', 'consts_is_list')
def load_list(ctx, flag):
    len_ = ctx.le4()
    res = MarshalList([])
    ctx.ref(res, flag)
    for x in range(len_):
        res.val.append(ctx.load_object())
    return res

# frozenset

@_code('>', 'has_frozenset')
def load_frozenset(ctx, flag):
    len_ = ctx.le4()
    res = MarshalFrozenset([])
    ctx.ref(res, flag)
    for x in range(len_):
        res.val.append(ctx.load_object())
    return res

# '<' not supported (set)

# dict

@_code('{', '!has_new_code')
def load_dict(ctx, flag):
    res = MarshalDict([])
    ctx.ref(res, flag)
    while True:
        key = ctx.load_object(nullable=True)
        if key is None:
            break
        val = ctx.load_object()
        res.val.append((key, val))
    return res

# code - old and new

@_code('C', '!has_new_code')
def load_ancient_code(ctx, flag):
    res = MarshalCode()
    ctx.ref(res, flag)
    res.argcount = None
    res.kwonlyargcount = 0
    res.nlocals = None
    res.stacksize = None
    res.flags = 0
    res.code = ctx.load_bytes()
    res.consts = ctx.load_tuple()
    res.names = ctx.load_str_tuple()
    res.varnames = None
    res.freevars = []
    res.cellvars = []
    res.filename = ctx.load_str()
    res.name = ctx.load_str(True)
    res.firstlineno = None
    res.lnotab = None
    return res

@_code('c', 'has_new_code')
def load_code(ctx, flag):
    res = MarshalCode()
    ctx.ref(res, flag)
    res.argcount = ctx.lea()
    if ctx.version.py3k:
        res.kwonlyargcount = ctx.le4()
    else:
        res.kwonlyargcount = 0
    res.nlocals = ctx.lea()
    if ctx.version.has_stacksize:
        res.stacksize = ctx.lea()
    else:
        res.stacksize = None
    res.flags = ctx.lea()
    res.code = ctx.load_bytes()
    res.consts = ctx.load_tuple()
    res.names = ctx.load_str_tuple()
    res.varnames = ctx.load_str_tuple()
    if ctx.version.has_closure:
        res.freevars = ctx.load_str_tuple()
        res.cellvars = ctx.load_str_tuple()
    else:
        res.freevars = []
        res.cellvars = []
    res.filename = ctx.load_str()
    res.name = ctx.load_str()
    if ctx.version.has_stacksize:
        res.firstlineno = ctx.lea()
        res.lnotab = ctx.load_bytes()
    else:
        res.firstlineno = None
        res.lnotab = None
    return res

# references. 'R' is only supposed to exist in py2 for interned strings.
# 'r' is only supposed to exist in marshal version 3 and up.  We store both
# kinds of referencable objects in the same place, since the mechanisms are
# mutually exclusive.

@_code('R', 'has_str_intern')
@_code('r', 'has_marshal_ref')
def load_ref(ctx, flag):
    idx = ctx.le4()
    try:
        return ctx.refs[idx]
    except IndexError:
        raise MarshalError("Invalid reference")


class _MarshalContext:
    def __init__(self, fp, version):
        self.fp = fp
        self.version = version
        self.refs = []
        self.level = 0

    def load_object(self, nullable=False):
        """Loads an object from file, returns a MarshalNode.

        If nullable is True, NULL is allowed and is returned as None.
        Otherwise, NULL raises an exception.
        """
        code = self.byte()
        if self.version.py3k:
            ref = bool(code & 0x80)
            code &= 0x7f
        else:
            ref = False
        for fun, flags in MARSHAL_CODES.get(code, []):
            if flags is None:
                flags = []
            if not isinstance(flags, list):
                flags = [flags]
            ok = True
            for flag in flags:
                if flag.startswith('!'):
                    ok = ok and not getattr(self.version, flag[1:])
                else:
                    ok = ok and getattr(self.version, flag)
            if ok:
                res = fun(self, ref)
                break
        else:
            raise MarshalError("marshal type unknown ({!r})".format(bytes([code])))
        if res is None and not nullable:
            raise MarshalError("NULL in a funny place")
        return res

    def load_tuple(self):
        """Loads a tuple from file, returns it as a list of MarshalNode.

        On Python 1.0, loads a marshal list instead.
        """
        obj = self.load_object()
        if self.version.consts_is_list:
            typ = MarshalList
        else:
            typ = MarshalTuple
        if not isinstance(obj, typ):
            raise MarshalError("{} expected, got {}".format(typ, type(obj)))
        return obj.val

    def load_bytes(self):
        """Loads a byte string from file, returns the raw bytes."""
        obj = self.load_object()
        if not isinstance(obj, MarshalString):
            raise MarshalError("bytes expected, got {}".format(type(obj)))
        return obj.val

    def pass_str(self, obj, nullable=False):
        """Takes a MarshalNode corresponding to a native string, decodes
        through ascii for py2, returns raw str.  If nullable is True, marshal
        None is allowed as well and is returned as None."""
        if isinstance(obj, MarshalNone) and nullable:
            return None
        if self.version.py3k:
            if not isinstance(obj, MarshalUnicode):
                raise MarshalError("string expected, got {}".format(type(obj)))
            return obj.val
        else:
            if not isinstance(obj, MarshalString):
                raise MarshalError("string expected, got {}".format(type(obj)))
            return obj.val.decode('ascii')

    def load_str(self, nullable=False):
        """Like pass_str, but loads from file."""
        return self.pass_str(self.load_object(), nullable)

    def load_str_tuple(self):
        """Loads a tuple of native strings from file.  The strings are decoded
        through ascii for py2.  Returns a list of raw str objects."""
        return [self.pass_str(x) for x in self.load_tuple()]

    def le2(self):
        """Reads a raw unsigned 16-bit int from file."""
        return read_le(self.fp, 2)

    def lea(self):
        """Reads a raw unsigned 16-bit or 32-bit int from file, as appropriate
        for code object fields for current Python version."""
        return read_le(self.fp, 4 if self.version.has_le4 else 2)

    def le4(self):
        """Reads a raw unsigned 32-bit int from file."""
        return read_le(self.fp, 4)

    def le4s(self):
        """Reads a raw signed 32-bit int from file."""
        return read_le(self.fp, 4, signed=True)

    def le8s(self):
        """Reads a raw signed 64-bit int from file."""
        return read_le(self.fp, 8, signed=True)

    def bytes(self, len_):
        """Reads given amount of raw bytes from file."""
        return read_bytes(self.fp, len_)

    def byte(self):
        """Reads a raw byte from file."""
        return read_byte(self.fp)

    def ref(self, obj, flag):
        """Maybe stores the object in the reference pool, depending on
        the flag.  Returns the object."""
        if flag:
            self.refs.append(obj)
        return obj


def load_marshal(fp, version):
    """Deserializes a marshal stream from a given file.  Returns
    a MarshalNode."""
    return _MarshalContext(fp, version).load_object()
