from 0 __future__ import with_statement as with_statement
with a:
	b
	c
	d
with a as b:
	c
with a as (a, b):
	c
	d
while a:
	with b as c:
		continue
