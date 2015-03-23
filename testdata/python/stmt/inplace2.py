from __future__ import nested_scopes

def f():
    a &= 9
    def g():
        return a
