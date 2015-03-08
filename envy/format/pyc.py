import datetime

from .helpers import read_bytes, read_byte, read_le, read_eof, FormatError
from .marshal import load_marshal


# exceptions

class PycError(FormatError):
    pass


# versions

class PycVersion:
    pass

# Python 2

class Pyc2(PycVersion):
    has_size = False
    major = 2
    py3k = False

class Pyc62211(Pyc2):
    code = 62211
    name = "Python 2.7"

# Python 3

class Pyc3(PycVersion):
    has_size = True
    major = 3
    py3k = True

class Pyc3310(Pyc3):
    code = 3310
    name = "Python 3.4"

PYC_VERSIONS = {
    62211: Pyc62211,
    62212: Pyc62211, # -U
    3310: Pyc3310,
}


class PycFile:
    __slots__ = 'version', 'timestamp', 'size', 'code'

    def __init__(self, fp):
        version_code = read_le(fp, 2)
        sig = read_bytes(fp, 2)
        if sig != b'\r\n':
            raise PycError("pyc signature incorrect")
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
