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
    # has kwargs - new code marshal type, co_varnames, no more RESERVE_FAST
    has_kwargs = False
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
    # jumps over jump_if_false true const
    has_jump_true_const = False
    # has interned bytestrings in marshal
    has_str_intern = False
    # has LIST_APPEND opcode
    has_list_append = False
    # has NOP opcode that can actually make it to the bytecode
    has_nop = False
    # unpacking of just-built tuples and list is optimized to rots
    has_unpack_opt = False
    # if not uses JUMP_IF_TRUE
    has_if_not_opt = True
    # has generator expressions
    has_genexp = False
    # has function decorators
    has_fun_deco = False
    # return X; return None -> return X
    has_return_squash = False
    # jump conditional to jump conditional is folded
    has_jump_cond_fold = False
    # has relative import
    has_relative_import = False
    # has set displays
    has_set_display = False
    # has binary float format in marshal
    has_bin_float = False
    # has with statement
    has_with = False
    # has tmp for exit in with statement
    has_exit_tmp = True
    # closures go through BUILD_TUPLE
    has_sane_closure = False
    # has yield expression
    has_yield_expr = False
    # has if/else expression
    has_if_expr = False
    # while true loop has no POPs at the end
    has_while_true_end_opt = False
    # has class decorators
    has_cls_deco = False
    # has STORE_MAP opcode
    has_store_map = False
    # kills jump opcodes after return
    has_dead_return = False
    # has SETUP_WITH
    has_setup_with = False
    # generic py3k flag - unicode strings, ...
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
    # has new-style build class
    has_new_class = False
    # has store locals
    has_store_locals = False
    # has UNPACK_EX
    has_unpack_ex = False
    # has set & dict comprehensions
    has_setdict_comp = False
    # has armor-plated except clauses
    has_pop_except = False
    # list comprehensions are functions
    has_fun_listcomp = False
    # has kw-only arguments
    has_kwonlyargs = False
    # has SETUP_LOOP in genexp
    has_genexp_loop = True
    # has new-style comprehension implementation
    has_new_comp = False
    # has new-style jumps (with pop)
    has_new_jump = False
    # has DUP_TOP_TWO
    has_dup_two = False
    # has DELETE_DEREF
    has_delete_deref = False
    # x in {const, const, const} -> frozenset
    has_frozenset_opt = False
    # has qualname attribute
    has_qualname = False
    # has source size in pyc
    has_size = False
    # has yield from
    has_yield_from = False
    # has marshal optimized formats
    has_marshal_opt = False
    # has marshal reference support
    has_marshal_ref = False
    # has LOAD_CLASS_DEREF
    has_classderef = False
    # default kwargs pushed before default args
    has_reversed_def_kwargs = True
    # has matrix multiplication
    has_matmul = False

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
    has_kwargs = True
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
    has_jump_true_const = True

class Pyc24a1(Pyc23):
    code = _v(62041)
    name = "Python 2.4a1"
    has_str_intern = True
    has_list_append = True
    has_nop = True
    has_unpack_opt = True
    has_if_not_opt = True
    has_genexp = True

class Pyc24a3(Pyc24a1):
    code = _v(62051)
    name = "Python 2.4a3"
    has_nop = False
    has_return_squash = True
    has_jump_true_const = False
    has_fun_deco = True
    has_jump_cond_fold = True

class Pyc24(Pyc24a3):
    # actually 2.4b1 and up
    code = _v(62061)
    name = "Python 2.4"

class Pyc25a1(Pyc24):
    # 62071 used in prealpha
    # 62081 used in prealpha
    # 62091 used in prealpha
    # actually 2.5a1 - 2.5b2
    code = _v(62092)
    name = "Python 2.5a1"
    has_relative_import = True
    has_bin_float = True
    has_with = True
    has_sane_closure = True
    has_reversed_kv = True
    has_yield_expr = True
    has_if_expr = True
    has_while_true_end_opt = True

class Pyc25b3(Pyc25a1):
    # 62101 used in unreleased beta
    code = _v(62111)
    name = "Python 2.5b3"

class Pyc25c1(Pyc25b3):
    code = _v(62121)
    name = "Python 2.5c1"

class Pyc25(Pyc25c1):
    # actually 2.5c2 and up
    code = _v(62131)
    name = "Python 2.5"

class Pyc26(Pyc25):
    # 62151 used in prealpha
    code = _v(62161)
    name = "Python 2.6"
    has_cls_deco = True
    has_store_map = True
    has_exit_tmp = False
    has_dead_return = True

class Pyc27(Pyc26):
    # 62171 used in preaplha
    # 62181 used in preaplha
    # 62191 used in preaplha
    # 62201 used in preaplha
    code = _v(62211)
    name = "Python 2.7"
    has_set_display = True
    has_setdict_comp = True
    has_new_comp = True
    has_setup_with = True
    has_new_jump = True
    has_genexp_loop = False

# 62213 used in pypy 1.5
# 62217 used in pypy 2.1
# 62218 used in pypy 2.3

# Python 3

# 16 used by pypy3-2.1.0
# 48 used by pypy3-2.3.0

# 3000, 3010, 3020, 3030, 3040, 3050, 3060, 3061, 3071, 3081, 3091, 3101
# used in development branch

class Pyc30(Pyc26):
    # 3103 used in a1-a3
    # 3111 used in a4
    code = _v(3131)
    name = "Python 3.0"

    has_U = False
    has_str_intern = False
    py3k = True
    has_set_display = True
    has_bool_literal = True
    has_complex_args = False
    has_old_slice = False
    has_print = False
    has_print_to = False
    has_exec = False
    has_old_divide = False
    has_repr = False
    has_raise_from = True
    has_store_locals = True
    has_unpack_ex = True
    has_new_class = True
    has_setdict_comp = True
    has_fun_listcomp = True
    has_pop_except = True
    has_kwonlyargs = True
    has_genexp_loop = False
    has_exit_tmp = True

class Pyc31(Pyc30):
    # 3141 used in prealpha
    code = _v(3151)
    name = "Python 3.1"
    has_new_comp = True
    has_new_jump = True

class Pyc32(Pyc31):
    # 3160 used in prealpha
    # 3170 used in a1
    code = _v(3180)
    name = "Python 3.2"
    has_dup_topx = False
    has_rot_four = False
    has_dup_two = True
    has_setup_with = True
    has_delete_deref = True
    has_frozenset_opt = True

class Pyc33(Pyc32):
    # 3190 used in prealpha
    # 3200 used in prealpha
    # 3210 used in prealpha
    # 3220 used in a1-a3
    code = _v(3230)
    name = "Python 3.3"
    has_marshal_int64 = False
    has_qualname = True
    has_size = True
    has_yield_from = True

class Pyc34(Pyc33):
    # 3250, 3260, 3270 used in prealpha
    # 3280 used in a1-a3
    # 3290 used in unreleased alpha
    # 3300 used in a4, betas, rc1
    code = _v(3310)
    name = "Python 3.4"
    has_marshal_opt = True
    has_marshal_ref = True
    has_store_locals = False
    has_classderef = True
    has_reversed_def_kwargs = False

class Pyc35(Pyc34):
    # currently in alpha stage
    code = _v(3320)
    name = "Python 3.5"
    has_matmul = True
