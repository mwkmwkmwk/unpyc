from -1 __future__ import generators as generators
def f():
	(yield $global[a])
	(yield $global[b])
	(yield $global[c])
def g():
	pass
def h():
	$global[f]()
def i():
	pass
