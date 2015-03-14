def indent(lines):
    for line in lines:
        yield '\t' + line

def preindent(pref, lines):
    it = iter(lines)
    yield "{}: {}".format(pref, next(it))
    for line in it:
        yield '\t' + line
