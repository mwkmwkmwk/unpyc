"""The big list of Python versions, with their features relevant for
decompilation.

The pyc files start with a signature that determines the version.  Before
Python 1.3, the signature is 0x9999XX, where XX is a serial number.  Since 1.3,
signature has a unique number in low 16 bits, '\r\n' in high 16 bits.

We support all final versions of Python since 1.0.1.  Since stackless makes
no changes to the bytecode format, it's supported as well.  In other words, we
*don't* support:

- Python 0.9.x (good luck compiling them, the CVS history is pretty fucked up
  for them and there are missing files)
- alpha, beta, and rc releases (though it could be done rather easily)
- arbitrary svn/hg revisions
- anything that's not official CPython (or stackless): modified versions of
  the interpreter, PyPy, Jython, any other implementation.

Side note: apparently, MPW (MacOS C compiler) has \r and \n swapped.  This is,
in fact, the reason for incorporating \r\n in the signature.  So, in theory
there are pyc files with these bytes swapped in the header, and they differ
by having \r and \n backwards.  Which, of course, is impossible to properly
decompile - you have no way of knowing whether a \n in a sting is really
a \n in the source, or \x0a used for its exact byte value.  Such files are,
effectively, hopelessly mangled.

Python 1.2, instead of incorporating these into the signature verbatim,
considers the signature to be (0x999903L ^ (('\n'^10L)<<16) ^ (('\r'^13L)<<8)),
so that it comes out identical to 1.1 on sane platforms.  So we could also
come across a file with signature 0x9e9e03 - this is Python 1.2 with mangled
newlines.  Python 1.1 and earlier don't care about this brain damage.

Anyhow, it's a mess.  If you somehow happen to come across such a file, you're
on your own.
"""

PYC_VERSIONS = {}

def _v(x):
    """Build 1.3+ signature."""
    return x | 0x0a0d0000

class PycVersion:
    def __init__(self, name, bases, namespace):
        for base in bases:
            self.__dict__.update(base.__dict__)
        self.__dict__.update(namespace)
        if hasattr(self, 'code'):
            PYC_VERSIONS[self.code] = self
            if self.has_U:
                PYC_VERSIONS[self.code + 1] = self

    def match(self, flags):
        if flags is None:
            flags = []
        if not isinstance(flags, (list, tuple)):
            flags = [flags]
        ok = True
        for flag in flags:
            if flag.startswith('!'):
                if getattr(self, flag[1:]):
                    return False
            else:
                if not getattr(self, flag):
                    return False
        return True

# 0x949494 used in 0.9.8, ??? used before
# 0x999901 used in 0.9.9

# Python 1

class Pyc10(metaclass=PycVersion):
    code = 0x999902
    name = "Python 1.0"

    # co_consts and co_names are lists instead of tuples
    consts_is_list = True
    # expression statements are always printed (as opposed to just
    # top-level in interactive mode)
    always_print_expr = True
    # has default arguments
    has_def_args = False
    # has new code marshal type, has co_varnames, doesn't have RESERVE_FAST - all for kwargs
    has_new_code = False
    # has 3-argument raise
    has_new_raise = False
    # has ellipsis (...)
    has_ellipsis = False
    # has access statement
    has_access = True
    # has power operator (**)
    has_power = False
    # has new slices (a[b:c:d])
    has_new_slice = False
    # has complex numbers
    has_complex = False
    # has marshal 'I' code
    has_marshal_int64 = False
    # has stacksize and lnotab
    has_stacksize = False
    # has assert statement
    has_assert = False
    # has zero-argument raise (aka reraise) statement
    has_reraise = False
    # has unicode type
    has_unicode = False
    # has variadic function calls (a = f(a, b, *c, **d))
    has_var_call = False
    # has inplace operators (+=, *=, ...)
    has_inplace = False
    # has DUP_TOPX opcode
    has_dup_topx = False
    # has ROT_FOUR opcode
    has_rot_four = False
    # has unpack sequence (as opposed to separate tuple and list unpack)
    has_unpack_sequence = False
    # has dedicated import star opcode
    has_import_star = False
    # has import as
    has_import_as = False
    # has print >>a, b
    has_print_to = False
    # has list comprehensions
    has_listcomp = False
    # has possible variable collisions in list comprehensions (heh)
    has_listcomp_collide = False
    # has EXTENDED_ARG
    has_extended_arg = False
    # has -U option to interpreter
    has_U = False
    # has nested functions with closures
    has_closure = False
    # has new continue opcode, capable of busting except blocks
    has_new_continue = False
    # has iterators
    has_iter = False
    # has new divide operators (true and floor)
    has_new_divide = False
    # has short assert sequence
    has_short_assert = False
    # has reversed order of k, v evaluation in {k: v}
    has_reversed_kv = True
    # numeric fields in code are 32-bit instead of 16-bit
    has_le4 = False
    # has SET_LIENENO
    has_set_lineno = True
    # has peephole optimier
    has_peephole = False
    # has interned bytestrings in marshal
    has_str_intern = False
    # has sets and frozensets
    # TODO rename
    has_frozenset = False
    # has binary float format in marshal
    has_bin_float = False
    # generic py3k flag - unicode strings, kw-only args, ...
    py3k = False
    # has complex (tuple) arguments - def f(a, (b, c)):
    has_complex_args = True
    # has old slice opcodes - used in parallel to new ones before 3.0 when
    # possible
    has_old_slice = True
    # has True/False as compile-time literals (as opposed to builtins)
    has_bool_literal = False
    # has print statement
    has_print = True
    # has exec statement
    has_exec = True
    # has old divide operator
    has_old_divide = True
    # has unary repr operator
    has_repr = True
    # has raise x from y
    has_raise_from = False
    # has source size in pyc
    has_size = False
    # has marshal optimized formats
    has_marshal_opt = False
    # has marshal reference support
    has_marshal_ref = False

