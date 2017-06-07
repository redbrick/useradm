#-----------------------------------------------------------------------------#
# MODULE DESCRIPTION                                                          #
#-----------------------------------------------------------------------------#

"""RedBrick Configuration Module; contains local configuration information."""

# System modules

import os
import random
import string

#---------------------------------------------------------------------#
# DATA                                                                #
#---------------------------------------------------------------------#

__version__ = '$Revision: 1.11 $'
__author__ = 'Cillian Sharkey'

# Find out where the rrs directory is.

DIR_RRS = (os.path.dirname(__file__) or '.') + os.sep

# Maximum length of usernames and groups.

MAXLEN_UNAME = 8
MAXLEN_GROUP = 8

# Default LDAP account attribute values.

LDAP_DEFAULT_OBJECTCLASS = ['posixAccount', 'top', 'shadowAccount']
LDAP_DEFAULT_HOSTS = ['paphos', 'metharme']

# RedBrick LDAP settings.

LDAP_URI = 'ldap://ldap.internal'
LDAP_ROOT_DN = 'cn=root,ou=ldap,o=redbrick'
LDAP_ROOTPW_FILE = '/etc/ldap.secret'
LDAP_TREE = 'o=redbrick'
LDAP_ACCOUNTS_TREE = 'ou=accounts,o=redbrick'
LDAP_GROUP_TREE = 'ou=groups,o=redbrick'
LDAP_RESERVED_TREE = 'ou=reserved,o=redbrick'

# DCU LDAP settings.

LDAP_DCU_URI = 'ldap://ad.dcu.ie'
LDAP_DCU_TREE = 'o=ad,o=dcu,o=ie'
LDAP_DCU_RBDN = 'CN=rblookup,OU=Service Accounts,DC=ad,DC=dcu,DC=ie'
LDAP_DCU_RBPW = '/etc/dcu_ldap.secret'
LDAP_DCU_STUDENTS_TREE = 'OU=Students,DC=ad,DC=dcu,DC=ie'
#'ou=students,dc=ad,dc=dcu,dc=ie'
LDAP_DCU_STAFF_TREE = 'OU=Staff,DC=ad,DC=dcu,DC=ie'
#'ou=staff,dc=ad,dc=dcu,dc=ie'
LDAP_DCU_ALUMNI_TREE = 'OU=Alumni,DC=ad,DC=dcu,DC=ie'
#'ou=alumni,o=dcu'

# DNS zones RedBrick is authorative for.

DCU_ZONES = (
    'redbrick.dcu.ie',
    'club.dcu.ie',
    'soc.dcu.ie',
)

# Mailman list suffixes.

MAILMAN_LIST_SUFFIXES = ("-admin", "-bounces", "-confirm", "-join", "-leave",
                         "-owner", "-request", "-subscribe", "-unsubscribe")

# Directory pathnames.

DIR_HOME = '/home'
DIR_WEBTREE = '/webtree'
DIR_SIGNAWAY_STATE = '/local/share/agreement/statedir'
DIR_DAFT = '/local/share/daft'
DIR_SKEL = '/etc/skel'
DIR_MAILMAN = '/var/lib/mailman'

# Filenames.

FILE_UIDNUMBER = DIR_RRS + 'uidNumber.txt'
FILE_PRE_SYNC = DIR_RRS + 'presync.txt'
FILE_RRSLOG = DIR_RRS + 'rrs.log'
FILE_SHELLS = '/etc/shells'
FILE_BACKUP_PASSWD = '/var/backups/passwd.pre-expired'
SHELL_DEFAULT = '/usr/local/shells/zsh'
SHELL_EXPIRED = '/usr/local/shells/expired'

# Unix group files: (group file, hostname) pairs.

FILES_GROUP = (
    ('/etc/group', 'Deathray'),
    ('/local/share/var/carbon/group', 'Carbon')
)

# host files: (host file, hostname) pairs.

FILES_HOST = (
    ('/etc/hosts', 'Deathray'),
    ('/local/share/var/carbon/hosts', 'Carbon')
)

# Email alias files.

FILES_ALIAS = (
    ('/etc/mail/exim_aliases.txt', 'Mail alias'),
)

# Commands.

COMMAND_SETQUOTA = '/usr/sbin/setquota'
COMMAND_CHOWN = '/bin/chown'
COMMAND_CHGRP = '/bin/chgrp'
COMMAND_CP = '/bin/cp'
COMMAND_SENDMAIL = '/usr/sbin/sendmail'

# Valid account USERTYPES and descriptions.
#
USERTYPES = {
    'founders': 'RedBrick founder',
    'member': 'Normal member',
    'associat': 'Graduate/associate member',
    'staff': 'DCU staff member',
    'society': 'DCU society',
    'club': 'DCU club',
    'projects': 'RedBrick/DCU/Course project account',
    'guest': 'Guest account',
    'intersoc': 'Account for society from another college',
    'committe': 'Committee member or a position account',
    'redbrick': 'RedBrick related account',
    'dcu': 'DCU related account'
}

# "Ordered" list of USERTYPES for listing with the exception of founders.
#
USERTYPES_LIST = (
    'member', 'associat', 'staff', 'committe',
    'society', 'club', 'dcu',
    'projects', 'redbrick', 'intersoc', 'guest'
)

# List of paying USERTYPES.
#
USERTYPES_PAYING = ('member', 'associat', 'staff', 'committe', 'guest')

# List of dcu USERTYPES (i.e. require a id number)
#
USERTYPES_DCU = ('member', 'associat', 'staff', 'committe')

# Pseudo USERTYPES for conversion to committee positions.
#
CONVERT_USERTYPES = {
    'admin': 'Elected admin',
    'webmaster': 'Elected webmaster',
    'helpdesk': 'Elected helpdesk'
}

# Supplementary groups when converting an account to given usertype.
#
# Format: 'usertype': 'a string of comma seperated groups with no spaces'
#
CONVERT_EXTRA_GROUPS = {
    'admin': 'root,log',
    'webmaster': 'root,log,webgroup',
    'helpdesk': 'helpdesk'
}

# Actual primary group to use when converting an account to given usertype
# (typically a 'pseudo-usertype').
#
# Format: 'usertype': 'actual unix group name'
#
CONVERT_PRIMARY_GROUPS = {
    'admin': 'committe',
    'webmaster': 'committe',
    'helpdesk': 'committe'
}

#---------------------------------------------------------------------#
# MODULE FUNCTIONS                                                    #
#---------------------------------------------------------------------#


def gen_passwd():
    """Create a random string and return it for the users password"""
    return ''.join(random.SystemRandom().choice(string.ascii_lowercase + string.digits)
                   for _ in range(12))


def gen_homedir(username, usertype):
    """Construct a user's home directory path given username and usertype."""

    if usertype in ('member', 'associat'):
        letter = username[0] + os.sep
    else:
        letter = ''

    return '%s/%s/%s%s' % (DIR_HOME, usertype, letter, username)


def gen_webtree(username):
    """Generate a user's webtree path for given username."""

    return os.path.join(DIR_WEBTREE, username[0], username)


def gen_quotas():
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

    # fixme: need files for carbon now aswell.

    return (
        '%s/%s' % (DIR_SIGNAWAY_STATE, username),
        '/var/mail/%s' % username,
        '/var/spool/cron/crontabs/%s' % username
    )
