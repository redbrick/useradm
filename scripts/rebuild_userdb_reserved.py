#! /usr/bin/env python

#-----------------------------------------------------------------------------#
# MODULE DESCRIPTION                                                          #
#-----------------------------------------------------------------------------#

"""Rebuild userdb reserved table.

Dynamic reserved entries are comprised of email aliases, mailing list names
and DNS entries for all zones RedBrick is authorative for.

"""

# System modules

import getopt
import os
import re

# RedBrick modules

from rbuserdb import *

#-----------------------------------------------------------------------------#
# DATA                                                                        #
#-----------------------------------------------------------------------------#

__version__ = "$Revision: 1.5 $"
__author__ = "Cillian Sharkey"

# Dictionary of (name, description) pairs to add.

entries = {}
ldap_users = {}

#-----------------------------------------------------------------------------#
# MAIN                                                                        #
#-----------------------------------------------------------------------------#

def add_entry(name, desc):
	"""Aggregate descriptions for multiple entries."""

	if name in ldap_users:
		return
	if name in entries:
		entries[name] += ', ' + desc
	else:
		entries[name] = desc

def main():
	"""Program entry function."""

	udb = RBUserDB()
	udb.connect()
	opt = RBOpt()

	opts, args = getopt.getopt(sys.argv[1:], 'T')

	for o, a in opts:
		if o == '-T':
			opt.test = 1
	
	udb.setopt(opt)

	print('userdb/reserved:', end=' ')

	# Gather new entries.
	#
	print('Gather', end=' ')

	# Get copy of all LDAP user, group and reserved entries in one go to
	# speedup queries later on.
	#
	global ldap_users
	for i in udb.list_users():
		ldap_users[i] = 1
	ldap_groups = {}
	for i in udb.list_groups():
		ldap_groups[i] = 1
	ldap_reserveds = udb.dict_reserved_desc()
	ldap_reserveds_static = udb.dict_reserved_static()

	# Email aliases.
	#
	re_alias = re.compile(r'^\s*([^#]{1,%d}):' % rbconfig.maxlen_uname)
	
	for file, desc in rbconfig.files_alias:
		fd = open(file, 'r')
		for line in fd.readlines():
			res = re_alias.search(line)
			if res:
				add_entry(res.group(1).lower(), desc)
		fd.close()
	
	# DNS entries.
	#
	dns_entries = {}
	for zone in rbconfig.dns_zones:
		fd = os.popen('dig @136.206.15.53 %s -t axfr' % zone)
		re_dns = re.compile(r'^([^#;]*\.)?([^#;]{1,%d})\.%s.\s+\d+\s+IN' % (rbconfig.maxlen_uname, zone))
		for line in fd.readlines():
			res = re_dns.search(line)
			if res:
				name = res.group(2).lower()
				if name in dns_entries:
					continue
				dns_entries[name] = 1
				add_entry(name, 'DNS entry')
		fd.close()

	# Do host files.
	#
	re_host = re.compile(r'^[^#\s]+\s+([^#]+)')
	re_hostent = re.compile(r'\s+')
	
	for file, host in rbconfig.files_host:
		fd = open(file)
		for line in fd.readlines():
			res = re_host.search(line.lower())
			if not res:
				continue
			for name in res.group(1).split():
				if name and '.' not in name and len(name) <= rbconfig.maxlen_uname and name not in dns_entries:
					dns_entries[name] = 1
					add_entry(name, '%s Host entry' % host)

	# Do Unix group files.
	#
	for file, host in rbconfig.files_group:
		fd = open(file)
		for line in fd.readlines():
			grp = line.split(':')[0].lower()
			if len(grp) <= rbconfig.maxlen_uname and grp not in ldap_groups:
				add_entry(grp, '%s Unix group' % host)

	print('[%d].' % len(list(entries.keys())), end=' ')

	# Delete any dynamic entries in LDAP reserved tree that are not in the
	# list we built i.e. unused.
	#
	print('Purge', end=' ')

	purge_dn = []
	res = udb.list_reserved_dynamic()
	for uid in res:
		if uid not in entries:
			purge_dn.append('uid=%s,%s' % (uid, rbconfig.ldap_reserved_tree))

	for i in purge_dn:
		if not opt.test:
			udb.ldap.delete_s(i)
		else:
			print('delete', i)
	print('[%d]' % len(purge_dn), end=' ')

	# Now add/update entries.
	#
	print('Populate.', end=' ')

	total_mods = total_adds = 0

	for k, v in list(entries.items()):
		if k in ldap_reserveds:
			if k not in ldap_reserveds_static and v != ldap_reserveds[k]:
				if not opt.test:
					udb.ldap.modify_s('uid=%s,%s' % (k, rbconfig.ldap_reserved_tree), ((ldap.MOD_REPLACE, 'description', v),))
				else:
					print('modify %-8s [%s] [%s]' % (k, v, ldap_reserveds[k]))
				total_mods += 1
		else:
			if not opt.test:
				udb.ldap.add_s('uid=%s,%s' % (k, rbconfig.ldap_reserved_tree), (('uid', k), ('description', v), ('objectClass', ('reserved', 'top'))))
			else:
				print('add %-8s [%s]' % (k, v))
			total_adds += 1

	print('Done [%d adds, %d mods]' % (total_adds, total_mods))

	udb.close()

if __name__ == "__main__":
	main()
