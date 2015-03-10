def parse_lnotab(firstlineno, lnotab, codelen):
    if len(lnotab) % 2:
        raise PythonError("lnotab length not divisible by 2")
    lit = iter(lnotab)
    res = []
    prev_addr = None
    cur_addr = 0
    cur_line = firstlineno
    for addr_inc, line_inc in zip(lit, lit):
        if addr_inc:
            if prev_addr is None:
                prev_addr = cur_addr
            cur_addr += addr_inc
        if line_inc:
            if prev_addr is not None:
                res.append([cur_line, prev_addr, cur_addr])
                prev_addr = None
            cur_line += line_inc
    if prev_addr is None:
        prev_addr = cur_addr
    res.append([cur_line, prev_addr, codelen])
    return res
