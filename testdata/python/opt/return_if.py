def f():
    return a if b else c

    return a if a and b else c
    return a if a or b else c
    return a if not a else c

    return a if b else (c and d)

    return (a and b) if c else d

    return (a and b) if c else (d and e)

    return (a if b else (c and d)) and e

    return ((a and b) if (c and d) else (e and f)) and g

    return a if b else (c or d)

    return (a or b) if c else d

    return (a or b) if c else (d or e)

    return (a if b else (c or d)) or e

    return ((a or b) if (c or d) else (e or f)) or g
