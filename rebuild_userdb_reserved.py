#! /usr/bin/env python

#-----------------------------------------------------------------------------#
# MODULE DESCRIPTION                                                          #
#-----------------------------------------------------------------------------#

"""Rebuild userdb reserved table.

Dynamic reserved entries are comprised of email aliases, mailing list names
and DNS entries for all zones RedBrick is authorative for.

"""

# System modules

import os
import re

# RedBrick modules

import rbconfig
from rbuserdb import *

#-----------------------------------------------------------------------------#
# DATA                                                                        #
#-----------------------------------------------------------------------------#

__version__ = "$Revision: 1.1 $"
__author__ = "Cillian Sharkey"

# Dictionary of (name, description) pairs to add.

entries = {}

#-----------------------------------------------------------------------------#
# MAIN                                                                        #
#-----------------------------------------------------------------------------#

def add_entry(name, desc):
	"""Aggregate descriptions for multiple entries."""

	if entries.has_key(name):
		entries[name] += ', ' + desc
	else:
		entries[name] = desc

def main():
	"""Program entry function."""

	udb = RBUserDB()
	udb.connect()

	print 'userdb/reserved:',

	# Build new entries.
	#
	print 'Build',

	# Email aliases.
	#
	re_alias = re.compile(r'^\s*([^#]{1,%d}):' % rbconfig.maxlen_uname)
	
	for file, desc in rbconfig.alias_files:
		fd = open(file, 'r')
		for line in fd.readlines():
			res = re_alias.search(line)
			if res:
				add_entry(res.group(1).lower(), desc)
		fd.close()

	# DNS entries.
	#
	fd = os.popen('dig @ns.redbrick.dcu.ie -t axfr ' % rbconfig.dns_zones))
	re_dns = re.compile(r'^([^;.]{1,%d})\..+\.dcu\.ie' % rbconfig.maxlen_uname)
	dns_entries = {}
	
	for line in fd.readlines():
		res = re_dns.search(line)
		if res:
			name = res.group(1).lower()
			if dns_entries.has_key(name):
				continue
			dns_entries[name] = 1		
			add_entry(name, 'DNS entry')
	fd.close()

	# Do host files.
	#
	re_alias = re.compile(r'^[^#\s]+(\s+[^#\s]{1,%d})+' % rbconfig.maxlen_uname)
	
	for file, host in rbconfig.host_files:
		fd = open(file)
		for line in fd.readlines():
			res = re_dns.search(line)
			if res:
				print res.groups()
				#name = res.group(1).lower()
				#if dns_entries.has_key(name):
				#	continue
				#dns_entries[name] = 1			
				#add_entry(g[0], '%s Unix group' % host)

	# Do Unix group files.
	#
	for file, host in rbconfig.group_files:
		fd = open(file)
		for line in fd.readlines():
			grp = line[:line.find(':')].lower()
			if not udb.check_group_byname(grp):
				add_entry(g[0], '%s Unix group' % host)

	print '[%d].' % len(entries.keys()),

	# Do mailing lists.
	#
	fd = os.popen('%s/bin/list_lists' % rbconfig.mailman_dir)
	for list in fd.readlines():
		add_entry(line, 'Mailing list')
		for suffix in rbconfig.mailman_list_suffixes:
			tmp = '%s%s' % (list, suffix)
			if len(tmp) <= rbconfig.maxlen_uname:
				add_entry(tmp), 'Mailing list')
	fd.close()

	# Delete unused entries.
	#
	print 'Purge.',

	purge_dn = []
	reserveds = {}
	res = udb.list_reserved_dynamic()
	if res:
		for uid in res:
			reserveds[uid] = 1
			if not entries.has_key(uid):
				purge_dn.push('uid=%s,%s' % (uid, rbconfig.ldap_reserved_tree))

	for i in purge_dn:
		res = udb.ldap.delete_s(i)

	# Now add/update entries.
	#
	print 'Populate.',

	for k, v in entries.items():
		if reserveds.has_key(k):
			# update
		else:
			# add

	print 'Done [%d]' % len(entries.items())

	udb.close()

if __name__ == "__main__":
	main()
