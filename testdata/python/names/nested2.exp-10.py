from __future__ import nested_scopes
def a():
	x$0 = 1
	def b():
		return x
	return x$0
def a():
	x$0 = 1
	def b():
		x$0 = 2
		return x$0
	return x$0
def a():
	x$0 = 1
	y$1 = 2
	z$2 = 3
	def b():
		def c():
			return (y, z)
		return (c$0, x, y)
	return b$3
