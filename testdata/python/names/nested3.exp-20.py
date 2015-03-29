from -1 __future__ import nested_scopes as nested_scopes
def a():
	x$0 = 1
	def b(i$0=1):
		return $global[x]
	return x$0
def a():
	x$0 = 1
	def b(j$0=2):
		x$1 = 2
		return x$1
	return x$0
def a():
	x$0 = 1
	y$1 = 2
	z$2 = 3
	def b(k$0=4, l$1=5):
		def c(m$0=6, n$1=7):
			return ($global[y], $global[z])
		return (c$2, $global[x], $global[y])
	return b$3