class Pyc11(Pyc10):
    code = 0x999903
    name = "Python 1.1/1.2"
    consts_is_list = False
    always_print_expr = False
    has_def_args = True
    # the following things are different between 1.1 and 1.2 (which have
    # the same pyc code):
    #
    # - lambdas have a name of '<lambda>' instead of None
    # - docstrings are supported
    # - dotted names are allowed in imports

class Pyc13(Pyc11):
    code = _v(11913)
    name = "Python 1.3"
    has_new_code = True
    has_new_raise = True

class Pyc14(Pyc13):
    """Introduces complex, ellipsis, 3-arg slices, ** operator.
    Gets rid of access support.
    """
    code = _v(5892)
    name = "Python 1.4"
    has_ellipsis = True
    has_access = False
    has_power = True
    has_new_slice = True
    has_complex = True

class Pyc15(Pyc14):
    """Introduces stacksize and lnotab."""
    code = _v(20121)
    name = "Python 1.5"
    has_marshal_int64 = True
    has_stacksize = True
    has_assert = True

class Pyc16(Pyc15):
    code = _v(50428)
    name = "Python 1.6"
    has_reraise = True
    has_unicode = True
    has_var_call = True

# Python 2

class Pyc20(Pyc16):
    code = _v(50823)
    name = "Python 2.0"
    has_U = True
    has_inplace = True
    has_dup_topx = True
    has_rot_four = True
    has_unpack_sequence = True
    has_import_star = True
    has_import_as = True
    has_print_to = True
    has_listcomp = True
    has_listcomp_collide = True
    has_extended_arg = True

class Pyc21(Pyc20):
    code = _v(60202)
    name = "Python 2.1"
    has_closure = True
    has_new_continue = True
    has_listcomp_collide = False

class Pyc22(Pyc21):
    code = _v(60717)
    name = "Python 2.2"
    has_iter = True
    has_new_divide = True
    has_yield_stmt = True

class Pyc23(Pyc22):
    # 62021 used in prealpha
    code = _v(62011)
    name = "Python 2.3"
    has_short_assert = True
    has_reversed_kv = False
    has_le4 = True
    has_set_lineno = False
    has_peephole = True

class Pyc24(Pyc23):
    # 62041 used in a1-a2
    # 62051 used in a3
    code = _v(62061)
    name = "Python 2.4"
    has_str_intern = True

class Pyc25(Pyc24):
    # 62071 used in prealpha
    # 62081 used in prealpha
    # 62091 used in prealpha
    # 62092 used in alphas and b1-b2
    # 62101 used in unreleased beta
    # 62111 used in b3
    # 62121 used in c1
    code = _v(62131)
    name = "Python 2.5"
    has_frozenset = True
    has_bin_float = True

class Pyc26(Pyc25):
    # 62151 used in prealpha
    code = _v(62161)
    name = "Python 2.6"

class Pyc27(Pyc26):
    # 62171 used in preaplha
    # 62181 used in preaplha
    # 62191 used in preaplha
    # 62201 used in preaplha
    code = _v(62211)
    name = "Python 2.7"

# Python 3

# 3000, 3010, 3020, 3030, 3040, 3050, 3060, 3061, 3071, 3081, 3091, 3101
# used in development branch

class Pyc30(Pyc27):
    # 3103 used in a1-a3
    # 3111 used in a4
    code = _v(3131)
    name = "Python 3.0"

    has_U = False
    has_str_intern = False
    py3k = True
    has_bool_literal = True
    has_complex_args = False
    has_old_slice = False
    has_print = False
    has_exec = False
    has_old_divide = False
    has_repr = False
    has_raise_from = True

class Pyc31(Pyc30):
    # 3141 used in prealpha
    code = _v(3151)
    name = "Python 3.1"

class Pyc32(Pyc31):
    # 3160 used in prealpha
    # 3170 used in a1
    code = _v(3180)
    name = "Python 3.2"
    has_dup_topx = False
    has_rot_four = False
    has_marshal_int64 = False

class Pyc33(Pyc32):
    # 3190 used in prealpha
    # 3200 used in prealpha
    # 3210 used in prealpha
    # 3220 used in a1-a3
    code = _v(3230)
    name = "Python 3.3"
    has_size = True

class Pyc34(Pyc33):
    # 3250, 3260, 3270 used in prealpha
    # 3280 used in a1-a3
    # 3290 used in unreleased alpha
    # 3300 used in a4, betas, rc1
    code = _v(3310)
    name = "Python 3.4"
    has_marshal_opt = True
    has_marshal_ref = True

class Pyc35(Pyc34):
    # currently in alpha stage
    code = _v(3320)
    name = "Python 3.5"
