import datetime

from .helpers import read_bytes, read_byte, read_le, read_eof, FormatError
from .marshal import load_marshal


# exceptions

class PycError(FormatError):
    pass


# versions

PYC_VERSIONS = {}

def v(x):
    return x | 0x0a0d0000

class PycVersionMeta:
    def __init__(self, name, bases, namespace):
        for base in bases:
            self.__dict__.update(base.__dict__)
        self.__dict__.update(namespace)
        if hasattr(self, 'code'):
            PYC_VERSIONS[self.code] = self
            if self.has_U:
                PYC_VERSIONS[self.code + 1] = self

class PycVersion(metaclass=PycVersionMeta):
    pass

# Python 1

class Pyc10(PycVersion):
    code = 0x999902
    name = "Python 1.0"

    has_U = False
    consts_is_list = True
    has_size = False
    py3k = False
    has_stacksize = False
    has_le4 = False
    has_closure = False

class Pyc11(Pyc10):
    code = 0x999903
    name = "Python 1.1/1.2"
    consts_is_list = False

class Pyc13(Pyc11):
    """Introduces new marshal code type"""
    code = v(11913)
    name = "Python 1.3"

class Pyc14(Pyc13):
    """Introduces complex, ellipsis, 3-arg slices, ** operator.
    Gets rid of access support.
    """
    code = v(5892)
    name = "Python 1.4"

class Pyc15(Pyc14):
    """Introduces stacksize and lnotab."""
    code = v(20121)
    name = "Python 1.5"
    has_stacksize = True

class Pyc16(Pyc15):
    code = v(50428)
    name = "Python 1.6"

# Python 2

class Pyc20(Pyc16):
    code = v(50823)
    name = "Python 2.0"
    has_U = True

class Pyc21(Pyc20):
    code = v(60202)
    name = "Python 2.1"
    has_closure = True

class Pyc22(Pyc21):
    code = v(60717)
    name = "Python 2.2"

class Pyc23(Pyc22):
    # 62021 used in prealpha
    code = v(62011)
    name = "Python 2.3"
    has_le4 = True

class Pyc24(Pyc23):
    # 62041 used in a1-a2
    # 62051 used in a3
    code = v(62061)
    name = "Python 2.4"

class Pyc25(Pyc24):
    # 62071 used in prealpha
    # 62081 used in prealpha
    # 62091 used in prealpha
    # 62092 used in alphas and b1-b2
    # 62101 used in unreleased beta
    # 62111 used in b3
    # 62121 used in c1
    code = v(62131)
    name = "Python 2.5"

class Pyc26(Pyc25):
    # 62151 used in prealpha
    code = v(62161)
    name = "Python 2.6"

class Pyc27(Pyc26):
    # 62171 used in preaplha
    # 62181 used in preaplha
    # 62191 used in preaplha
    # 62201 used in preaplha
    code = v(62211)
    name = "Python 2.7"

# Python 3

# 3000, 3010, 3020, 3030, 3040, 3050, 3060, 3061, 3071, 3081, 3091, 3101
# used in development branch

class Pyc30(PycVersion):
    # 3103 used in a1-a3
    # 3111 used in a4
    code = v(3131)
    name = "Python 3.0"

    has_U = False
    consts_is_list = False
    has_size = False
    py3k = True
    has_stacksize = True
    has_le4 = True
    has_closure = True

class Pyc31(Pyc30):
    # 3141 used in prealpha
    code = v(3151)
    name = "Python 3.1"

class Pyc32(Pyc31):
    # 3160 used in prealpha
    # 3170 used in a1
    code = v(3180)
    name = "Python 3.2"

class Pyc33(Pyc32):
    # 3190 used in prealpha
    # 3200 used in prealpha
    # 3210 used in prealpha
    # 3220 used in a1-a3
    code = v(3230)
    name = "Python 3.3"
    has_size = True

class Pyc34(Pyc33):
    # 3250, 3260, 3270 used in prealpha
    # 3280 used in a1-a3
    # 3290 used in unreleased alpha
    # 3300 used in a4, betas, rc1
    code = v(3310)
    name = "Python 3.4"

class Pyc35(Pyc34):
    # currently in alpha stage
    code = v(3320)
    name = "Python 3.5"


class PycFile:
    __slots__ = 'version', 'timestamp', 'size', 'code'

    def __init__(self, fp):
        version_code = read_le(fp, 4)
        try:
            self.version = PYC_VERSIONS[version_code]
        except KeyError:
            raise PycError("pyc version unknown ({})".format(version_code))
        self.timestamp = read_le(fp, 4)
        if self.version.has_size:
            self.size = read_le(fp, 4)
        else:
            self.size = None
        self.code = load_marshal(fp, self.version)
        read_eof(fp)

    def print(self):
        print("pyc version {} ({}) {}".format(self.version.code, self.version.name, datetime.datetime.fromtimestamp(self.timestamp)))
        if self.size is not None:
            print("source size {}".format(self.size))
        self.code.print(0)
