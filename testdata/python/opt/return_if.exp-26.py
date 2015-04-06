def f():
	if $global[b]:
		return $global[a]
	return $global[c]
	if ($global[a] and $global[b]):
		return $global[a]
	return $global[c]
	if ($global[a] or $global[b]):
		return $global[a]
	return $global[c]
	if (not $global[a]):
		return $global[a]
	return $global[c]
	if $global[b]:
		return $global[a]
	return ($global[c] and $global[d])
	return (($global[a] and $global[b]) if $global[c] else $global[d])
	return (($global[a] and $global[b]) if $global[c] else ($global[d] and $global[e]))
	return (($global[a] if $global[b] else ($global[c] and $global[d])) and $global[e])
	return ((($global[a] and $global[b]) if ($global[c] and $global[d]) else ($global[e] and $global[f])) and $global[g])
	if $global[b]:
		return $global[a]
	return ($global[c] or $global[d])
	return (($global[a] or $global[b]) if $global[c] else $global[d])
	return (($global[a] or $global[b]) if $global[c] else ($global[d] or $global[e]))
	return (($global[a] if $global[b] else ($global[c] or $global[d])) or $global[e])
	return ((($global[a] or $global[b]) if ($global[c] or $global[d]) else ($global[e] or $global[f])) or $global[g])
