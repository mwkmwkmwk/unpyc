from pathlib import Path
import os
import subprocess
import sys
import shutil

from envy.format.pyc import PycFile
from envy.format.helpers import FormatError
from envy.python.helpers import PythonError
from envy.python.code import Code
from envy.python.deco import deco_code
from envy.python.postproc import ast_process
from envy.python.version import *

root_dir = (Path(__file__).parent / '..' / '..').resolve()

test_dir = root_dir / 'testdata' / 'python'

if "OLDPY_PATH" in os.environ:
    oldpy_dir = Path(os.environ["OLDPY_PATH"])
else:
    oldpy_dir = root_dir / '..' / 'oldpy'

wanted = sys.argv[1:]

TESTS_10 = {
    # marshal types exercises
    'marshal/none': '10',
    'marshal/int': '10',
    'marshal/str': '10',
    'marshal/float': '10',
    'marshal/tuple': '10',
    # unary ops
    'unary/plus': '10',
    'unary/minus': '10',
    'unary/not_': '10',
    'unary/repr': '10',
    'unary/invert': '10',
    # binary ops
    'binary/add': '10',
    'binary/sub': '10',
    'binary/mul': '10',
    'binary/div': '10',
    'binary/mod': '10',
    'binary/and_': '10',
    'binary/or_': '10',
    'binary/xor': '10',
    'binary/shl': '10',
    'binary/shr': '10',
    # misc expressions
    'expr/attr': '10',
    'expr/call': '10',
    'expr/tuple': '10',
    'expr/list': '10',
    'expr/dict': '10',
    'expr/cmp': '10',
    'expr/chain': '10',
    'expr/chain2': '10',
    'expr/logic': '10',
    'expr/logic_const': '10',
    'expr/slice': '10',
    'expr/subscr': '10',
    'expr/misc': '10',
    # function/class definitions
    'defs/fun': '10',
    'defs/lambda_': '10',
    'defs/cls': '10',
    'defs/doc': '10',
    'defs/doc2': '10',
    # names processing
    'names/simple': '10',
    'names/fun': '10',
    'names/fun2': '10',
    'names/global_': '10',
    'names/nested': '10',
    'names/nested2': '10',
    # statements
    'stmt/multi': '10',

    'stmt/assign': '10',
    'stmt/access_': '10',
    'stmt/exec_': '10',
    'stmt/raise_': '10',
    'stmt/print_': '10',
    'stmt/import_': '10',

    'stmt/break_': '10',
    'stmt/continue_': '10',

    'stmt/if_': '10',
    'stmt/if_logic': '10',
    'stmt/if_const': '10',
    'stmt/if_logic_const': '10',
    'stmt/for_': '10',
    'stmt/while_': '10',
    'stmt/while_logic': '10',
    'stmt/while_const': '10',
    'stmt/except_': '10',
    'stmt/finally_': '10',
    'stmt/fake_assert': '10',
    'stmt/fake_assert2': '10',
    # misc
    'misc/unpack': '10',
    'misc/empty': '10',
    'misc/dup_code': '10',
    # optimization stuff
    'opt/if_if': '10',
    'opt/if_except': '10',
    'opt/except_if': '10',
    'opt/except_except': '10',
    'opt/while_if': '10',
    'opt/while_except': '10',
    'opt/for_if': '10',
    'opt/for_if_not': '10',
    'opt/cond': '10',
    'opt/cond_const': '10',
    'opt/if_while': '10',
    'opt/if_while_true': '10',
    'opt/except_while': '10',
    'opt/deep': '10',
    'opt/continue_': '10',
    'opt/logic': '10',
    'opt/if_and': '10',
    'opt/if_or': '10',
    'opt/if_return': '10',
    'opt/try_return': '10',
    'opt/while_return': '10',
    'opt/while_continue': '10',
    'opt/for_return': '10',
    'opt/for_try_if': '10',
    'opt/return_cmp': '10',
}

