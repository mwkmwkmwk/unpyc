from __future__ import generators as generators
def f():
	(yield $global[a])
	(yield $global[b])
	(yield $global[c])
def g():
	pass
def h():
	if 1:
		$global[f]()
	else:
		(yield $global[a])
def i():
	while 0:
		(yield $global[a])
