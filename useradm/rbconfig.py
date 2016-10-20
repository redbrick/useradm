#-----------------------------------------------------------------------------#
# MODULE DESCRIPTION                                                          #
#-----------------------------------------------------------------------------#

"""RedBrick Configuration Module; contains local configuration information."""

# System modules

import os
import random

#---------------------------------------------------------------------#
# DATA                                                                #
#---------------------------------------------------------------------#

__version__ = '$Revision: 1.11 $'
__author__  = 'Cillian Sharkey'

# Find out where the rrs directory is.

dir_rrs = (os.path.dirname(__file__) or '.') + '/'

# Maximum length of usernames and groups.

maxlen_uname = 8
maxlen_group = 8

# Default LDAP account attribute values.

ldap_default_objectClass = ['posixAccount', 'top', 'shadowAccount']
ldap_default_hosts = ['paphos', 'metharme']

# RedBrick LDAP settings.

ldap_uri = 'ldap://ldap.internal'
ldap_root_dn = 'cn=root,ou=ldap,o=redbrick'
ldap_rootpw_file = '/etc/ldap.secret'
ldap_tree = 'o=redbrick'
ldap_accounts_tree = 'ou=accounts,o=redbrick'
ldap_group_tree = 'ou=groups,o=redbrick'
ldap_reserved_tree = 'ou=reserved,o=redbrick'

# DCU LDAP settings.

ldap_dcu_uri = 'ldap://ad.dcu.ie'
ldap_dcu_tree = 'o=ad,o=dcu,o=ie'
ldap_dcu_rbdn = 'CN=rblookup,OU=Service Accounts,DC=ad,DC=dcu,DC=ie'
ldap_dcu_rbpw = '/etc/dcu_ldap.secret'
ldap_dcu_students_tree = 'OU=Students,DC=ad,DC=dcu,DC=ie'
#'ou=students,dc=ad,dc=dcu,dc=ie'
ldap_dcu_staff_tree = 'OU=Staff,DC=ad,DC=dcu,DC=ie'
#'ou=staff,dc=ad,dc=dcu,dc=ie'
ldap_dcu_alumni_tree = 'OU=Alumni,DC=ad,DC=dcu,DC=ie'
#'ou=alumni,o=dcu'

# DNS zones RedBrick is authorative for.

dns_zones = (
	'redbrick.dcu.ie',
	'club.dcu.ie',
	'soc.dcu.ie',
)

# Mailman list suffixes.

mailman_list_suffixes = ("-admin", "-bounces", "-confirm", "-join", "-leave", "-owner", "-request", "-subscribe", "-unsubscribe")

# Directory pathnames.

dir_home = '/home'
dir_webtree = '/webtree'
dir_signaway_state = '/local/share/agreement/statedir'
dir_daft = '/local/share/daft'
dir_skel = '/etc/skel'
dir_mailman = '/var/lib/mailman'

# Filenames.

file_uidNumber = dir_rrs + 'uidNumber.txt'
file_pre_sync = dir_rrs + 'presync.txt'
file_rrslog = dir_rrs + 'rrs.log'
file_shells = '/etc/shells'
file_backup_passwd = '/var/backups/passwd.pre-expired'
shell_default = '/usr/local/shells/zsh'
shell_expired = '/usr/local/shells/expired'

# Unix group files: (group file, hostname) pairs.

files_group = (
	('/etc/group', 'Deathray'),
	('/local/share/var/carbon/group', 'Carbon')
)

# host files: (host file, hostname) pairs.

files_host = (
	('/etc/hosts', 'Deathray'),
	('/local/share/var/carbon/hosts', 'Carbon')
)

# Email alias files.

files_alias = (
	('/etc/mail/exim_aliases.txt', 'Mail alias'),
)

# Commands.

command_setquota = '/usr/sbin/setquota'
command_chown = '/bin/chown'
command_chgrp = '/bin/chgrp'
command_cp = '/bin/cp'
command_sendmail = '/usr/sbin/sendmail'

# Valid account usertypes and descriptions.
#
usertypes = {
	'founders':	'RedBrick founder',
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

# "Ordered" list of usertypes for listing with the exception of founders.
#
usertypes_list = (
	'member', 'associat', 'staff', 'committe',
	'society', 'club', 'dcu',
	'projects', 'redbrick', 'intersoc', 'guest'
)

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

# Supplementary groups when converting an account to given usertype.
#
# Format: 'usertype': 'a string of comma seperated groups with no spaces'
#
convert_extra_groups = {
	'admin':	'root,log',
	'webmaster':	'root,log,webgroup',
	'helpdesk':	'helpdesk'
}

# Actual primary group to use when converting an account to given usertype
# (typically a 'pseudo-usertype').
#
# Format: 'usertype': 'actual unix group name'
#
convert_primary_groups = {
	'admin':	'committe',
	'webmaster':	'committe',
	'helpdesk':	'committe'
}

#---------------------------------------------------------------------#
# MODULE FUNCTIONS                                                    #
#---------------------------------------------------------------------#

def gen_passwd():

def gen_homedir(username, usertype):
	"""Construct a user's home directory path given username and usertype."""
	
	if usertype in ('member', 'associat'):
		hash = username[0] + '/'
	else:
		hash = ''

	return '%s/%s/%s%s' % (dir_home, usertype, hash, username)

def gen_webtree(username):
	"""Generate a user's webtree path for given username."""

	return '%s/%s/%s' % (dir_webtree, username[0], username)

def gen_quotas(usertype = None):
	"""Returns a dictionary of quota limits for filesystems (possibly
	depending on the given usertype, if any).

	The format of the quota dictionary is as follows:

	'filesystem': (block quota soft, block quota hard,
	               inode quota soft, inode quota hard),
	 ...

	Block quota is in kilobytes, inode quota is number of inodes.
	
	"""

	return {
		'/storage': (1000000, 1100000, 800000, 1000000)
	}

def gen_extra_user_files(username):
	"""Return list of files that may belong to the given user outside of
	their main storage areas. For purposes of renaming or deleting."""

	# XXX: need files for carbon now aswell.

	return  (
		'%s/%s' % (dir_signaway_state, username),
		'/var/mail/%s' % username,
		'/var/spool/cron/crontabs/%s' % username
	)
