#! /usr/bin/env python

"""Rebuild students table in userdb from DCU's LDAP student tree."""

import ldap
import pgdb

__version__ = "$Revision: 1.1 $"
__author__ = "Cillian Sharkey"

def main():
	"""Program entry function."""

	ldaphost = 'atlas.dcu.ie'
	
	dbh = pgdb.connect(database = 'userdb')
	cur = dbh.cursor()
	
	l = ldap.open(ldaphost)
	l.simple_bind_s('', '') # anonymous bind
	
	print 'userdb/students:',
	
	print 'Search',
	students = l.search_s('ou=students,o=dcu', ldap.SCOPE_SUBTREE, 'objectclass=person', ('givenName', 'sn', 'mail', 'l', 'cn'))
	print '[%d].' % len(students),
	
	# Delete all existing entries.
	#
	print 'Purge.',
	cur.execute('delete from students')
	
	# Add new entries.
	#
	print 'Populate.',
	
	total = 0
	ids = {}
	insert_student = 'INSERT INTO students (id, name, email, course, year) VALUES (%d, %s, %s, %s, %s)'
	
	for i in students:
		try:
			attr = i[1]
			
			# Extract course & year from 'l' attribute value. Assumes last
			# character is the year (1, 2, 3, 4, X, O, C, etc.) and the rest is the
			# course name. Uppercase course & year for consistency.
			#
			course = attr['l'][0][:-1].upper() or 'N/A'
			year = attr['l'][0][-1].upper() or 'N/A'
			
			# Cycle through each 'cn' attribute value until we find one that is a
			# number (which can only be the id number).
			#
			for j in attr['cn']:
				try:
					id = int(j)
				except ValueError:
					pass
				else:
					break
			else:
				# No ID number found! Skip this ldap entry.
				continue
		
			if ids.has_key(id):
				continue
			else:
				ids[id] = 1
	
			# Construct their full name from first name ('givenName') followed by
			# their surname ('sn').
			#	
			name = '%s %s' % (attr['givenName'][0], attr['sn'][0])
			email = attr['mail'][0]
			
			cur.execute(insert_student, (id, name, email, course, year))
			total += 1
		except KeyError:
			pass
	
	print 'Done [%d/%d].' % (total, len(students))
	
	dbh.commit()
	cur.execute('END; VACUUM ANALYZE students')
	dbh.close()
	l.unbind()


if __name__ == "__main__":
	main()