TESTS_11 = TESTS_10.copy()
TESTS_11.update({
    'names/fun': '11',
    'defs/lambda_': '11',
    'defs/fun': '11',
    'defs/cls': '11',
    'names/nested': '11',
    'names/nested2': '11',
    'names/nested3': '11',
    'opt/if_except_else': '11',
    'opt/while_except_else': '11',
    'opt/except_else_if': '11',
    'opt/except_except_else': '11',
    'opt/if_return': '11',
    'opt/try_return': '11',
    'opt/try_return2': '11',
    'opt/while_return': '11',
    'opt/for_return': '11',
    'opt/return_cmp': '11',
    'stmt/fake_assert': '11',
    'stmt/fake_assert2': '11',
})

TESTS_12 = TESTS_11.copy()
TESTS_12.update({
    'defs/doc': '12',
    'stmt/import2': '12',
})

TESTS_13 = TESTS_12.copy()
TESTS_13.update({
    'defs/lambda_': '13',
    'defs/fun': '13',
    'defs/fun2': '13',
    'defs/fun3': '13',
    'stmt/access_': '13',
    'stmt/raise2': '13',
    'expr/call2': '13',
    'names/fun': '13',
    'names/fun2': '13',
    'misc/dup_code': '13',
})

TESTS_14 = TESTS_13.copy()
TESTS_14.update({
    'marshal/complex': '14',
    'binary/pow': '14',
    'expr/slice2': '14',
})
del TESTS_14['stmt/access_']

TESTS_15 = TESTS_14.copy()
TESTS_15.update({
    'marshal/int': '15',
    'defs/doc': '15',
    'defs/doc2': '15',
    'stmt/assert_': '15',
    'stmt/if_const': '15',
    'opt/assert_logic': '15',
})

TESTS_16 = TESTS_15.copy()
TESTS_16.update({
    'marshal/unicode': '16',
    'defs/fun4': '16',
    'expr/call3': '16',
    'stmt/raise3': '16',
})
del TESTS_16['defs/fun2']
del TESTS_16['defs/fun3']

TESTS_20 = TESTS_16.copy()
TESTS_20.update({
    #'misc/huge': '20',
    'misc/unpack': '20',
    'names/nested2': '20',
    'names/nested3': '20',
    'names/fun': '20',
    'names/fun2': '20',
    'comp/basic': '20',
    'comp/nested': '20',
    'comp/cond': '20',
    'comp/complex': '20',
    'comp/fun': '20',
    'comp/cond_and': '20',
    'comp/cond_const': '20',
    'comp/cond_not': '20',
    'comp/ctx': '20',
    'stmt/import_': '20',
    'stmt/import2': '20',
    'stmt/import3': '20',
    'stmt/inplace': '20',
    'stmt/print2': '20',
})

TESTS_21 = TESTS_20.copy()
TESTS_21.update({
    'names/nested': '21',
    'names/nested2': '21',
    'names/nested3': '21',
    'names/fun': '21',
    'names/fun2': '21',
    'names/global_': '21',
    'stmt/inplace': '21',
    'stmt/inplace2': '21',
    'stmt/continue2': '21',
})

TESTS_22 = TESTS_21.copy()
TESTS_22.update({
    'marshal/complex': '22',
    'binary/floordiv': '22',
    'binary/truediv': '22',
    'defs/gen': '22',
    'defs/doc': '22',
    'defs/doc2': '22',
    'defs/cls': '22',
    'names/nested': '22',
    'names/nested2': '22',
    'names/nested3': '22',
    'names/fun': '22',
    'names/fun2': '22',
    'comp/fun': '22',
    'stmt/inplace': '22',
    'stmt/inplace3': '22',
})

TESTS_23 = TESTS_22.copy()
TESTS_23.update({
    'defs/gen': '23',
    'comp/cond_const': '23',
    'expr/logic_const': '23',
    'names/global_': '23',
    'stmt/if_const': '23',
    'stmt/if_logic_const': '23',
    'stmt/continue_': '23',
    'stmt/while_const': '23',
    'opt/while_return': '23',
    'opt/while_continue': '23',
    'opt/cond_const': '23',
    'opt/if_while_true': '23',
})

