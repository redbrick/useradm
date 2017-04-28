#! /usr/bin/env python

import sys

dcu = 0
for line in sys.stdin:
	if line.startswith('dn:'):
		dcu = line.find('ou=dcu') != -1
	if not dcu:
		print(line, end=' ')

