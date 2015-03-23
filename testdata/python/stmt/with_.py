from __future__ import with_statement

with a:
    b
    c
    d

with a as b:
    c

with a as (a, b):
    c
    d