TESTS_24a1 = TESTS_23.copy()
TESTS_24a1.update({
    'marshal/int2': '24',
    'genexp/basic': '24',
    'genexp/nested': '24',
    'genexp/cond': '24',
    'genexp/complex': '24',
    'genexp/fun': '24',
    'genexp/cond_and': '24',
    'genexp/cond_const': '24',
    'genexp/cond_not': '24',
    'genexp/ctx': '24',
})

TESTS_24a3 = TESTS_24a1.copy()
TESTS_24a3.update({
    'defs/deco': '24',
    'defs/fun': '24',
    'defs/gen': '24',
    'names/fun': '24',
    'names/fun2': '24',
    'names/global_': '24',
    'stmt/exec_': '24',
    'stmt/if_logic': '24',
    'stmt/if_const': '24',
    'stmt/if_logic_const': '24',
    'stmt/while_const': '24',
    'expr/logic': '24',
    'expr/logic_const': '24',
    'misc/unpack': '24',
    'opt/if_and': '24',
    'opt/logic': '24',
    'opt/cond_const': '24',
})

TESTS_24 = TESTS_24a3.copy()
TESTS_24.update({
})

TESTS_25a1 = TESTS_24.copy()
TESTS_25a1.update({
    'marshal/complex': '25',
    'marshal/unicode': '25',
    'marshal/float': '25a1',
    'stmt/with_': '25',
    'stmt/import4': '25',
    'stmt/while_const': '25a1', # yup, a bug.
    'stmt/try_': '25',
    'expr/misc': '25',
    'expr/if_': '25',
    'expr/if_const': '25',
    'defs/fun': '25',
    'defs/cls': '25',
    'defs/doc': '25a1',
    'defs/doc2': '25a1',
    'defs/gen': '25',
    'defs/gen2': '25',
    'names/global_': '25',
    'names/fun': '25',
    'names/fun2': '25',
    'names/nested': '25',
    'names/nested2': '25',
    'names/nested3': '25',
    'stmt/if_const': '25',
    'genexp/nested': '25',
    'comp/complex': '25',
    'comp/cond_const': '25',
    'genexp/complex': '25',
    'genexp/cond_const': '25',
    'opt/cond_const': '25',
    'opt/return_if': '25',
})

TESTS_25b3 = TESTS_25a1.copy()
TESTS_25b3.update({
})

TESTS_25c1 = TESTS_25b3.copy()
TESTS_25c1.update({
    'defs/doc': '25',
    'defs/doc2': '25',
})

TESTS_25 = TESTS_25c1.copy()
TESTS_25.update({
    'marshal/float': '25',
    'stmt/while_const': '25',
})

TESTS_26 = TESTS_25.copy()
TESTS_26.update({
    'marshal/bytes': '26',
    'defs/deco2': '26',
    'names/fun': '24',
    'stmt/import5': '26',
    'opt/if_return': '26',
    'opt/while_return': '26',
    'opt/try_return2': '26',
    'opt/return_if': '26',
})

TESTS_27 = TESTS_26.copy()
TESTS_27.update({
    'expr/set': '27',
    'comp/set': '27',
    'comp/dict': '27',
    'opt/logic': '27',
    'expr/logic_const': '27',
    'stmt/while_const': '27',
    'stmt/if_logic_const': '27',
    'opt/if_and': '27',
})

