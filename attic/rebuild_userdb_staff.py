#! /usr/bin/env python

"""Rebuild staff table in userdb from DCU's LDAP staff tree."""

import ldap
import pgdb
import re

__version__ = "$Revision$"
__author__ = "Cillian Sharkey"

def main():
	"""Program entry function."""

	ldaphost = 'atlas.dcu.ie'
	
	dbh = pgdb.connect(database = 'userdb')
	cur = dbh.cursor()
	
	l = ldap.open(ldaphost)
	l.simple_bind_s('', '') # anonymous bind
	
	print 'userdb/staff:',
	
	print 'Search',
	staff = l.search_s('ou=staff,o=dcu', ldap.SCOPE_SUBTREE, 'objectclass=person', ('fullName', 'givenName', 'sn', 'mail', 'cn', 'gecos'))
	print '[%d].' % len(staff),
	
	# Delete all existing entries.
	#
	print 'Purge.',
	cur.execute('delete from staff')
	
	# Add new entries.
	#
	print 'Populate.',
	
	total = 0
	ids = {}
	insert_staff = "INSERT INTO staff (id, name, email) VALUES (%s, %s, %s)"
	re_gecos = re.compile(r'^(.*),.*(\d{8})')
	
	for i in staff:
		try:
			attr = i[1]
			id = name = None
	
			# Check gecos for full name and staff id.
			#
			if attr.has_key('gecos'):
				res = re_gecos.search(attr['gecos'][0])
				if res:
					name = res.group(1)
					id = int(res.group(2))
	
			# If no id in gecos, cycle through each cn attribute value
			# until we find one that is a number (which can only be the id
			# number).
			#
			if not id:
				if attr.has_key('cn'):
					for j in attr['cn']:
						try:
							id = int(j)
						except ValueError:
							pass
						else:
							break
				else:
					# No id found!
					continue
			
			# Ignore entries with duplicate IDs.
			#
			if ids.has_key(id):
				continue
			else:
				ids[id] = 1
	
			# If no name found from gecos and no fullName attribute,
			# construct their full name from first name ('givenName')
			# followed by their surname ('sn').
			#
			if not name:
				if attr.has_key('fullName'):
					name = attr['fullName'][0]
				else:
					name = '%s %s' % (attr['givenName'][0], attr['sn'][0])
	
			email = attr['mail'][0]
			
			cur.execute(insert_staff, (id, name, email))
			total += 1
		except KeyError, e:
			pass
	
	print 'Done [%d/%d].' % (total, len(staff))

	dbh.commit()
	cur.execute('END; VACUUM ANALYZE staff')
	dbh.close()
	l.unbind()
	
	
if __name__ == "__main__":
	main()
