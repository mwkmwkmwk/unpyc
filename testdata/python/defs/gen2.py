def f():
    b = yield a
    yield b
    yield (yield c)
    (yield d)
    return