TESTS_30 = TESTS_26.copy()
TESTS_30.update({
    'comp/basic': '30',
    'comp/nested': '30',
    'comp/cond': '30',
    'comp/complex': '30',
    'comp/fun': '30',
    'comp/cond_and': '30',
    'comp/cond_const': '30',
    'comp/cond_not': '30',
    'comp/ctx': '30',
    'comp/set': '27',
    'comp/dict': '27',
    'stmt/continue3': '30',
    'stmt/raise4': '30',
    'stmt/import_': '30',
    'stmt/import2': '30',
    'stmt/import3': '30',
    'stmt/inplace': '30',
    'stmt/inplace2': '30',
    'stmt/inplace3': '30',
    'marshal/int2': '30',
    'marshal/str': '30',
    'defs/doc': '30',
    'defs/gen': '30',
    'defs/cls': '30',
    'defs/fun5': '30',
    'defs/fun6': '30',
    'defs/lambda2': '30',
    'stmt/except2': '30',
    'stmt/with_': '30',
    'stmt/try2': '30',
    'binary/div': '30',
    'binary/truediv': '30',
    'names/fun3': '30',
    'names/fun4': '30',
    'names/nested2': '30',
    'names/nested3': '30',
    'misc/unpack2': '30',
    'expr/set': '27',
    'expr/dict': '30',
})
del TESTS_30['stmt/print_']
del TESTS_30['stmt/print2']
del TESTS_30['stmt/exec_']
del TESTS_30['stmt/try_']
del TESTS_30['stmt/continue_']
del TESTS_30['stmt/continue2']
del TESTS_30['stmt/raise_']
del TESTS_30['stmt/raise2']
del TESTS_30['stmt/raise3']
del TESTS_30['stmt/except_']
del TESTS_30['stmt/fake_assert']
del TESTS_30['expr/chain']
del TESTS_30['marshal/unicode']
del TESTS_30['marshal/int']
del TESTS_30['unary/repr']
del TESTS_30['names/fun']
del TESTS_30['names/fun2']
del TESTS_30['defs/fun']
del TESTS_30['defs/fun4']
del TESTS_30['defs/lambda_']
del TESTS_30['misc/dup_code']

TESTS_31 = TESTS_30.copy()
TESTS_31.update({
})

TESTS_32 = TESTS_31.copy()
TESTS_32.update({
    'marshal/float': '32',
    'stmt/import6': '32',
})

TESTS_33 = TESTS_32.copy()
TESTS_33.update({
    'marshal/unicode': '25',
    'marshal/float': '25',
    'defs/gen3': '33',
})

TESTS_34 = TESTS_33.copy()
TESTS_34.update({
})

TESTS_35 = TESTS_34.copy()
TESTS_35.update({
    'binary/matmul': '35',
    'stmt/inplace4': '35',
})

VERSIONS = [
    ("1.0", "1.0.1", 'import', None, Pyc10, TESTS_10),
    ("1.1", "1.1", 'import', None, Pyc11, TESTS_11),
    ("1.2", "1.2", 'import', None, Pyc11, TESTS_12),
    ("1.3", "1.3", 'import', None, Pyc13, TESTS_13),
    ("1.4", "1.4", 'compile', None, Pyc14, TESTS_14),
    ("1.5", "1.5", 'compile', None, Pyc15, TESTS_15),
    ("1.6", "1.6.1", 'compile', None, Pyc16, TESTS_16),
    ("2.0", "2.0.1", 'compile', None, Pyc20, TESTS_20),
    ("2.1", "2.1.3", 'compile', None, Pyc21, TESTS_21),
    ("2.2", "2.2.3", 'compile', None, Pyc22, TESTS_22),
    ("2.3", "2.3.7", 'compile', None, Pyc23, TESTS_23),
    ("2.4a1", "2.4a1", 'compile', None, Pyc24a1, TESTS_24a1),
    ("2.4a3", "2.4a3", 'compile', None, Pyc24a3, TESTS_24a3),
    ("2.4", "2.4.6", 'compile', None, Pyc24, TESTS_24),
    ("2.5a1", "2.5b2", 'compile', None, Pyc25a1, TESTS_25a1),
    ("2.5b3", "2.5b3", 'compile', None, Pyc25b3, TESTS_25b3),
    ("2.5c1", "2.5c1", 'compile', None, Pyc25c1, TESTS_25c1),
    ("2.5", "2.5.6", 'compile', None, Pyc25, TESTS_25),
    ("2.6", "2.6.9", 'compile', None, Pyc26, TESTS_26),
    ("2.7", "2.7.9", 'compile', None, Pyc27, TESTS_27),
    ("3.0", "3.0.1", 'compile', None, Pyc30, TESTS_30),
    ("3.1", "3.1.5", 'compile', None, Pyc31, TESTS_31),
    ("3.2", "3.2.6", 'compile', 'cpython-32', Pyc32, TESTS_32),
    ("3.3", "3.3.6", 'compile', 'cpython-33', Pyc33, TESTS_33),
    ("3.4", "3.4.3", 'compile', 'cpython-34', Pyc34, TESTS_34),
    ("3.5", "3.5.0a2", 'compile', 'cpython-35', Pyc35, TESTS_35),
]

