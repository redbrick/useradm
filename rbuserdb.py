#-----------------------------------------------------------------------------#
# MODULE DESCRIPTION                                                          #
#-----------------------------------------------------------------------------#

"""RedBrick User Database Module; contains RBUserDB class."""

# System modules

import crypt
import math
import random
import re
import sys
import time
import types

# 3rd party modules

import ldap

# RedBrick modules

import rbconfig
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
		self.ldap = None
		self.ldap_dcu = None

	def connect(self, uri = rbconfig.ldap_uri, dn = rbconfig.ldap_root_dn, password = None, dcu_uri = rbconfig.ldap_dcu_uri):
		"""Connect to databases.
	
		Custom URI, DN and password may be given for RedBrick LDAP.
		Password if not given will be read from shared secret file set
		in rbconfig.

		Custom URI may be given for DCU LDAP.
		
		"""

		if not password:
			try:
				fd = open(rbconfig.ldap_rootpw_file, 'r')
				password = fd.readline().rstrip()
			except IOError:
				raise RBFatalError("Unable to open LDAP root password file")
			fd.close()
		
		# Default protocol seems to be 2, set to 3.
		ldap.set_option(ldap.OPT_PROTOCOL_VERSION, 3)

		# Connect to RedBrick LDAP.
		self.ldap = ldap.initialize(uri)
		self.ldap.simple_bind_s(dn, password)
		
		# Connect to DCU LDAP (anonymous bind).
		self.ldap_dcu = ldap.initialize(dcu_uri)
		self.ldap_dcu.simple_bind_s('', '') 

	def close(self):
		"""Close database connections."""

		if self.ldap:
			self.ldap.unbind()
		if self.ldap_dcu:
			self.ldap_dcu.unbind()
	
	def setopt(self, opt):
		"""Use given RBOpt object to retrieve options."""

		self.opt = opt
	
	#---------------------------------------------------------------------#
	# USER CHECKING AND INFORMATION RETRIEVAL METHODS                     #
	#---------------------------------------------------------------------#
	
	def check_userfree(self, uid):
 		"""Check if a username is free.
		
		If username is already used or is an LDAP group, an
		RBFatalError is raised. If the username is in the additional
		reserved LDAP tree, an RBWarningError is raised and checked if
		it is to be overridden.

		"""

		res = self.ldap.search_s(rbconfig.ldap_accounts_tree, ldap.SCOPE_ONELEVEL, 'uid=%s' % uid)
		if res:
			raise RBFatalError("Username '%s' is already taken by %s account (%s)" % (uid, res[0][1]['objectClass'][0], res[0][1]['cn'][0]))

		res = self.ldap.search_s(rbconfig.ldap_group_tree, ldap.SCOPE_ONELEVEL, 'cn=%s' % uid)
		if res:
			raise RBFatalError("Username '%s' is reserved (LDAP Group)" % uid)

		res = self.ldap.search_s(rbconfig.ldap_reserved_tree, ldap.SCOPE_ONELEVEL, 'uid=%s' % uid)
		if res:
			self.rberror(RBWarningError("Username '%s' is reserved (%s)" % (uid, res[0][1]['description'][0])))

	def check_user_byname(self, uid):
		"""Raise RBFatalError if given username does not exist in user
		database."""

		if not self.ldap.search_s(rbconfig.ldap_accounts_tree, ldap.SCOPE_ONELEVEL, 'uid=%s' % uid):
			raise RBFatalError("User '%s' does not exist" % uid)
		
	def check_user_byid(self, id):
		"""Raise RBFatalError if given id does not belong to a user in
		user database."""

		if not self.ldap.search_s(rbconfig.ldap_accounts_tree, ldap.SCOPE_ONELEVEL, 'id=%s' % id):
			raise RBFatalError("User with id '%s' does not exist" % id)

	def check_group_byname(self, group):
		"""Raise RBFatalError if given group does not exist in group
		database."""

		if not self.ldap.search_s(rbconfig.ldap_group_tree, ldap.SCOPE_ONELEVEL, 'cn=%s' % group):
			raise RBFatalError("Group '%s' does not exist" % group)
		
	def check_group_byid(self, gid):
		"""Raise RBFatalError if given id does not belong to a group in
		group database."""

		if not self.ldap.search_s(rbconfig.ldap_group_tree, ldap.SCOPE_ONELEVEL, 'gidNumber=%s' % gid):
			raise RBFatalError("Group with id '%s' does not exist" % gid)
		
	#---------------------------------------------------------------------#
	# INFORMATION RETRIEVAL METHODS                                       #
	#---------------------------------------------------------------------#
	
	# XXX still needed ?
