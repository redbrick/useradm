#! /usr/bin/env python

"""Update userdb reserved table from mail aliases, DNS entries and Unix groups."""

import grp
import os
import pgdb
import re

__version__ = "$Revision$"
__author__ = "Cillian Sharkey"

entries = {}

def add_entry(name, desc):
	"""Aggregate descriptions for multiple entries."""

	if entries.has_key(name):
		entries[name] += ', ' + desc
	else:
		entries[name] = desc

def main():
	"""Program entry function."""

	dbh = pgdb.connect(database = 'userdb')
	cur = dbh.cursor()

	print 'userdb/reserved:',

	alias_files = (
		('/etc/mail/aliases', 'Mail alias'),
		#('/etc/mail/personal_aliases', 'Personal mail alias'),
		#('/etc/mail/user_rename_aliases', 'User rename mail alias'),
		#('/local/mailman/aliases', 'Mailing lists mail alias')
	)

	# Delete all existing entries.
	#
	print 'Purge.',
	cur.execute('delete from reserved')

	# Add new entries.
	#
	print 'Populate.',

	# Ignore aliases that are longer than 8 characters.
	re_alias = re.compile(r'^\s*([^#]{1,8}):')

	# Do mail alias files.
	#
	for file, desc in alias_files:
		fd = open(file, 'r')
		for line in fd.readlines():
			res = re_alias.search(line)
			if res:
				add_entry(res.group(1).lower(), desc)
		fd.close()

	# DNS entries, *.{club,soc,redbrick}.dcu.ie
	#
	fd = os.popen('dig @ns.redbrick.dcu.ie -t axfr redbrick.dcu.ie club.dcu.ie soc.dcu.ie')
	re_dns = re.compile(r'^([^;.]+)\..+\.dcu\.ie')
	dns_entries = {}
	
	for line in fd.readlines():
		res = re_dns.search(line)
		if res:
			name = res.group(1).lower()
			# Ignore entries that are longer than 8 characters.
			if len(name) > 8 or dns_entries.has_key(name):
				continue
			dns_entries[name] = 1		
			add_entry(name, 'DNS entry')
	fd.close()

	# Do Unix /etc/group file.
	#
	for g in grp.getgrall():
		add_entry(g[0].lower(), 'Unix group')

	# Now add entries to table.
	#
	insert_reserved = 'INSERT INTO reserved (username, info) VALUES (%s, %s)'
	for k, v in entries.items():
		cur.execute(insert_reserved, (k, v))

	print 'Done [%d]' % len(entries.items())

	dbh.commit()
	cur.execute('END; VACUUM ANALYZE reserved')
	dbh.close()


if __name__ == "__main__":
	main()