for v in VERSIONS:
    version, rversion, cmode, tag, pycver, tests = v
    failed = 0
    mismatch = 0
    missing = 0
    nopyc = 0
    if wanted and version not in wanted:
        continue
    subdir = test_dir / 'work' / version
    shutil.rmtree(str(subdir), ignore_errors=True)
    subdir.mkdir(parents=True)
    print("version {} ({})...".format(version, rversion))
    pydir = oldpy_dir / "Python-{}".format(rversion)
    if not pydir.exists():
        print("No python {}".format(rversion))
        continue
    # clear all pyc files
    for test in tests:
        srcfile = test_dir / (test + '.py')
        if not srcfile.exists():
            continue
        pyfile = subdir / (test + '.py')
        try:
            pyfile.parent.mkdir(parents=True)
        except FileExistsError:
            pass
        shutil.copyfile(str(srcfile), str(pyfile))
    # if compileall is present, use it now
    if cmode == 'compile':
        p = subprocess.Popen(['./python', 'Lib/compileall.py', str(subdir)], cwd=str(pydir), stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        p.wait()
    # now, the actual tests
    for test, exp in sorted(tests.items(), key=lambda x: x[0]):
        if tag:
            tdir, _, tname = test.rpartition('/')
            pycfile = subdir / tdir / '__pycache__' / ('{}.{}.pyc'.format(tname, tag))
        else:
            pycfile = subdir / (test + '.pyc')
        if cmode == 'import':
            errfile = subdir / (test + '.log')
            with errfile.open('wb') as err:
                p = subprocess.Popen([str(pydir / 'python'), '-c', 'import {}'.format(pycfile.stem)], cwd=str(pycfile.parent), stderr=err, stdout=subprocess.DEVNULL)
            p.wait()
            if not pycfile.exists():
                print("compiling {} did not succeed:".format(test))
                with errfile.open() as err:
                    for line in err.readlines():
                        print('\t{}'.format(line))
                nopyc += 1
                continue
            errfile.unlink()
        if not pycfile.exists():
            print("compiling {} did not succeed".format(test))
            nopyc += 1
            continue
        try:
            with pycfile.open('rb') as fp:
                pyc = PycFile(fp)
            if pyc.version is not pycver:
                print("pyc tag mismatch")
            code = Code(pyc.code, pyc.version)
            deco = deco_code(code)
            ast = ast_process(deco, pyc.version)
            res = [line + '\n' for line in ast.show()]
        except (PythonError, FormatError) as e:
            print("FAIL {}: {}".format(test, e))
            failed += 1
        else:
            expfile = test_dir / (test + '.exp-{}.py'.format(exp))
            resfile = subdir / (test + '.res.py')
            if resfile.exists():
                resfile.unlink()
            if not expfile.exists():
                print("no expected result for {}".format(test))
                exp = None
                missing += 1
            else:
                with expfile.open() as expf:
                    exp = list(expf.readlines())
                if exp != res:
                    print("Result mismatch for {}".format(test))
                    mismatch += 1
            with resfile.open("w") as resf:
                for line in res:
                    resf.write(line)

    if failed or mismatch or missing or nopyc:
        print("STATS: {} failed, {} missing, {} mismatch, {} no pyc".format(failed, missing, mismatch, nopyc))
