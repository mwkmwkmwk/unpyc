import datetime

from .helpers import read_bytes, read_byte, read_le, read_eof, FormatError
from .marshal import load_marshal
from envy.python.version import PYC_VERSIONS

class PycError(FormatError):
    pass


class PycFile:
    """Represents a pyc file in deserialized, but not decompiled form.

    A pyc file is basically just signature + timestamp + size (3.3+ only)
    + a marshal object.  Nothing to see here.
    """
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