#	def get_usertype_byname(self, uid):
#		"""Return usertype for username in user database. Raise
#		RBFatalError if user does not exist."""
#
#		res = self.ldap.search_s(rbconfig.ldap_accounts_tree, ldap.SCOPE_ONELEVEL, 'uid=%s' % usr.uid, ('objectClass',))
#		if res:
#			for i in res[0][1]['objectClass']:
#				if rbconfig.usertypes.has_key(i):
#					return i
#			else:
#				raise RBFatalError("Unknown usertype for user '%s'" % uid)
#		else:
#			raise RBFatalError("User '%s' does not exist" % uid)
		
	def get_user_byname(self, usr):
		"""Populate RBUser object with data from user with given
		username in user database. Raise RBFatalError if user does not
		exist."""

		res = self.ldap.search_s(rbconfig.ldap_accounts_tree, ldap.SCOPE_ONELEVEL, 'uid=%s' % usr.uid)
		if res:
			self.set_user(usr, res[0])
		else:
			raise RBFatalError("User '%s' does not exist" % usr.uid)
		
	def get_user_byid(self, usr):
		"""Populate RBUser object with data from user with given id in
		user database. Raise RBFatalError if user does not exist."""

		res = self.ldap.search_s(rbconfig.ldap_accounts_tree, ldap.SCOPE_ONELEVEL, 'id=%s' % usr.id)
		if res:
			self.set_user(usr, res[0])
		else:
			raise RBFatalError("User with id '%s' does not exist" % usr.id)
		
	def get_userinfo_new(self, usr):
		"""Checks if ID already belongs to an existing user and if so
		raises RBFatalError. Populates RBUser object with data for new
		user from DCU databases otherwise raises RBWarningError."""
		
		if usr.id != None:
			tmpusr = RBUser(id = usr.id)
			try:
				self.get_user_byid(tmpusr)
			except RBError:
				pass
			else:
				raise RBFatalError("Id '%s' is already registered to %s (%s)" % (usr.id, tmpusr.uid, tmpusr.name))
		
			self.get_dcu_byid(usr)
	
	def get_userinfo_renew(self, usr, curusr = None, override = 0):
		"""Merge RBUser object with current data from DCU & user
		databases. Set curusr if given to current data from user
		database."""

		# Load the user data currently in the database.
		#
		if not curusr:
			curusr = RBUser()
		curusr.uid = usr.uid
		curusr.id = usr.id
		if usr.uid:
			self.get_user_byname(curusr)
		else:
			self.get_user_byid(curusr)
		
		usr.usertype = usr.usertype or curusr.usertype
		usr.id = usr.id != None and usr.id or curusr.id
		self.check_renewal_usertype(usr.usertype)

		# Load the dcu data using usertype and ID set in the given usr
		# or failing that from the current user database.
		#
		dcuusr = RBUser(uid = usr.uid, usertype = usr.usertype, id = usr.id)
		try:
			self.get_dcu_byid(dcuusr, override = override)
		except RBError, e:
			self.rberror(e)
		
		# Any attributes not set in the given usr are taken from the
		# current dcu database or failing that, the current user
		# database.
		#
		# Exceptions to this are:
		#
		# - updatedby: caller must give this
		# - email: for associates as it may be changed from their DCU
		#   address when they leave DCU so we don't want to
		#   automatically overwrite it.
		# - usertype: if get_dcu_byid finds the dcu details, it'll set
		#   the usertype as appropriate when override option is given,
		#   so we automatically override this here too.
		#
		if dcuusr.usertype:
			usr.usertype = dcuusr.usertype
		if usr.usertype == 'associat':
			dcuusr.altmail = None
		usr.merge(dcuusr)
		usr.merge(RBUser(curusr, updatedby = None))

	def get_userdefaults_new(self, usr):
		"""Populate RBUser object with default values for a new user.

		Usertype should be provided, but a default of member will be
		assumed.
		
		"""

		if not usr.usertype:
			usr.usertype = 'member'

		if usr.newbie == None:
			usr.newbie = 1
					
		if usr.yearsPaid == None and usr.usertype in rbconfig.usertypes_paying and usr.usertype not in ('committe', 'guest'):
			usr.yearsPaid = 1

	def get_userdefaults_renew(self, usr, override = 0):
		"""Populate RBUser object with some reasonable default values
		for renewal user"""
		
		if usr.usertype in rbconfig.usertypes_paying:
			if usr.yearsPaid == None or usr.yearsPaid < 1:
				usr.yearsPaid = 1

	def get_dcu_byid(self, usr, override = 0):
		"""Populates RBUser object with data for new user from
		appropriate DCU database for the given usertype. If usertype
		is not given, all DCU databases are tried and the usertype is
		determined from which database has the given ID. If no data for
		ID, raise RBWarningError."""

		# Just try all databases for a match regardless if
		# usertype was given or not. If usertype wasn't set or the
		# override option is given, set the usertype to the
		# corresponding database that had the ID.
		#
		usertype = None
		try:
			self.get_staff_byid(usr, override)
		except RBError:
			try:
				self.get_alumni_byid(usr, override)
			except RBError, e:
				try:
					self.get_student_byid(usr, override)
				except RBError, e:
					if usr.usertype not in ('associat', 'staff'):
						self.rberror(e)
				else:
					usertype = 'member'
			else:
				usertype = 'associat'
		else:
			usertype = 'staff'

		if usertype and (override or not usr.usertype):
			usr.usertype = usertype

		return

		# Graduates now remain in the (currently student, but may
		# change) LDAP tree for their life long email accounts so try
		# to load in information for associates (but don't fail if we
		# can't).
		#
