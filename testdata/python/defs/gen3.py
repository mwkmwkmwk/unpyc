def f():
    b = yield from a
    yield from b
    yield from (yield from c)
    (yield from d)
    return
