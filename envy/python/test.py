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
from envy.python.ast import ast_process
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
    # misc
    'misc/unpack': '10',
    'misc/empty': '10',
}

TESTS_11 = TESTS_10.copy()
TESTS_11.update({
    'names/fun': '11',
    'defs/lambda_': '11',
    'defs/fun': '11',
    'defs/cls': '11',
    'names/nested': '11',
    'names/nested2': '11',
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
    'misc/huge': '20',
    'misc/unpack': '20',
    'names/nested2': '20',
    'names/fun': '20',
    'names/fun2': '20',
    'comp/basic': '20',
    'comp/nested': '20',
    'comp/cond': '20',
    'comp/complex': '20',
    'comp/fun': '20',
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
    'names/fun': '22',
    'names/fun2': '22',
    'comp/fun': '22',
    'stmt/inplace': '22',
    'stmt/inplace3': '22',
})

TESTS_23 = TESTS_22.copy()
TESTS_23.update({
    'defs/gen': '23',
    'expr/logic_const': '23',
    'names/global_': '23',
    'stmt/if_const': '23',
    'stmt/if_logic_const': '23',
    'stmt/while_const': '23',
})

TESTS_24 = TESTS_23.copy()
TESTS_24.update({
    'marshal/int2': '24',
    'defs/deco': '24',
    'defs/fun': '24',
    'names/fun': '24',
    'names/fun2': '24',
    'stmt/exec_': '24',
})

TESTS_25 = TESTS_24.copy()
TESTS_25.update({
    'marshal/complex': '25',
    'marshal/float': '25',
    'marshal/unicode': '25',
    'stmt/with_': '25',
    'expr/misc': '25',
    'defs/cls': '25',
    'defs/gen': '25',
    'defs/gen2': '25',
    'names/global_': '25',
    'stmt/if_const': '25',
})

TESTS_26 = TESTS_25.copy()
TESTS_26.update({
    'marshal/bytes': '26',
    'defs/deco2': '26',
})

TESTS_27 = TESTS_26.copy()
TESTS_27.update({
})

TESTS_30 = TESTS_26.copy()
TESTS_30.update({
    'stmt/continue3': '30',
    'stmt/raise4': '30',
    'marshal/int2': '30',
    'marshal/str': '30',
    'defs/fun5': '30',
    'defs/lambda2': '30',
    'stmt/except2': '30',
    'binary/div': '30',
    'names/fun3': '30',
    'names/fun4': '30',
})
del TESTS_30['stmt/print_']
del TESTS_30['stmt/print2']
del TESTS_30['stmt/exec_']
del TESTS_30['stmt/continue_']
del TESTS_30['stmt/continue2']
del TESTS_30['stmt/raise_']
del TESTS_30['stmt/raise2']
del TESTS_30['stmt/raise3']
del TESTS_30['stmt/except_']
del TESTS_30['expr/chain']
del TESTS_30['marshal/unicode']
del TESTS_30['marshal/int']
del TESTS_30['unary/repr']
del TESTS_30['names/fun']
del TESTS_30['names/fun2']
del TESTS_30['defs/fun']
del TESTS_30['defs/fun4']
del TESTS_30['defs/lambda_']

TESTS_31 = TESTS_30.copy()
TESTS_31.update({
})

TESTS_32 = TESTS_31.copy()
TESTS_32.update({
    'marshal/unicode': '32',
    'marshal/float': '32',
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
    ("2.4", "2.4.6", 'compile', None, Pyc24, TESTS_24),
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
                pycfile.unlink()
                exp = None
                missing += 1
            else:
                with expfile.open() as expf:
                    exp = list(expf.readlines())
                if exp != res:
                    print("Result mismatch for {}".format(test))
                    mismatch += 1
            if exp != res:
                with resfile.open("w") as resf:
                    for line in res:
                        resf.write(line)
            else:
                pycfile.unlink()

    if failed or mismatch or missing or nopyc:
        print("STATS: {} failed, {} missing, {} mismatch, {} no pyc".format(failed, missing, mismatch, nopyc))