#		if usr.usertype in ('member', 'associat', 'committe'):
#			try:
#				self.get_student_byid(usr, override)
#			except RBError, e:
#				if usr.usertype != 'associat':
#					self.rberror(e)
#		# Not all staff may be in the LDAP tree, so don't fail if we
#		# can't get their information either.
#		#
#		elif usr.usertype == 'staff':
#			try:
#				self.get_staff_byid(usr, override)
#			except RBError:
#				pass
	
	def get_student_byid(self, usr, override = 0):
		"""Populate RBUser object with data from user with given id in
		student database.
		
		By default will only populate RBUser attributes that have no
		value (None) unless override is enabled.
		
		Note that all students *should* be in the database, but only
		raise a RBWarningError if user does not exist.
	
		"""

		res = self.ldap_dcu.search_s(rbconfig.ldap_dcu_students_tree, ldap.SCOPE_SUBTREE, 'cn=%s' % usr.id)
		if res:
			self.set_user_dcu(usr, res[0], override)
			self.set_user_dcu_student(usr, res[0], override)
		else:
			raise RBWarningError("Student id '%s' does not exist in database" % usr.id)
	
	def get_alumni_byid(self, usr, override = 0):
		"""Populate RBUser object with data from user with given id in
		alumni database.
		
		By default will only populate RBUser attributes that have no
		value (None) unless override is enabled.
		
		Not all alumni will be in the database, so only raise a
		RBWarningError if user does not exist.
	
		"""

		res = self.ldap_dcu.search_s(rbconfig.ldap_dcu_alumni_tree, ldap.SCOPE_SUBTREE, 'cn=%s' % usr.id)
		if res:
			self.set_user_dcu(usr, res[0], override)
			self.set_user_dcu_alumni(usr, res[0], override)
		else:
			raise RBWarningError("Alumni id '%s' does not exist in database" % usr.id)
	
	def get_staff_byid(self, usr, override = 0):
		"""Populate RBUser object with data from user with given id in
		staff database.
		
		By default will only populate RBUser attributes that have no
		value (None) unless override is enabled.
		
		Not all staff are in the database, so only raise a
		RBWarningError if user does not exist.
	
		"""

		# Staff ID is not consistently set. It will either be in the cn
		# or in the gecos, so try both.
		#
		res = self.ldap_dcu.search_s(rbconfig.ldap_dcu_staff_tree, ldap.SCOPE_SUBTREE, '(|(cn=%s)(gecos=*,*%s))' % (usr.id, usr.id))
		if res:
			self.set_user_dcu(usr, res[0], override)
			self.set_user_dcu_staff(usr, res[0], override)
		else:
			raise RBWarningError("Staff id '%s' does not exist in database" % usr.id)
	
	def get_dummyid(self, usr):
		"""Set usr.id to unique 'dummy' DCU ID number."""

		raise RBFatalError('NOT YET IMPLEMENTED')

		res = self.ldap.search_s(rbconfig.ldap_accounts_tree, ldap.SCOPE_ONELEVEL, '(&(id>=10000000)(id<20000000))"' % (usr.uid))
		if res:
			usr.id = int(results[0][1]['id'][0]) + 1
		else:
			usr.id = 10000000

	def get_gid_byname(self, group):
		"""Get gid for given group name.
		
		Raise RBFatalError if given name does not belong to a group in
		group database."""

		res = self.ldap.search_s(rbconfig.ldap_group_tree, ldap.SCOPE_ONELEVEL, 'cn=%s' % group)
		if res:
			return int(res[0][1]['gidNumber'][0])
		else:
			raise RBFatalError("Group '%s' does not exist" % group)

	def get_group_byid(self, gid):
		"""Get group name for given group ID.
		
		Raise RBFatalError if given id does not belong to a group in
		group database."""

		res = self.ldap.search_s(rbconfig.ldap_group_tree, ldap.SCOPE_ONELEVEL, 'gidNumber=%s' % gid)
		if res:
			return res[0][1]['cn'][0]
		else:
			raise RBFatalError("Group with id '%s' does not exist" % gid)

	#---------------------------------------------------------------------#
	# USER DATA SYNTAX CHECK METHODS                                      #
	#---------------------------------------------------------------------#

	def check_userdata(self, usr):
		"""Verifies RBUser object's user data with the various
		check_*() methods. Raises RBError if any data is not valid."""

		self.check_username(usr.uid)
		self.check_usertype(usr.usertype)
		self.check_id(usr)
		self.check_email(usr)
		self.check_name(usr)
		self.check_years_paid(usr)
		self.check_updatedby(usr.updatedby)
		self.check_birthday(usr)

	def check_username(self, uid):
	 	"""Raise RBFatalError if username is not valid."""

		if not uid:
			raise RBFatalError('Username must be given')

		if re.search(r'[^a-z0-9_.-]', uid):
			raise RBFatalError("Invalid characters in username")
	
		if len(uid) > rbconfig.maxlen_uname:
			raise RBFatalError("Username can not be longer than %d characters" % rbconfig.maxlen_uname)
		
		if not re.search(r'[a-z]', uid):
			raise RBFatalError("Username must contain at least one letter")
		
		if re.search(r'^[^a-z0-9]', uid):
			raise RBFatalError("Username must begin with letter or number")

	def check_usertype(self, usertype):
		"""Raise RBFatalError if usertype is not valid."""

		if not usertype:
			raise RBFatalError('Usertype must be given')

		if not rbconfig.usertypes.has_key(usertype):
			raise RBFatalError("Invalid usertype '%s'" % usertype)

	def check_convert_usertype(self, usertype):
		"""Raise RBFatalError if conversion usertype is not valid."""

		if not (rbconfig.usertypes.has_key(usertype) or rbconfig.convert_usertypes.has_key(usertype)):
			raise RBFatalError("Invalid conversion usertype '%s'" % usertype)
		
	def check_renewal_usertype(self, usertype):
		"""Raise RBFatalError if renewal usertype is not valid."""

		if not usertype in rbconfig.usertypes_paying:
			raise RBFatalError("Invalid renewal usertype '%s'" % usertype)
		
	def check_id(self, usr):
	 	"""Raise RBFatalError if ID is not valid for usertypes that require one."""

		if usr.usertype in rbconfig.usertypes_dcu:
			if usr.id != None:
				if type(usr.id) != types.IntType:
					raise RBFatalError('ID must be an integer')
				if usr.id < 10000000 or usr.id > 99999999:
					raise RBFatalError("Invalid ID '%s'" % (usr.id))
			elif usr.usertype not in ('committe', 'guest'):
				raise RBFatalError('ID must be given')

	def check_years_paid(self, usr):
	 	"""Raise RBFatalError if years_paid is not valid."""

		if usr.usertype in rbconfig.usertypes_paying:
			if usr.yearsPaid != None:
				if type(usr.yearsPaid) != types.IntType:
					raise RBFatalError('Years paid must be an integer')
				if usr.yearsPaid < -1:
					raise RBFatalError('Invalid number of years paid')
			elif usr.usertype not in ('committe', 'guest'):
				raise RBFatalError('Years paid must be given')
		
	def check_name(self, usr):
		"""Raise RBFatalError if name is not valid."""

		if not usr.cn:
			raise RBFatalError('Name must be given')

		if usr.cn.find(':') >= 0:
			raise RBFatalError("No colon ':' characters allowed in name")

	def check_email(self, usr):
	 	"""Raise RBError if email is not valid."""
		
		if not usr.altmail:
			raise RBFatalError('Email must be given')

		if not re.search(r'.+@.+', usr.altmail):
			raise RBFatalError("Invalid email address '%s'" % (usr.altmail))

		if usr.usertype in ('member', 'staff') and not re.search(r'.+@.*dcu\.ie', usr.altmail, re.I):
			self.rberror(RBWarningError("%s users should have a DCU email address" % (usr.usertype)))

	def check_updatedby(self, updatedby):
		"""Raise RBFatalError if updatedby is not a valid username."""

		if not updatedby:
			raise RBFatalError('Updated by must be given')
		try:
			self.check_user_byname(updatedby)
		except RBError:
			raise RBFatalError("Updated by username '%s' is not valid" % updatedby)
		
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

		if usr.yearsPaid != None and usr.yearsPaid > 0:
			self.rberror(RBWarningError("User '%s' is already paid!" % usr.uid))

	#---------------------------------------------------------------------#
	# SINGLE USER METHODS                                                 #
	#---------------------------------------------------------------------#

	def add(self, usr):
		"""Add new RBUser object to database."""

		# Note: it is safe to try all these functions without an
		# exception handler, as the functions will call rberror
		# internally for any RBWarningError exceptions that are raised.
		#
		self.check_userfree(usr)
		self.get_userinfo_new(usr)
		self.get_userdefaults_new(usr)
		self.check_userdata(usr)
		self.gen_accinfo(usr)

		# XXX: not sure if this is the right place for this?
		if not usr.objectClass:
			usr.objectClass = [usr.usertype] + rbconfig.ldap_default_objectClass

		self.wrapper(self.ldap.add_s, self.uid2dn(usr.uid), self.usr2ldap_add(usr))
	
	def delete(self, uid):
		"""Delete user from database."""

		self.check_user_byname(uid)
		self.ldap.delete_s(self.uid2dn(uid))

	def renew(self, usr):
		"""Renew and update RBUser object in database."""

		curusr = RBUser()

		self.get_userinfo_renew(usr, curusr)
		self.check_unpaid(curusr)
		self.get_userdefaults_renew(usr)
		self.check_userdata(usr)

		self.wrapper(self.ldap.modify_s, self.uid2dn(usr.uid), self.usr2ldap_renew(usr))

	def update(self, usr):
		"""Update RBUser object in database."""

		self.get_user_byname(usr)
		self.check_updatedby(usr.updatedby)
		self.check_userdata(usr)

		self.wrapper(self.ldap.modify_s, self.uid2dn(usr.uid), self.usr2ldap_update(usr))

	def rename(self, usr, newusr):
		"""Rename a user.
		
		Renamed additonal attributes (homeDirectory, updated,
		updatedby) are set in newusr.

		Requires: usr.uid, usr.updatedby, newusr.uid.

		"""

		self.get_user_byname(usr)
		self.check_userfree(newusr.uid)
		self.check_updatedby(usr.updatedby)

		# Rename DN first.
		#
		self.wrapper(self.ldap.rename_s, self.uid2dn(usr.uid), 'uid=%s' % newusr.uid)

		# Rename homedir and update the updated* attributes.
		#
		newusr.homeDirectory = rbconfig.gen_homedir(newusr.uid, usr.usertype)
		newusr.merge(usr)
		self.wrapper(self.ldap.modify_s, self.uid2dn(newusr.uid), self.usr2ldap_rename(newusr))

	def convert(self, usr, newusr):
		"""Convert a user to a different usertype."""

		self.get_user_byname(usr)
		self.check_usertype(newusr.usertype)
		self.check_updatedby(usr.updatedby)

		# If usertype is one of the pseudo usertypes, change the
		# usertype to 'committe' for the database conversion.
		#
		if rbconfig.convert_usertypes.has_key(newusr.usertype):
			newusr.usertype = 'committe'
			raise RBFatalError('NOT IMPLEMENTED YET')

		# Rename homedir, replace old usertype with new usertype in
		# objectClass and update gidNumber to new usertype.
		#
		newusr.homeDirectory = rbconfig.gen_homedir(usr.uid, newusr.usertype)
		newusr.gidNumber = self.get_gid_byname(newusr.usertype)
		newusr.objectClass = []
		for i in usr.objectClass:
			if i == usr.usertype:
				newusr.objectClass.append(newusr.usertype)
			else:
				newusr.objectClass.append(i)
		newusr.merge(usr)

		self.wrapper(self.ldap.modify_s, self.uid2dn(usr.uid), self.usr2ldap_convert(newusr))

	#---------------------------------------------------------------------#
	# SINGLE USER INFORMATION METHODS                                     #
	#---------------------------------------------------------------------#

	def show(self, usr):
		"""Show RBUser object information on standard output."""

		for i in usr.attr_list:
			if getattr(usr, i) != None:
				print "%13s: %s" % (i, getattr(usr, i))
	
	#---------------------------------------------------------------------#
	# BATCH INFORMATION METHODS                                           #
	#---------------------------------------------------------------------#

	def list_users(self):
		"""Return list of all usernames."""

		res = self.ldap.search_s(rbconfig.ldap_accounts_tree, ldap.SCOPE_ONELEVEL, 'objectClass=posixAccount', ('uid',))
		return [data['uid'][0] for dn, data in res]

	def list_renewed(self):
		"""Return list of all paid renewal (non-newbie) usernames."""

		raise RBFatalError("NOT IMLEMENTED YET")

		res = self.ldap.search_s(rbconfig.ldap_accounts_tree, ldap.SCOPE_ONELEVEL, '(&(yearsPaid>0)(newbie=FALSE))', ('uid',))
		return [data['uid'][0] for dn, data in res]

	def list_newbies(self):
		"""Return list of all paid newbie usernames."""

		raise RBFatalError("NOT IMLEMENTED YET")

		self.cur.execute("SELECT username FROM users WHERE years_paid > 0 AND newbie = 't'")
		return [i[0] for i in self.cur.fetchall()]

	def list_reserved_all(self):
		"""Return list of all usernames that are taken or reserved."""

		#XXX: doesn't return LDAP groups..
		res = self.ldap.search_s(rbconfig.ldap_tree, ldap.SCOPE_SUBTREE, '(|(objectClass=posixAccount)(objectClass=reserved))', ('uid',))
		return [data['uid'][0] for dn, data in res]

	def list_reserved_static(self):
		"""Return list of all static reserved names."""
		
		res = self.ldap.search_s(rbconfig.ldap_reserved_tree, ldap.SCOPE_ONELEVEL, '(&(objectClass=reserved)(flag=static))', ('uid',))
		return [data['uid'][0] for dn, data in res]
	
	def list_reserved_dynamic(self):
		"""Return list of all dynamic reserved names."""
		
		res = self.ldap.search_s(rbconfig.ldap_reserved_tree, ldap.SCOPE_ONELEVEL, '(&(objectClass=reserved)(!(flag=static)))', ('uid',))
		return [data['uid'][0] for dn, data in res]

	def list_unpaid(self):
		"""Return list of all non-renewed users."""
		
		raise RBFatalError("NOT IMLEMENTED YET")

		self.cur.execute('SELECT username FROM users WHERE years_paid <= 0')
		return [i[0] for i in self.cur.fetchall()]

	def list_unpaid_normal(self):
		"""Return list of all normal non-renewed users."""

		raise RBFatalError("NOT IMLEMENTED YET")

		self.cur.execute('SELECT username FROM users WHERE years_paid = 0')
		return [i[0] for i in self.cur.fetchall()]

	def list_unpaid_grace(self):
		"""Return list of all grace non-renewed users."""

		raise RBFatalError("NOT IMLEMENTED YET")

		self.cur.execute('SELECT username FROM users WHERE years_paid < 0')
		return [i[0] for i in self.cur.fetchall()]

	def search_users_byusername(self, uid):
		"""Search user database by username and return results
		((username, usertype, id, name, course, year, email), ...)"""

		raise RBFatalError("NOT IMLEMENTED YET")

		self.cur.execute('SELECT username, usertype, id, name, course, year, email FROM users WHERE username LIKE %s', ('%%%s%%' % uid,))
		return self.cur.fetchall()

	def search_users_byid(self, id):
		"""Search user database by id and return results
		((username, id, name, course, year), ...)"""

		raise RBFatalError("NOT IMLEMENTED YET")

		return self.search_users('id LIKE', id)

	def search_users_byname(self, name):
		"""Search user database by name and return results as per
		search_users_byid()."""

		raise RBFatalError("NOT IMLEMENTED YET")

		return self.search_users('name ILIKE', name)

	def search_users(self, where, var):
		"""Performs actual user database search with given where clause
		and data."""

		raise RBFatalError("NOT IMLEMENTED YET")

		self.cur.execute('SELECT username, usertype, id, name, course, year, email FROM users WHERE ' + where + ' %s', ('%%%s%%' % var,))
		return self.cur.fetchall()

	def search_dcu_byid(self, id):
		"""Search user & DCU databases by id and return results
		((username, id, name, course, year), ...)"""

		raise RBFatalError("NOT IMLEMENTED YET")

		return self.search_dcu('s.id LIKE', id)

	def search_dcu_byname(self, name):
		"""Search user & DCU databases by name and return results as
		per search_dcu_byid"""

		raise RBFatalError("NOT IMLEMENTED YET")

		return self.search_dcu('s.name ILIKE', name)

	def search_dcu(self, where, var):
		"""Performs actual DCU database search with given where clause
		and data."""

		raise RBFatalError("NOT IMLEMENTED YET")

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
		
		raise RBFatalError("NOT IMLEMENTED YET")

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

		raise RBFatalError("NOT IMLEMENTED YET")

		tmp = {}
		for i in rbconfig.usertypes_list:
			tmp[i] = 0

		self.cur.execute("SELECT usertype, count(*) FROM users GROUP BY usertype")
		for u, c in self.cur.fetchall():
			tmp[u] = c

		for i in rbconfig.usertypes_list:
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

	def crypt(self, password):
		"""Return crypted DES password."""

		saltchars = "./0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
		return crypt.crypt(password, saltchars[random.randrange(len(saltchars))] + saltchars[random.randrange(len(saltchars))])

	def uid2dn(self, uid):
		"""Return full Distinguished Name (DN) for given username."""

		return "uid=%s,%s" % (uid, rbconfig.ldap_accounts_tree)

	#--------------------------------------------------------------------#
	# INTERNAL METHODS                                                   #
	#--------------------------------------------------------------------#
	
	def usr2ldap_add(self, usr):
		"""Return a list of (type, attribute) pairs for given user.
		
		This list is used in LDAP add queries."""

		now = time.strftime('%Y-%m-%d %H:%M:%S%z')
		tmp = [
			('uid', usr.uid),
			('objectClass', usr.objectClass),
			('newbie', usr.newbie and 'TRUE' or 'FALSE'),
			('cn', usr.cn),
			('altmail', usr.altmail),
			('updatedby', usr.updatedby),
			('updated', now),
			('createdby', usr.updatedby),
			('created', now),
			('uidNumber', str(usr.uidNumber)),
			('gidNumber', str(usr.gidNumber)),
			('gecos', usr.gecos),
			('loginShell', usr.loginShell),
			('homeDirectory', usr.homeDirectory),
			('userPassword', usr.userPassword),
			('host', usr.host)
		]
		if usr.id != None:
			tmp.append(('id', str(usr.id)))
		if usr.course:
			tmp.append(('course', usr.course))
		if usr.year != None:
			tmp.append(('year', usr.year))
		if usr.yearsPaid != None:
			tmp.append(('yearsPaid', str(usr.yearsPaid)))
		if usr.birthday:
			tmp.append(('birthday', usr.birthday))

		return tmp

	def usr2ldap_renew(self, usr):
		"""Return a list of (type, attribute) pairs for given user.
		
		This list is used in LDAP modify queries for renewing."""

		now = time.strftime('%Y-%m-%d %H:%M:%S%z')
		tmp = [
			(ldap.MOD_REPLACE, 'newbie', usr.newbie and 'TRUE' or 'FALSE'),
			(ldap.MOD_REPLACE, 'cn', usr.cn),
			(ldap.MOD_REPLACE, 'altmail', usr.altmail),
			(ldap.MOD_REPLACE, 'updatedby', usr.updatedby),
			(ldap.MOD_REPLACE, 'updated', now),
		]
		if usr.id != None:
			tmp.append((ldap.MOD_REPLACE, 'id', str(usr.id)))
		if usr.course:
			tmp.append((ldap.MOD_REPLACE, 'course', usr.course))
		if usr.year != None:
			tmp.append((ldap.MOD_REPLACE, 'year', usr.year))
		if usr.yearsPaid != None:
			tmp.append((ldap.MOD_REPLACE, 'yearsPaid', str(usr.yearsPaid)))
		if usr.birthday:
			tmp.append((ldap.MOD_REPLACE, 'birthday', usr.birthday))

		return tmp

	def usr2ldap_update(self, usr):
		"""Return a list of (type, attribute) pairs for given user.
		
		This list is used in LDAP modify queries for updating."""

		tmp = [
			(ldap.MOD_REPLACE, 'newbie', usr.newbie and 'TRUE' or 'FALSE'),
			(ldap.MOD_REPLACE, 'cn', usr.cn),
			(ldap.MOD_REPLACE, 'altmail', usr.altmail),
			(ldap.MOD_REPLACE, 'updatedby', usr.updatedby),
			(ldap.MOD_REPLACE, 'updated', time.strftime('%Y-%m-%d %H:%M:%S%z')),
		]
		if usr.id != None:
			tmp.append((ldap.MOD_REPLACE, 'id', str(usr.id)))
		if usr.course:
			tmp.append((ldap.MOD_REPLACE, 'course', usr.course))
		if usr.year != None:
			tmp.append((ldap.MOD_REPLACE, 'year', usr.year))
		if usr.yearsPaid != None:
			tmp.append((ldap.MOD_REPLACE, 'yearsPaid', str(usr.yearsPaid)))
		if usr.birthday:
			tmp.append((ldap.MOD_REPLACE, 'birthday', usr.birthday))

		return tmp
	
	def usr2ldap_rename(self, usr):
		"""Return a list of (type, attribute) pairs for given user.
		
		This list is used in LDAP modify queries for renaming."""

		return (
			(ldap.MOD_REPLACE, 'gidNumber', str(usr.gidNumber)),
			(ldap.MOD_REPLACE, 'homeDirectory', usr.homeDirectory),
			(ldap.MOD_REPLACE, 'updatedby', usr.updatedby),
			(ldap.MOD_REPLACE, 'updated', time.strftime('%Y-%m-%d %H:%M:%S%z')),
		)

		return tmp
	
	def usr2ldap_convert(self, usr):
		"""Return a list of (type, attribute) pairs for given user.
		
		This list is used in LDAP modify queries for converting."""

		return (
			(ldap.MOD_REPLACE, 'objectClass', usr.objectClass),
			(ldap.MOD_REPLACE, 'gidNumber', str(usr.gidNumber)),
			(ldap.MOD_REPLACE, 'homeDirectory', usr.homeDirectory),
			(ldap.MOD_REPLACE, 'updatedby', usr.updatedby),
			(ldap.MOD_REPLACE, 'updated', time.strftime('%Y-%m-%d %H:%M:%S%z'))
		)
		
	def gen_accinfo(self, usr):
		if not usr.userPassword:
			if not usr.passwd and self.opt.setpasswd:
				usr.passwd = rbconfig.gen_passwd()
			if usr.passwd:
				usr.userPassword = "{CRYPT}" + self.crypt(usr.passwd)
			else:
				# XXX: is this correct way to disable password?
				usr.userPassword = "{CRYPT}*"
		if not usr.homeDirectory:
			usr.homeDirectory = rbconfig.gen_homedir(usr.uid, usr.usertype)
		if usr.uidNumber == None:
			# XXX: need way of auto-incrementing UIDs. For RRS,
			# we're just setting it to -1 and assigning them later
			# when the accounts are being created.
			#
			usr.uidNumber = -1
		if usr.gidNumber == None:
			usr.gidNumber = self.get_gid_byname(usr.usertype)
		if not usr.gecos:
			usr.gecos = usr.cn
		if not usr.loginShell:
			usr.loginShell = rbconfig.default_shell
		if not usr.host:
			usr.host = rbconfig.ldap_default_hosts

	def set_user(self, usr, res):
		"""Populate RBUser object with information from LDAP query.

		By default will only populate RBUser attributes that have no
		value (None).

		"""
		
		for i in res[1]['objectClass']:
			if rbconfig.usertypes.has_key(i):
				usr.usertype = i
				break
		else:
			raise RBFatalError("Unknown usertype for user '%s'" % usr.uid)

		for k, v in res[1].items():
			if getattr(usr, k) == None:
				if k not in RBUser.attr_list_value:
					setattr(usr, k, v[0])
				else:
					setattr(usr, k, v)

		# LDAP returns everything as strings, so booleans and integers
		# need to be converted:
		#
		usr.newbie = res[1]['newbie'][0] == 'TRUE'
		if usr.id:
			usr.id = int(usr.id)
		if usr.yearsPaid:
			usr.yearsPaid = int(usr.yearsPaid)
		usr.uidNumber = int(usr.uidNumber)
		usr.gidNumber = int(usr.gidNumber)

	def set_user_dcu(self, usr, res, override = 0):
		"""Populate RBUser object with common information from DCU LDAP query.
		
		By default will only populate RBUser attributes that have no
		value (None) unless override is enabled.
		
		"""
		
		# Construct their full name from first name ('givenName')
		# followed by their surname ('sn') or failing that, from their
		# gecos up to the comma.
		#	
		if override or usr.cn == None:
			if res[1].get('givenName') and res[1].get('sn'):
				usr.cn = '%s %s' % (res[1]['givenName'][0], res[1]['sn'][0])
			elif res[1].get('gecos'):
				usr.cn = res[1].get('gecos')[:res[1].get('gecos').find(',')]

		if override or usr.altmail == None:
			usr.altmail = res[1]['mail'][0]

	def set_user_dcu_student(self, usr, res, override = 0):
		"""Populate RBUser object with student information from DCU
		LDAP query."""

		# Extract course & year from 'l' attribute if set. Assumes last
		# character is the year (1, 2, 3, 4, X, O, C, etc.) and the
		# rest is the course name. Uppercase course & year for
		# consistency.
		#
		if res[1].get('l'):
			if override or usr.course == None:
				usr.course = res[1]['l'][0][:-1].upper()
			if override or usr.year == None:
				usr.year = res[1]['l'][0][-1].upper()

	def set_user_dcu_staff(self, usr, res, override = 0):
		"""Populate RBUser object with staff information from DCU
		LDAP query."""

		# Set course to department name from 'l' attribute if set.
		#
		if res[1].get('l'):
			if override or usr.course == None:
				usr.course = res[1]['l'][0]

	def set_user_dcu_alumni(self, usr, res, override = 0):
		"""Populate RBUser object with alumni information from DCU
		LDAP query."""

		# Extract course & year from 'l' attribute if set. Assumes
		# syntax of [a-zA-Z]+[0-9]+ i.e. course code followed by year
		# of graduation. Uppercase course for consistency.
		#
		if res[1].get('l'):
			tmp = res[1].get('l')[0]
			for i in range(len(tmp)):
				if tmp[i].isdigit():
					if override or usr.year == None:
						usr.year = tmp[i:]
					if override or usr.course == None:
						usr.course = tmp[:i].upper()
					break
			else:
				if override or usr.course == None:
					usr.course = tmp.upper()

	def wrapper(self, function, *keywords, **arguments):
		"""Wrapper method for executing other functions.
		
		If test mode is set, print function name and arguments.
		Otherwise call function with arguments.
		
		"""

		if self.opt.test:
			sys.stderr.write("TEST: %s(" % function.__name__)
			for i in keywords:
				sys.stderr.write("%s, " % (i,))
			for k, v in arguments.items():
				sys.stderr.write("%s = %s, " % (k, v))
			sys.stderr.write(")\n")
		else:
			return function(*keywords, **arguments)
		
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
		"""Handle RBError exceptions.
	
		If e is an RBWarningError and the override option is set,
		ignore the exception and return. Otherwise, raise the exception
		again.
		
		"""
		
		if self.opt.override and isinstance(e, RBWarningError):
			return

		# If we reach here it's either a FATAL error or there was no
		# override for a WARNING error, so raise it again to let the
		# caller handle it.
		#
		raise e
