def f():
	try:
		a
	except b:
		c
		return d
	try:
		a
	except b:
		return c
	except:
		return d
