#-----------------------------------------------------------------------------#
# MODULE DESCRIPTION                                                          #
#-----------------------------------------------------------------------------#

"""RedBrick User Database Module; contains RBUserDB class."""

# System modules

import math
import re
import sys
import time
import types

# 3rd party modules

import pgdb

# RedBrick modules

from rberror import *
from rbopt import *
from rbuser import *

#-----------------------------------------------------------------------------#
# DATA                                                                        #
#-----------------------------------------------------------------------------#

__version__ = '$Revision: 1.1 $'
__author__  = 'Cillian Sharkey'

#-----------------------------------------------------------------------------#
# CLASSES                                                                     #
#-----------------------------------------------------------------------------#

class RBUserDB:
	"""Class to interface with user database."""

	def __init__(self):
		"""Create new RBUserDB object."""

		self.opt = RBOpt()
		self.dbh = None
		self.cur = None

	def connect(self, host = 'localhost', database = 'userdb'):
		"""Connect to database. Custom hostname and database name may
		be given."""

		self.dbh = pgdb.connect(host = host, database = database)
		self.cur = self.dbh.cursor()

	def close(self):
		"""Close database connection"""

		if self.dbh:
			self.dbh.commit()
			self.dbh.close()
	
	def setopt(self, opt):
		"""Use given RBOpt object to retrieve options."""

		self.opt = opt
	
	#---------------------------------------------------------------------#
	# DATA                                                                #
	#---------------------------------------------------------------------#
	
	# Valid account usertypes and descriptions.
	#
	usertypes = {
		'reserved':	'Reserved name (NOT an account)',
		'system':	'System/pseudo-user account',
		'member':	'Normal member',
		'associat':	'Graduate/associate member',
		'staff':	'DCU staff member',
		'society':	'DCU society',
		'club':		'DCU club',
		'projects':	'RedBrick/DCU/Course project account',
		'guest':	'Guest account',
		'intersoc':	'Account for society from another college',
		'committe':	'Committee member or a position account',
		'redbrick':	'RedBrick related account',
		'dcu':		'DCU related account'
	}

	# "Ordered" list of usertypes for listing.
	#
	usertypes_list = ('system', 'reserved', 'member', 'associat', 'staff', 'society', 'club', 'dcu', 'projects', 'committe', 'redbrick', 'intersoc', 'guest');

	# List of system usertypes.
	#
	usertypes_system = ('system', 'reserved')

	# List of paying usertypes.
	#
	usertypes_paying = ('member', 'associat', 'staff', 'committe', 'guest')

	# List of dcu usertypes (i.e. require a id number)
	#
	usertypes_dcu = ('member', 'associat', 'staff', 'committe')

	# Pseudo usertypes for conversion to committee positions.
	#
	convert_usertypes = {
		'admin':	'Elected admin',
		'webmaster':	'Elected webmaster',
		'helpdesk':	'Elected helpdesk'
	}

	#---------------------------------------------------------------------#
	# USER CHECKING AND INFORMATION RETRIEVAL METHODS                     #
	#---------------------------------------------------------------------#
	
	def check_userfree(self, username, check_reserved = 1):
 		"""Check if a username is free.
		
		If username is not free, an RBFatalError is raised. If the
		username is in the additional reserved user table, an
		RBWarningError is raised.

		By default the additional reserved user table is checked,
		however when adding system or reserved users which may already
		have a Unix group name or DNS entry of the same name etc. it is
		useful to disable this check (check_reserved = 0).

		"""

		self.cur.execute("SELECT usertype, name FROM users WHERE username = '%s'" % username)
		
		if self.cur.rowcount:
			usertype, name = self.cur.fetchone();
			raise RBFatalError("Username '%s' is already taken by %s account (%s)" % (username, usertype, name))
		
		if not check_reserved:
			return
			
		self.cur.execute("SELECT info FROM reserved WHERE username = '%s'" % username)
		
		if self.cur.rowcount:
			info = self.cur.fetchone()[0];
			self.rberror(RBWarningError("Username '%s' is reserved (%s)" % (username, info)))

	def check_user_byname(self, username):
		"""Raise RBFatalError if given username does not exist in user
		database."""

		self.cur.execute('SELECT username FROM users WHERE username = %s', (username,)) 
		if self.cur.rowcount != 1:
			raise RBFatalError("User '%s' does not exist" % username)
		
	def check_user_byid(self, id):
		"""Raise RBFatalError if given id does not belong to a user in
		user database."""

		self.cur.execute('SELECT username FROM users WHERE id = %s', (id,)) 
		if self.cur.rowcount != 1:
			raise RBFatalError("User with id '%s' does not exist" % id)

	def get_usertype_byname(self, username):
		"""Return usertype for username in user database. Raise
		RBFatalError if user does not exist."""

		self.cur.execute('SELECT usertype FROM users WHERE username = %s', (username,))
		res = self.cur.fetchone()
		if res:
			return res[0]
		else:
			raise RBFatalError("User '%s' does not exist" % username)
		
	def get_user_byname(self, usr):
		"""Populate RBUser object with data from user with given
		username in user database. Raise RBFatalError if user does not
		exist."""

		self.cur.execute('SELECT username, usertype, name, newbie, email, id, course, year, years_paid, created_by, created_at, updated_by, updated_at, birthday FROM users WHERE username = %s', (usr.username,)) 
		res = self.cur.fetchone()
		if res:
			self.set_user(usr, res)
		else:
			raise RBFatalError("User '%s' does not exist" % usr.username)
		
	def get_user_byid(self, usr):
		"""Populate RBUser object with data from user with given id in
		user database. Raise RBFatalError if user does not exist."""

		self.cur.execute('SELECT username, usertype, name, newbie, email, id, course, year, years_paid, created_by, created_at, updated_by, updated_at, birthday FROM users WHERE id = %s', (usr.id,)) 
		res = self.cur.fetchone()
		if res:
			self.set_user(usr, res)
		else:
			raise RBFatalError("User with id '%s' does not exist" % usr.id)
		
	def get_userinfo_new(self, usr):
		"""Checks if ID already belongs to an existing user and if so
		raises RBFatalError. Populates RBUser object with data for new
		user from DCU databases otherwise raises RBWarningError."""
		
		# Check if id belongs to another user first.
		#
		if usr.id != None:
			tmpusr = RBUser(id = usr.id)
			try:
				self.get_user_byid(tmpusr)
			except RBError:
				pass
			else:
				raise RBFatalError("Id '%s' is already registered to %s (%s)" % (usr.id, tmpusr.username, tmpusr.name))
		
			self.get_dcu_byid(usr)
	
	def get_userinfo_renew(self, usr, curusr = None):
		"""Merge RBUser object with current data from DCU & user
		databases. Set oldusr if given to current data from user
		database."""

		# Load the user data currently in the database.
		#
		if not curusr:
			curusr = RBUser()
		curusr.username = usr.username
		curusr.id = usr.id
		if usr.username:
			self.get_user_byname(curusr)
		else:
			self.get_user_byid(curusr)
		
		usr.usertype = usr.usertype or curusr.usertype
		usr.id = usr.id != None and usr.id or curusr.id
		self.check_renewal_usertype(usr.usertype)

		# Load the dcu data using usertype and ID set in the given usr
		# or failing that from the current user database.
		#
		dcuusr = RBUser(username = usr.username, usertype = usr.usertype, id = usr.id)
		try:
			self.get_dcu_byid(dcuusr)
		except RBError, e:
			self.rberror(e)
		
		# Any attributes not set in the given usr are taken from the
		# current dcu database or failing that, the current user
		# database.
		#
		# Exceptions to this are updated_by which the caller must give
		# and email for associates as it may be changed from their DCU
		# address when they leave DCU so we don't want to automatically
		# overwrite it.
		#
		if usr.usertype == 'associat':
			dcuusr.email = None
		usr.merge(usr.usertype == 'associat' and RBUser(dcuusr, email = None) or dcuusr)
		usr.merge(RBUser(curusr, updated_by = None))

	def get_userdefaults_new(self, usr):
		"""Populate RBUser object with some reasonable default values
		for new user (usertype should be provided)."""

		if not usr.usertype:
			usr.usertype = 'member'

		if usr.usertype in self.usertypes_system:
			if not usr.email:
				usr.email = 'admins@redbrick.dcu.ie'

			if not usr.name:
				if usr.usertype == 'system':
					usr.name = 'System Account'
				else:
					usr.name = 'Reserved Name'

		if usr.newbie == None:
			usr.newbie = 1
					
		if usr.years_paid == None and usr.usertype in self.usertypes_paying and usr.usertype not in ('committe', 'guest'):
			usr.years_paid = 1

	def get_userdefaults_renew(self, usr, override = 0):
		"""Populate RBUser object with some reasonable default values
		for renewal user"""
		
		if usr.usertype in self.usertypes_paying:
			if usr.years_paid == None or usr.years_paid < 1:
				usr.years_paid = 1

	def get_dcu_byid(self, usr, override = 0):
		"""Populates RBUser object with data for new user from
		appropriate DCU database for the given usertype. If usertype
		is not given, all DCU databases are tried and the usertype is
		determined from which database has the given ID. If no data for
		ID, raise RBWarningError."""

		# No usertype given, so we try and determine it ourselves.
		#
		if not usr.usertype:
			try:
				self.get_staff_byid(usr, override)
			except RBError:
				try:
					self.get_student_byid(usr, override)
				except RBError, e:
					self.rberror(e)
				else:
					usr.usertype = 'member'
					return
			else:
				usr.usertype = 'staff'
				return

		# Graduates now remain in the (currently student, but may
		# change) LDAP tree for their life long email accounts so try
		# to load in information for associates (but don't fail if we
		# can't).
		#
		if usr.usertype in ('member', 'associat', 'committe'):
			try:
				self.get_student_byid(usr, override)
			except RBError, e:
				if usr.usertype != 'associat':
					self.rberror(e)
		# Not all staff may be in the LDAP tree, so don't fail if we
		# can't get their information either.
		#
		elif usr.usertype == 'staff':
			try:
				self.get_staff_byid(usr, override)
			except RBError:
				pass
	
	def get_student_byid(self, usr, override = 0):
		"""Populate RBUser object with data from user with given id in
		student database. Raise RBWarningError if user does not
		exist."""

		self.cur.execute('SELECT name, email, course, year FROM students WHERE id = %s', (usr.id,))
		res = self.cur.fetchone()
		if res:
			for k in ('name', 'email', 'course', 'year'):
				v = res.pop(0)
				if override or getattr(usr, k) == None:
					setattr(usr, k, v)
		else:
			# Note that all students *should* be in the LDAP tree,
			# but only raise a warning so that it can still be
			# overriden.
			#
			raise RBWarningError("Student id '%s' does not exist in database" % usr.id)
	
	def get_staff_byid(self, usr, override = 0):
		"""Populate RBUser object with data from user with given id in
		staff database. Raise RBWarningError if user does not exist."""

		self.cur.execute('SELECT name, email FROM staff WHERE id = %s', (usr.id,))
		res = self.cur.fetchone()
		if res:
			for k in ('name', 'email'):
				v = res.pop(0)
				if override or getattr(usr, k) == None:
					setattr(usr, k, v)
		else:
			raise RBWarningError("Staff id '%s' does not exist in database" % usr.id)
	
	def get_dummyid(self, usr):
		"""Set usr.id to unique 'dummy' DCU ID number."""

		self.cur.execute('SELECT id FROM users WHERE id >= 10000000 AND id < 20000000')
		results = self.cur.fetchone()
		
		if results:
			usr.id = results[0] + 1
		else:
			usr.id = 10000000

	#---------------------------------------------------------------------#
	# USER DATA SYNTAX CHECK METHODS                                      #
	#---------------------------------------------------------------------#

	def check_userdata(self, usr):
		"""Verifies RBUser object's user data with the various
		check_*() methods. Raises RBError if any data is not valid."""

		self.check_username(usr.username)
		self.check_usertype(usr.usertype)
		self.check_id(usr)
		self.check_email(usr)
		self.check_name(usr)
		self.check_years_paid(usr)
		self.check_updated_by(usr.updated_by)
		self.check_birthday(usr)

	def check_username(self, username):
	 	"""Raise RBFatalError if username is not valid."""

		if not username:
			raise RBFatalError('Username must be given')

		if re.search(r'[^a-z0-9_.-]', username):
			raise RBFatalError("Invalid characters in username")
	
		if len(username) > 8:
			raise RBFatalError("Username can not be longer than 8 characters")
		
		if not re.search(r'[a-z]', username):
			raise RBFatalError("Username must contain at least one letter")
		
		if re.search(r'^[^a-z0-9]', username):
			raise RBFatalError("Username must begin with letter or number")

	def check_usertype(self, usertype):
		"""Raise RBFatalError if usertype is not valid."""

		if not usertype:
			raise RBFatalError('Usertype must be given')

		if not self.usertypes.has_key(usertype):
			raise RBFatalError("Invalid usertype '%s'" % usertype)

	def check_convert_usertype(self, usertype):
		"""Raise RBFatalError if conversion usertype is not valid."""

		if not (self.usertypes.has_key(usertype) or self.convert_usertypes.has_key(usertype)):
			raise RBFatalError("Invalid conversion usertype '%s'" % usertype)
		
	def check_renewal_usertype(self, usertype):
		"""Raise RBFatalError if renewal usertype is not valid."""

		if not usertype in self.usertypes_paying:
			raise RBFatalError("Invalid renewal usertype '%s'" % usertype)
		
	def check_id(self, usr):
	 	"""Raise RBFatalError if ID is not valid for usertypes that require one."""

		if usr.usertype in self.usertypes_dcu:
			if usr.id != None:
				if type(usr.id) != types.IntType:
					raise RBFatalError('ID must be an integer')
				if usr.id < 10000000 or usr.id > 99999999:
					raise RBFatalError("Invalid ID '%s'" % (usr.id))
			elif usr.usertype not in ('committe', 'guest'):
				raise RBFatalError('ID must be given')

	def check_years_paid(self, usr):
	 	"""Raise RBFatalError if years_paid is not valid."""

		if usr.usertype in self.usertypes_paying:
			if usr.years_paid != None:
				if type(usr.years_paid) != types.IntType:
					raise RBFatalError('Years paid must be an integer')
				if usr.years_paid < -1:
					raise RBFatalError('Invalid number of years paid')
			elif usr.usertype not in ('committe', 'guest'):
				raise RBFatalError('Years paid must be given')
		
	def check_name(self, usr):
		"""Raise RBFatalError if name is not valid."""

		if not usr.name:
			raise RBFatalError('Name must be given')

		if usr.name.find(':') >= 0:
			raise RBFatalError("No colon ':' characters allowed in name")

	def check_email(self, usr):
	 	"""Raise RBError if email is not valid."""
		
		if not usr.email:
			raise RBFatalError('Email must be given')

		if not re.search(r'.+@.+', usr.email):
			raise RBFatalError("Invalid email address '%s'" % (usr.email))

		if usr.usertype in ('member', 'staff') and not re.search(r'.+@.*dcu\.ie', usr.email, re.I):
			self.rberror(RBWarningError("%s users should have a DCU email address" % (usr.usertype)))

	def check_updated_by(self, updated_by):
		"""Raise RBFatalError if updated_by is a valid username."""

		if not updated_by:
			raise RBFatalError('Updated by must be given')
		try:
			self.check_user_byname(updated_by)
		except RBError:
			raise RBFatalError("Updated by username '%s' is not valid" % updated_by)
		
	def check_birthday(self, usr):
	 	"""Raise RBFatalError if the birthday is not valid, if set (it's optional)."""
	
		if usr.birthday:
			if not re.search(r'^\d{4}-\d{1,2}-\d{1,2}$', usr.birthday):
				raise RBFatalError('Birthday format must be YYYY-MM-DD')
	
	def check_disuser_period(self, usr):
	 	"""Raise RBFatalError if the period of disuserment is not valid."""

		if usr.disuser_period and not re.search(r'^[-0-9a-zA-Z:"\'+ ]+$', usr.disuser_period):
			raise RBFatalError("Invalid characters in disuser period")

	def check_unpaid(self, usr):
		"""Raise RBWarningError if the user is already paid up."""

		if usr.years_paid != None and usr.years_paid > 0:
			self.rberror(RBWarningError("User '%s' is already paid!" % usr.username))

	#---------------------------------------------------------------------#
	# SINGLE USER METHODS                                                 #
	#---------------------------------------------------------------------#

	def add(self, usr):
		"""Add new RBUser object to database."""

		try:
			self.check_userfree(usr, not usr.usertype in self.usertypes_system)
			self.get_userinfo_new(usr)
			self.get_userdefaults_new(usr)
			self.check_userdata(usr)
		except RBError, e:
			self.rberror(e)

		self.execute('INSERT INTO users (username, usertype, name, newbie, email, id, course, year, years_paid, created_by, updated_by, birthday) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)', (usr.username, usr.usertype, usr.name, ('f', 't')[usr.newbie], usr.email, usr.id, usr.course, usr.year, usr.years_paid, usr.updated_by, usr.updated_by, usr.birthday))
		if not self.opt.test and self.cur.rowcount != 1:
			raise RBFatalError("Failed to add user '%s' to database" % usr.username)
		self.dbh.commit()
	
	def delete(self, username):
		"""Delete user from database."""

		self.execute('DELETE FROM users WHERE username = %s', (username,))
		if not self.opt.test and self.cur.rowcount != 1:
			raise RBFatalError("Failed to delete '%s'" % username)
		self.dbh.commit()

	def renew(self, usr):
		"""Renew and update RBUser object in database."""

		curusr = RBUser()

		try:
			self.get_userinfo_renew(usr, curusr)
			self.check_unpaid(curusr)
			self.get_userdefaults_renew(usr)
			self.check_userdata(usr)
		except RBError, e:
			self.rberror(e)

		self.execute('UPDATE users SET usertype = %s, newbie = %s, name = %s, email = %s, id = %s, course = %s, year = %s, years_paid = %s, updated_by = %s, birthday = %s WHERE username = %s', (usr.usertype, ('f','t')[usr.newbie], usr.name, usr.email, usr.id, usr.course, usr.year, usr.years_paid, usr.updated_by, usr.birthday, usr.username))
		if not self.opt.test and self.cur.rowcount != 1:
			raise RBFatalError("Failed to update '%s'" % usr.username)
		self.dbh.commit()

	def update(self, usr):
		"""Update RBUser object in database."""

		self.check_userdata(usr)

		self.execute('UPDATE users SET newbie = %s, name = %s, email = %s, id = %s, course = %s, year = %s, years_paid = %s, updated_by = %s, birthday = %s WHERE username = %s', (('f','t')[usr.newbie], usr.name, usr.email, usr.id, usr.course, usr.year, usr.years_paid, usr.updated_by, usr.birthday, usr.username))
		if not self.opt.test and self.cur.rowcount != 1:
			raise RBFatalError("Failed to update '%s'" % usr.username)
		self.dbh.commit()

	def rename(self, username, newusername, updated_by):
		"""Rename a user."""

		usr = RBUser()
		usr.username = username
		self.get_user_byname(usr)
		self.check_userfree(newusername, not usr.usertype in self.usertypes_system)
		self.check_updated_by(updated_by)

		self.execute('UPDATE users SET username = %s, updated_by = %s WHERE username = %s', (newusername, updated_by, username))
		if not self.opt.test and self.cur.rowcount != 1:
			raise RBFatalError("Failed to rename '%s'" % username)
		self.dbh.commit()

	def convert(self, username, usertype, updated_by):
		"""Convert a user to a different usertype."""

		# If usertype is one of the pseudo usertypes, change the
		# usertype to 'committe' for the database conversion.
		#
		if self.convert_usertypes.has_key(usertype):
			usertype = 'committe'

		self.check_usertype(usertype)
		self.check_updated_by(updated_by)

		self.execute('UPDATE users SET usertype = %s, updated_by = %s WHERE username = %s', (usertype, updated_by, username))
		if not self.opt.test and self.cur.rowcount != 1:
			raise RBFatalError("Failed to convert usertype of '%s'" % username)
		self.dbh.commit()

	#---------------------------------------------------------------------#
	# SINGLE USER INFORMATION METHODS                                     #
	#---------------------------------------------------------------------#

	def show(self, usr):
		"""Show RBUser object information on standard output."""

		for i in ('username', 'usertype', 'name', 'newbie', 'email', 'id', 'course', 'year', 'years_paid', 'created_by', 'created_at', 'updated_by', 'updated_at', 'birthday'):
			if i == 'newbie':
				print "%12s:" % i,
				if usr.newbie: print "yes"
				else: print "no"
			elif getattr(usr, i) != None:
				print "%12s: %s" % (i, getattr(usr, i))
	
	#---------------------------------------------------------------------#
	# BATCH INFORMATION METHODS                                           #
	#---------------------------------------------------------------------#

	def user_list(self):
		"""Return list of all usernames."""

		self.cur.execute('SELECT username FROM users')
		return [i[0] for i in self.cur.fetchall()]

	def renewals_list(self):
		"""Return list of all paid renewal (non-newbie) usernames."""

		self.cur.execute("SELECT username FROM users WHERE years_paid > 0 AND newbie = 'f'")
		return [i[0] for i in self.cur.fetchall()]

	def newbies_list(self):
		"""Return list of all paid newbie usernames."""

		self.cur.execute("SELECT username FROM users WHERE years_paid > 0 AND newbie = 't'")
		return [i[0] for i in self.cur.fetchall()]

	def non_system_list(self):
		"""Return list of all non-system usernames with their usertype."""

		self.cur.execute("SELECT username, usertype FROM users WHERE usertype != 'system' AND usertype != 'reserved'")
		return self.cur.fetchall()

	def freename_list(self):
		"""Return list of all usernames that are taken."""

		self.cur.execute('SELECT username FROM users UNION SELECT username FROM reserved')
		return [i[0] for i in self.cur.fetchall()]

		
	def unpaid_list(self):
		"""Return list of all non-renewed users."""
		
		self.cur.execute('SELECT username FROM users WHERE years_paid <= 0')
		return [i[0] for i in self.cur.fetchall()]

	def unpaid_list_normal(self):
		"""Return list of all normal non-renewed users."""

		self.cur.execute('SELECT username FROM users WHERE years_paid = 0')
		return [i[0] for i in self.cur.fetchall()]

	def unpaid_list_grace(self):
		"""Return list of all grace non-renewed users."""

		self.cur.execute('SELECT username FROM users WHERE years_paid < 0')
		return [i[0] for i in self.cur.fetchall()]

	def search_users_byusername(self, username):
		"""Search user database by username and return results
		((username, usertype, id, name, course, year, email), ...)"""

		self.cur.execute('SELECT username, usertype, id, name, course, year, email FROM users WHERE username LIKE %s', ('%%%s%%' % username,))
		return self.cur.fetchall()

	def search_users_byid(self, id):
		"""Search user database by id and return results
		((username, id, name, course, year), ...)"""

		return self.search_users('id LIKE', id)

	def search_users_byname(self, name):
		"""Search user database by name and return results as per
		search_users_byid()."""

		return self.search_users('name ILIKE', name)

	def search_users(self, where, var):
		"""Performs actual user database search with given where clause
		and data."""

		self.cur.execute('SELECT username, usertype, id, name, course, year, email FROM users WHERE ' + where + ' %s', ('%%%s%%' % var,))
		return self.cur.fetchall()

	def search_dcu_byid(self, id):
		"""Search user & DCU databases by id and return results
		((username, id, name, course, year), ...)"""

		return self.search_dcu('s.id LIKE', id)

	def search_dcu_byname(self, name):
		"""Search user & DCU databases by name and return results as
		per search_dcu_byid"""

		return self.search_dcu('s.name ILIKE', name)

	def search_dcu(self, where, var):
		"""Performs actual DCU database search with given where clause
		and data."""

		var = '%%%s%%' % var
		self.cur.execute('SELECT u.username, u.usertype, s.id, s.name, s.course, s.year, s.email FROM students s LEFT JOIN users u USING (id) WHERE ' + where + ' %s', (var,))
		res = self.cur.fetchall()
		self.cur.execute('SELECT u.username, u.usertype, s.id, s.name, s.email FROM staff s LEFT JOIN users u USING (id) WHERE ' + where + '%s', (var,))
		return [(username, usertype, id, name, None, None, email) for username, usertype, id, name, email in self.cur.fetchall()] + res

	#---------------------------------------------------------------------#
	# BATCH METHODS                                                       #
	#---------------------------------------------------------------------#

	def newyear(self):
		"""Prepare database for start of new academic year.
		
		This involves the following: creating a backup of the current
		users table for the previous academic year for archival
		purposes, reducing all paying users subscription by one year
		and setting the newbie field to false for all users.

		"""
		
		year = time.localtime()[0] - 1

		self.execute('CREATE TABLE users%d AS SELECT * FROM users', (year,))
		self.execute('CREATE INDEX users%d_username_key ON users%d (username)', (year, year))
		self.execute('CREATE INDEX users%d_id_key ON users%d (id)', (year, year))
		self.execute('UPDATE users SET years_paid = years_paid - 1 WHERE years_paid IS NOT NULL')
		self.execute("UPDATE users SET newbie = 'f'")
		self.dbh.commit()

	#---------------------------------------------------------------------#
	# MISCELLANEOUS METHODS                                               #
	#---------------------------------------------------------------------#

	def stats(self):
		"""Print database statistics on standard output."""

		tmp = {}
		for i in self.usertypes_list:
			tmp[i] = 0

		self.cur.execute("SELECT usertype, count(*) FROM users GROUP BY usertype")
		for u, c in self.cur.fetchall():
			tmp[u] = c

		for i in self.usertypes_list:
			print "%20s %5d" % (i, tmp[i])
		
		print "%s  %s" % ("-" * 20, "-" * 4)
		
		self.cur.execute("SELECT COUNT(*) FROM users")
		print "%20s %5d\n" % ('Total userdb entries', self.cur.fetchone()[0])
		
		self.cur.execute("SELECT COUNT(*) FROM users WHERE years_paid > 0")
		print "%20s %5d" % ('Paid', self.cur.fetchone()[0])
		
		self.cur.execute("SELECT COUNT(*) FROM users WHERE years_paid < 1")
		print "%20s %5d" % ('Not paid', self.cur.fetchone()[0])
		
		self.cur.execute("SELECT COUNT(*) FROM users WHERE years_paid IS NOT NULL")
		print "%s  %s" % ("-" * 20, "-" * 4)
		print "%20s %5d\n" % ('Total paying users', self.cur.fetchone()[0])
		
		self.cur.execute("SELECT COUNT(*) FROM users WHERE (usertype = 'member' OR usertype = 'committe' OR usertype = 'staff') AND years_paid > 0")
		print "%20s %5d" % ('Paid members', self.cur.fetchone()[0])
		
		self.cur.execute("SELECT COUNT(*) FROM users WHERE (usertype = 'member' OR usertype = 'staff') AND years_paid > 0")
		print "%20s %5.0f (square root of paid non-cmte members, rounded up)" % ('Quorum', math.ceil(math.sqrt(self.cur.fetchone()[0])))
		
		self.cur.execute("SELECT COUNT(*) FROM users WHERE newbie = 't'")
		print "%20s %5d (since start of year)" % ('New', self.cur.fetchone()[0])

	#--------------------------------------------------------------------#
	# INTERNAL METHODS                                                   #
	#--------------------------------------------------------------------#
	
	def set_user(self, usr, res):
		"""Populate RBUser object with information from SQL query."""

		for k in ('username', 'usertype', 'name', 'newbie', 'email', 'id', 'course', 'year', 'years_paid', 'created_by', 'created_at', 'updated_by', 'updated_at', 'birthday'):
			v = res.pop(0)
			if getattr(usr, k) == None:
				setattr(usr, k, v)

	def execute(self, sql, params = None):
		"""Wrapper method for executing given SQL query."""

		if params == None:
			params = ()
		if self.opt.test:
			print >> sys.stderr, "TEST:", (sql % params)
		else:
			self.cur.execute(sql, params)

	#--------------------------------------------------------------------#
	# ERROR HANDLING                                                     #
	#--------------------------------------------------------------------#

	def rberror(self, e):
		"""Handle RBError exceptions."""
		
		if self.opt.override and isinstance(e, RBWarningError):
			return

		# If we reach here it's either a FATAL error or there was no
		# override for a WARNING error, so raise it again to let the
		# caller handle it.
		#
		raise e
