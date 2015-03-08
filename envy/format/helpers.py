class FormatError(Exception):
    pass

def read_bytes(fp, size):
    buf = fp.read(size)
    if len(buf) != size:
        raise FormatError("premature EOF")
    return buf

def read_byte(fp):
    return read_bytes(fp, 1)[0]

def read_le(fp, size, signed=False):
    return int.from_bytes(read_bytes(fp, size), 'little', signed=signed)

def read_eof(fp):
    if fp.read(1) != b'':
        raise FormatError("junk after EOF")
