try:
    a
except x:
    b

try:
    a
except x:
    b
except:
    c

try:
    d
except:
    e

try:
    f
except y:
    g
except z as w:
    h

try:
    a
except x:
    b
except y as z:
    c
except:
    d

try:
    a
except x[y] as z:
    b
