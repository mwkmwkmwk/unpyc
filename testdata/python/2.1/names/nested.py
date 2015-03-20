def a():
    x = 1
    def b():
        return x
    return x

def a():
    x = 1
    def b():
        x = 2
        return x
    return x
