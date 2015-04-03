def f():
    try:
        a
    except b:
        c
        return d
    else:
        e
    f

    try:
        a
    except b:
        return c
    except:
        return d
    else:
        e
    f
