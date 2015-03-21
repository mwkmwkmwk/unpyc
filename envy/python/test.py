from pathlib import Path
import os
import subprocess
import sys

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

def gather_tests(dir):
    for item in dir.iterdir():
        if item.is_dir():
            if item.name != '__pycache__':
                yield from gather_tests(item)
        elif item.suffix == '.py':
            yield item

wanted = sys.argv[1:]

VERSIONS = [
    ("1.0", "1.0.1", 'import', None, Pyc10),
    ("1.1", "1.1", 'import', None, Pyc11),
    ("1.2", "1.2", 'import', None, Pyc11),
    ("1.3", "1.3", 'import', None, Pyc13),
    ("1.4", "1.4", 'compile', None, Pyc14),
    ("1.5", "1.5", 'compile', None, Pyc15),
    ("1.6", "1.6.1", 'compile', None, Pyc16),
    ("2.0", "2.0.1", 'compile', None, Pyc20),
    ("2.1", "2.1.3", 'compile', None, Pyc21),
    ("2.2", "2.2.3", 'compile', None, Pyc22),
]

for v in VERSIONS:
    version, rversion, cmode, tag, pycver = v
    if wanted and version not in wanted:
        continue
    subdir = test_dir / version
    print("version {} ({})...".format(version, rversion))
    pydir = oldpy_dir / "Python-{}".format(rversion)
    if not pydir.exists():
        print("No python {}".format(rversion))
        continue
    # clear all pyc files
    for test in gather_tests(subdir):
        pycfile = test.parent / (test.stem + '.pyc')
        if pycfile.exists():
            pycfile.unlink()
    # if compileall is present, use it now
    if cmode == 'compile':
        p = subprocess.Popen(['./python', 'Lib/compileall.py', str(subdir)], cwd=str(pydir), stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        p.wait()
    # now, the actual tests
    for test in gather_tests(subdir):
        name = test.stem
        pycfile = test.parent / (test.stem + '.pyc')
        if cmode == 'import':
            errfile = test.parent / (test.stem + '.log')
            with errfile.open('wb') as err:
                p = subprocess.Popen([str(pydir / 'python'), '-c', 'import {}'.format(name)], cwd=str(test.parent), stderr=err, stdout=subprocess.DEVNULL)
            p.wait()
            if not pycfile.exists():
                print("compiling {} did not succeed:".format(test))
                with errfile.open() as err:
                    for line in err.readlines():
                        print('\t{}'.format(line))
                continue
            errfile.unlink()
        if not pycfile.exists():
            print("compiling {} did not succeed".format(test))
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
        else:
            expfile = test.parent / (test.stem + '.exp')
            resfile = test.parent / (test.stem + '.res')
            if resfile.exists():
                resfile.unlink()
            if not expfile.exists():
                print("no expected result for {}".format(test))
                pycfile.unlink()
                exp = None
            else:
                with expfile.open() as expf:
                    exp = list(expf.readlines())
                if exp != res:
                    print("Result mismatch for {}".format(test))
            if exp != res:
                with resfile.open("w") as resf:
                    for line in res:
                        resf.write(line)
            else:
                pycfile.unlink()
