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

pydirs = list(oldpy_dir.iterdir())

wanted = sys.argv[1:]

for subdir in sorted(test_dir.iterdir(), key=lambda x: x.name):
    version = subdir.name
    if wanted and version not in wanted:
        continue
    print("version {}...".format(version))
    for pydir in pydirs:
        if pydir.is_dir() and pydir.name.startswith("Python-{}".format(version)):
            break
    else:
        print("No python {}".format(version))
        continue
    for test in gather_tests(subdir):
        name = test.stem
        errfile = test.parent / (test.stem + '.log')
        pycfile = test.parent / (test.stem + '.pyc')
        if pycfile.exists():
            pycfile.unlink()
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
