from -1 __future__ import nested_scopes as nested_scopes
def a():
	x$d0 = 1
	def b():
		return x$d0
	return x$d0
def a():
	x$0 = 1
	def b():
		x$0 = 2
		return x$0
	return x$0
def a():
	x$d1 = 1
	y$d0 = 2
	z$d2 = 3
	def b():
		def c():
			return (y$d0, z$d1)
		return (c$0, x$d1, y$d0)
	return b$0
