#-----------------------------------------------------------------------------#
# MODULE DESCRIPTION                                                          #
#-----------------------------------------------------------------------------#

"""RedBrick Configuration Module; contains local configuration information."""

# System modules

import random

#---------------------------------------------------------------------#
# DATA                                                                #
#---------------------------------------------------------------------#

__version__ = '$Revision: 1.2 $'
__author__  = 'Cillian Sharkey'

# Maximum length of usernames and groups.

maxlen_uname = 8
maxlen_group = 8

# Default LDAP account attribute values.

ldap_default_objectClass = ['posixAccount', 'top', 'shadowAccount']
ldap_default_hosts = ['carbon', 'prodigy']

# RedBrick LDAP settings.

ldap_uri = 'ldap://ldap.internal'
ldap_root_dn = 'cn=root,ou=ldap,o=redbrick'
ldap_rootpw_file = '/etc/ldap.secret'
ldap_tree = 'o=redbrick'
ldap_accounts_tree = 'ou=accounts,o=redbrick'
ldap_group_tree = 'ou=groups,o=redbrick'
ldap_reserved_tree = 'ou=reserved,o=redbrick'

# DCU LDAP settings.

ldap_dcu_uri = 'ldap://nds.dcu.ie'
ldap_dcu_tree = 'o=dcu'
ldap_dcu_students_tree = 'ou=students,o=dcu'
ldap_dcu_staff_tree = 'ou=staff,o=dcu'
ldap_dcu_alumni_tree = 'ou=alumni,o=dcu'

# DNS zones RedBrick is authorative for.

dns_zones = (
	'redbrick.dcu.ie',
	'club.dcu.ie',
	'soc.dcu.ie',
)

# Mailman list suffixes.

mailman_list_suffixes = ("-admin", "-bounces", "-confirm", "-join", "-leave", "-owner", "-request", "-subscribe", "-unsubscribe")

# Directory pathnames.

home_dir = '/home'
webtree_dir = '/webtree'
signaway_state_dir = '/local/share/agreement/statedir'
daft_dir = '/local/share/daft'
skel_dir = '/etc/skel'
mailman_dir = '/local/mailman'

# Filenames.

shells_file = '/etc/shells'
backup_passwd_file = '/var/backups/passwd.pre-expired'
default_shell = '/usr/local/shells/zsh'
expired_shell = '/usr/local/shells/expired'

# Unix group files: (group file, hostname) pairs.

group_files = (
	('/etc/group', 'Prodigy'),
	('/local/share/var/deathray/group', 'Deathray')
)

# host files: (host file, hostname) pairs.

host_files = (
	('/etc/hosts', 'Prodigy'),
	('/local/share/var/deathray/hosts', 'Deathray')
)

# Email alias files.

alias_files = (
	('/etc/mail/exim_aliases.txt', 'Mail alias'),
)

# Extra files that may belong to a user outside of their main storage areas.
# '%s' will be replaced with username.

extra_user_files = (
	"%s/%%s" % signaway_state_dir,
	"/var/mail/%s",
	"/var/spool/cron/crontabs/%s"
)
			
# Commands.

setquota_command = '/usr/local/sbin/setquota'

# Valid account usertypes and descriptions.
#
usertypes = {
	'founder':	'RedBrick founder',
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
	"""Generate a random plaintext password.

	Alternates between vowels & consonants and decimal digits. We don't use
	upper case letters, solves the CAPS LOCK and clueless user problem.
	Characters and numbers that are similar in appearance (1, l, O, 0) or
	difficult to 'pronounce' (x, q) are not used.
	
	"""

	passchars = (
		'a e i o u'.split(),
		'b c d f g h j k m n p r s t v w y z'.split(),
	)
	numchars = '2 3 4 5 6 7 8 9'.split()
	password = ''
	offset = random.randrange(2)
	for c in range(6):
		password += passchars[(c + offset) % 2][random.randrange(len(passchars[(c + offset) % 2]))]
	offset = random.randrange(2) and 6 or 0
	password = password[offset:] + numchars[random.randrange(len(numchars))] + numchars[random.randrange(len(numchars))] + password[:offset]
	return password

def gen_homedir(username, usertype):
	"""Construct a user's home directory path given username and usertype."""
	
	if usertype in ('member', 'associat'):
		hash = username[0] + '/'
	else:
		hash = ''

	return '%s/%s/%s%s' % (home_dir, usertype, hash, username)

def gen_webtree(self, username):
	"""Generate a user's webtree path for given username."""

	return '%s/%s/%s' % (webtree_dir, username[0], username)

def quotas(usertype = None):
	"""Returns a dictionary of quota limits for filesystems (possibly
	depending on the given usertype, if any).

	The format of the quota dictionary is as follows:

	'filesystem': (block quota soft, block quota hard,
	               inode quota soft, inode quota hard),
	 ...

	Block quota is in kilobytes, inode quota is number of inodes.
	
	"""

	quotas = {}
	default_home_quota = (75000, 80000, 10000, 10500)

	# Clubs & Socs get a 100MB quota.
	#
	if usertype in ('club', 'society'):
		quotas['/home'] = (100000, 105000) + default_home_quota[2:]
	else:
		quotas['/home'] = default_home_quota

	return quotas
