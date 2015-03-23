try:
    a
finally:
    b

try:
    try:
        a
    except b:
        c
finally:
    d
