# -*- coding: iso8859-15 -*-
# --------------------------------------------------------------------------- #
# MODULE DESCRIPTION                                                          #
# --------------------------------------------------------------------------- #
"""RedBrick command line user administration interface."""

# System modules

import atexit
import getopt
import os
import pprint
import re
import readline
import sys

import ldap
import rbconfig
from rbaccount import RBAccount
from rberror import RBError, RBFatalError, RBWarningError
from rbopt import RBOpt
from rbuser import RBUser
from rbuserdb import RBUserDB

# --------------------------------------------------------------------------- #
# DATA                                                                        #
# --------------------------------------------------------------------------- #

__version__ = '$Revision: 1.17 $'
__author__ = 'Cillian Sharkey'

# Command name -> (command description, optional arguments)
#
CMDS = {
    'add': ('Add new user', '[username]'),
    'renew': ('Renew user', '[username]'),
    'update': ('Update user', '[username]'),
    'altmail': ('Change Alternate Email', '[username]'),
    'activate': ('Re-Enable a club/soc account', '[username]'),
    'delete': ('Delete user', '[username]'),
    'resetpw': ('Set new random password and mail it to user', '[username]'),
    'setshell': ('Set user\'s shell', '[username [shell]]'),
    'resetsh': ('Reset user\'s shell', '[username]'),
    'rename': ('Rename user', '[username]'),
    'convert': ('Change user to a different usertype', '[username]'),
    'disuser': ('Disuser a user', '[username [new username]]'),
    'reuser': ('Re-user a user', '[username]'),
    'show': ('Show user details', '[username]'),
    'info': ('Show shorter user details', '[username]'),
    'freename': ('Check if a username is free', '[username]'),
    'search': ('Search user and dcu databases', '[username]'),
    'pre_sync': ('Dump LDAP tree for use by sync before new tree is loaded',
                 ''),
    'sync': ('Synchronise accounts with userdb (for RRS)',
             '[rrs-logfile [presync-file]]'),
    'sync_dcu_info': ('Interactive update of userdb using dcu database info',
                      ''),
    'list_users': ('List all usernames', ''),
    'list_unavailable': ('List all usernames that are unavailable', ''),
    'list_newbies': ('List all paid newbies', ''),
    'list_renewals': ('List all paid renewals (non-newbie)', ''),
    'list_unpaid': ('List all non-renewed users', ''),
    'list_unpaid_normal': ('List all normal non-renewed users', ''),
    'list_unpaid_reset':
    ('List all normal non-renewed users with reset shells', ''),
    'list_unpaid_grace': ('List all grace non-renewed users', ''),
    'newyear': ('Prepare database for start of new academic year', ''),
    'unpaid_warn': ('Warn (mail) all non-renewed users', ''),
    'unpaid_disable': ('Disable all normal non-renewed users', ''),
    'unpaid_delete': ('Delete all grace non-renewed users', ''),
    'checkdb': ('Check database for inconsistencies', ''),
    'stats': ('Show database and account statistics', ''),
    'create_uidNumber': ('Create uidNumber text file with next free uidNumber',
                         ''),
}

# Command groups
#
CMDS_SINGLE_USER = ('add', 'delete', 'renew', 'update', 'altmail', 'activate',
                    'rename', 'convert')
CMDS_SINGLE_ACCOUNT = ('resetpw', 'resetsh', 'disuser', 'reuser', 'setshell')
CMDS_SINGLE_USER_INFO = ('show', 'info', 'freename')
CMDS_INTERACTIVE_BATCH = ('search', 'sync', 'sync_dcu_info')
CMDS_BATCH = ('newyear', 'unpaid_warn', 'unpaid_disable', 'unpaid_delete')
CMDS_BATCH_INFO = ('pre_sync', 'list_users', 'list_unavailable',
                   'list_newbies', 'list_renewals', 'list_unpaid',
                   'list_unpaid_normal', 'list_unpaid_reset',
                   'list_unpaid_grace')
CMDS_MISC = ('checkdb', 'stats', 'create_uidNumber')

# Command group descriptions
#
CMDS_GROUP_DESC = ((CMDS_SINGLE_USER,
                    'Single user commands'), (CMDS_SINGLE_ACCOUNT,
                                              'Single account commands'),
                   (CMDS_SINGLE_USER_INFO, 'Single user information commands'),
                   (CMDS_INTERACTIVE_BATCH,
                    'Interactive batch commands'), (CMDS_BATCH,
                                                    'Batch commands'),
                   (CMDS_BATCH_INFO,
                    'Batch information commands'), (CMDS_MISC,
                                                    'Miscellaneous commands'))

# All commands
#
CMDS_ALL = list(CMDS.keys())

# Command option -> (optional argument, option description,
#                    commands that use option)
#
CMDS_OPTS = (('h', '', 'Display this usage',
              CMDS_ALL), ('T', '', 'Test mode, show what would be done',
                          CMDS_ALL), ('d', '',
                                      'Perform database operations only',
                                      CMDS_SINGLE_USER),
             ('a', '', 'Perform unix account operations only',
              CMDS_SINGLE_USER), ('u', 'username',
                                  'Unix username of who updated this user',
                                  CMDS_SINGLE_USER + ('disuser', 'reuser')),
             ('f', '', 'Set newbie (fresher) to true',
              ('add', 'update')), ('F', '', 'Opposite of -f', ('add',
                                                               'update')),
             ('m', '',
              'Send account details to user\'s alternate email address',
              ('add', 'renew', 'rename',
               'resetpw')), ('M', '', 'Opposite of -m', ('add', 'renew',
                                                         'rename', 'resetpw')),
             ('o', '', 'Override warning errors',
              CMDS_ALL), ('p', '', 'Set new random password',
                          ('add', 'renew')), ('P', '', 'Opposite of -p',
                                              ('add', 'renew')),
             ('t', 'usertype', 'Type of account',
              ('add', 'renew', 'update',
               'convert')), ('n', 'name', 'Real name or account description',
                             ('add', 'renew', 'update',
                              'search')), ('e', 'email',
                                           'Alternative email address',
                                           ('add', 'renew', 'update')),
             ('i', 'id', 'Student/Staff ID',
              ('add', 'renew', 'update',
               'search')), ('c', 'course', 'DCU course (abbreviation)',
                            ('add', 'renew',
                             'update')), ('y', 'year', 'DCU year',
                                          ('add', 'renew', 'update')),
             ('s', 'years', 'paid Number of years paid (subscription)',
              ('add', 'renew',
               'update')), ('b', 'birthday', 'Birthday (format YYYY-MM-DD)',
                            ('add', 'renew',
                             'update')), ('q', '', 'Quiet mode', ('reuser', )))

INPUT_INSTRUCTIONS = '\033[1mRETURN\033[0m: use [default] given \
                      \033[1mTAB\033[0m: answer completion \
                      \033[1mEOF\033[0m: give empty answer\n'

# Global variables.
#
OPT = RBOpt()
UDB = ACC = None  # Initialised later in main()
HEADER_MSG = None

# --------------------------------------------------------------------------- #
# MAIN                                                                        #
# --------------------------------------------------------------------------- #


def main():
    """Program entry function."""

    atexit.register(shutdown)

    if len(sys.argv) > 1 and sys.argv[1][0] != '-':
        OPT.mode = sys.argv.pop(1)

    try:
        opts, args = getopt.getopt(sys.argv[1:],
                                   'b:c:e:i:n:s:t:u:y:adfFhmMopPqT')
    except getopt.GetoptError as err:
        print(err)
        usage()
        sys.exit(1)

    # fixme, Should be fixed with a dictionary

    for option, arg in opts:
        if option == '-h':
            OPT.help = 1
            usage()
            sys.exit(0)
        elif option == '-T':
            OPT.test = 1
        elif option == '-d':
            OPT.dbonly = 1
            OPT.aconly = 0
        elif option == '-a':
            OPT.aconly = 1
            OPT.dbonly = 0
        elif option == '-u':
            OPT.updatedby = arg
        elif option == '-f':
            OPT.newbie = 1
        elif option == '-F':
            OPT.newbie = 0
        elif option == '-m':
            OPT.mailuser = 1
        elif option == '-M':
            OPT.mailuser = 0
        elif option == '-o':
            OPT.override = 1
        elif option == '-p':
            OPT.setpasswd = 1
        elif option == '-P':
            OPT.setpasswd = 0
        elif option == '-t':
            OPT.usertype = arg
        elif option == '-n':
            OPT.cn = arg
        elif option == '-e':
            OPT.altmail = arg
        elif option == '-i':
            OPT.id = arg
        elif option == '-c':
            OPT.course = arg
        elif option == '-y':
            OPT.year = arg
        elif option == '-s':
            OPT.yearsPaid = arg
        elif option == '-b':
            OPT.birthday = arg
        elif option == '-q':
            OPT.quiet = 1

    if OPT.mode not in CMDS:
        usage()
        sys.exit(1)

    global UDB, ACC
    UDB = RBUserDB()

    try:
        UDB.connect()
    except ldap.LDAPError as err:
        error(err, 'Could not connect to user database')
        # not reached
    except KeyboardInterrupt:
        print()
        sys.exit(1)
        # not reached

    ACC = RBAccount()

    # Optional additional parameters after command line options.
    OPT.args = args

    try:
        # Call function for specific mode.
        eval(OPT.mode + "()")
    except KeyboardInterrupt:
        print()
        sys.exit(1)
        # not reached
    except RBError as err:
        rberror(err)
        # not reached
    except ldap.LDAPError as err:
        error(err)
        # not reached

    sys.exit(0)


def shutdown():
    """Cleanup function registered with atexit."""

    if UDB:
        UDB.close()


def usage():
    """Print command line usage and options."""

    if OPT.mode and OPT.mode not in CMDS:
        print(("Unknown command '%s'" % OPT.mode))
        OPT.mode = None

    if not OPT.mode:
        print("Usage: useradm command [options]")
        if OPT.help:
            for grp in CMDS_GROUP_DESC:
                print(("[1m%s:[0m" % (grp[1])))
                for cmd in grp[0]:
                    print(("  %-20s %s" % (cmd, CMDS[cmd][0])))
            print("""
            'useradm command -h' for more info on a command's options & usage.
            """)
        else:
            print("'useradm -h' for more info on available commands")
    else:
        print((CMDS[OPT.mode][0]))
        print(("Usage: useradm", OPT.mode, "[options]", CMDS[OPT.mode][1]))
        for i in CMDS_OPTS:
            if OPT.mode in i[3]:
                print((" -%s %-15s%s" % (i[0], i[1], i[2])))


# =========================================================================== #
# MAIN FUNCTIONS                                                              #
# =========================================================================== #

# --------------------------------------------------------------------------- #
# SINGLE USER COMMANDS                                                        #
# --------------------------------------------------------------------------- #


def add():
    """Add a new user."""

    usr = RBUser()
    get_usertype(usr)
    get_freeusername(usr)
    oldusertype = usr.usertype

    while 1:
        try:
            get_id(usr)
            UDB.get_userinfo_new(usr, override=1)
        except RBError as err:
            if not rberror(err, OPT.id is None):
                break
            usr.id = None
        else:
            break

    UDB.get_userdefaults_new(usr)

    # If we get info from the DCU databases, show the user details and any
    # differences to previous data (in this case it's just the initial
    # usertype entered at first) and offer to edit these with a default of
    # no so we can hit return and quickly add a user without verifying each
    # attribute.
    #
    if usr.cn:
        UDB.show(usr)
        print()
        if oldusertype != usr.usertype:
            print(
                'NOTICE: Given usertype is different to one determined by DCU\
                database!')
            print()
        edit_details = yesno(
            'Details of user to be added are shown above. Edit user details?',
            0)
    else:
        edit_details = 1

    if edit_details:
        get_usertype(usr)
        get_newbie(usr)
        get_name(usr)
        get_email(usr)
        get_course(usr)
        get_year(usr)
        get_years_paid(usr)
        get_birthday(usr)

    get_createaccount(usr)
    get_setpasswd(usr)
    get_mailuser(usr)
    get_updatedby(usr)

    # End of user interaction, set options for override & test mode.
    #
    UDB.setopt(OPT)
    ACC.setopt(OPT)

    if OPT.setpasswd:
        usr.passwd = rbconfig.gen_passwd()

    if not OPT.aconly:
        print(("User added: %s %s (%s)" % (usr.usertype, usr.uid, usr.cn)))
        UDB.add(usr)

    if not OPT.dbonly:
        print(("Account created: %s %s password: %s" % (usr.usertype, usr.uid,
                                                        usr.passwd)))
        ACC.add(usr)
    else:
        # If not creating a Unix account but setting a new password is
        # required, do that now.
        #
        if OPT.setpasswd:
            print(("Account password set for %s password: %s" % (usr.uid,
                                                                 usr.passwd)))
            # ACC.setpasswd(usr.uid, usr.passwd)

    if OPT.mailuser:
        print(("User mailed:", usr.altmail))
        mailuser(usr)


def delete():
    """Delete user."""

    usr = RBUser()
    get_username(usr)
    UDB.get_user_byname(usr)

    # End of user interaction, set options for override & test mode.
    UDB.setopt(OPT)
    ACC.setopt(OPT)

    if not OPT.aconly:
        print(('User deleted:', usr.uid))
        UDB.delete(usr)
    if not OPT.dbonly:
        print(('Account deleted:', usr.uid))
        ACC.delete(usr)


def renew():
    """Renew user."""

    usr = RBUser()
    curusr = RBUser()
    get_username(usr)

    try:
        UDB.get_userinfo_renew(usr, curusr, override=1)
    except RBError as err:
        if rberror(err, OPT.uid is None):
            return

    try:
        UDB.check_unpaid(curusr)
    except RBError as err:
        if rberror(err, OPT.uid is None):
            return

    UDB.get_userdefaults_renew(usr)

    UDB.show_diff(usr, curusr)
    print()
    if curusr.usertype != usr.usertype:
        print('NOTICE: A new usertype was determined by DCU database!\n')
    edit_details = yesno('''
        New details of user to be renewed are shown above with any differences
        \nfrom current values. Edit user details?
    ''', 0)

    if edit_details:
        while 1:
            get_id(usr)

            try:
                # If id was changed, need to get updated user info.
                #
                UDB.get_userinfo_renew(usr, override=1)
                # fixme: check id not already in use
            except RBError as err:
                if not rberror(err, OPT.id is None):
                    break
            else:
                break

        if curusr.id != usr.id:
            UDB.show_diff(usr, curusr)
            print()

        get_usertype(usr)
        get_newbie(usr)
        get_name(usr, (curusr.cn, ))
        get_email(usr, (curusr.altmail, ))
        get_course(usr, (curusr.course, ))
        get_year(usr, (curusr.year, ))
        get_years_paid(usr)
        get_birthday(usr)

    get_setpasswd(usr)
    get_mailuser(usr)
    get_updatedby(usr)

    # End of user interaction, set options for override & test mode.
    UDB.setopt(OPT)
    ACC.setopt(OPT)

    if not OPT.aconly:
        print(('User renewed:', usr.uid))
        UDB.renew(usr)

    if OPT.setpasswd:
        usr.passwd = rbconfig.gen_passwd()
        print(("Account password reset: %s password: %s" % (usr.uid,
                                                            usr.passwd)))
        UDB.set_passwd(usr)

    if curusr.usertype != usr.usertype:
        if not OPT.aconly:
            print(('User converted: %s -> %s' % (usr.uid, usr.usertype)))
            UDB.convert(curusr, usr)
        if not OPT.dbonly:
            print(('Account converted: %s -> %s' % (usr.uid, usr.usertype)))
            ACC.convert(curusr, usr)

    if UDB.reset_shell(usr):
        print(('Account shell reset for', usr.uid, '(%s)' % usr.loginShell))

    if OPT.mailuser:
        print(("User mailed:", usr.altmail))
        mailuser(usr)


def update():
    """Update user."""

    # Update mode only works on database.
    OPT.dbonly = 1
    OPT.aconly = 0

    usr = RBUser()
    get_username(usr)
    UDB.get_user_byname(usr)
    get_newbie(usr)
    defid = usr.id

    while 1:
        try:
            get_id(usr)
            newusr = RBUser(id=usr.id)
            if usr.id is not None:
                UDB.get_dcu_byid(newusr)
        except RBError as err:
            if not rberror(err, OPT.id is None):
                break
            usr.id = defid
        else:
            break

    get_name(usr, (newusr.cn, ))
    get_email(usr, (newusr.altmail, ))
    get_course(usr, (newusr.course, ))
    get_year(usr, (newusr.year, ))
    get_years_paid(usr)
    get_birthday(usr)
    get_updatedby(usr)

    # End of user interaction, set options for override & test mode.
    UDB.setopt(OPT)

    print(("User updated:", usr.uid))
    UDB.update(usr)


def altmail():
    """Update user."""

    # Update mode only works on database.
    OPT.dbonly = 1
    OPT.aconly = 0

    usr = RBUser()
    get_username(usr)
    UDB.get_user_byname(usr)
    #       get_newbie(usr)
    defid = usr.id

    while 1:
        try:
            get_id(usr)
            newusr = RBUser(id=usr.id)
            if usr.id is not None:
                UDB.get_dcu_byid(newusr)
        except RBError as err:
            if not rberror(err, OPT.id is None):
                break
            usr.id = defid
        else:
            break

    get_email(usr, (newusr.altmail, ))
    get_updatedby(usr)

    # End of user interaction, set options for override & test mode.
    UDB.setopt(OPT)

    print(("User updated:", usr.uid))
    UDB.update(usr)


def activate():
    """Update user."""

    # Update mode only works on database.
    #       OPT.dbonly = 1
    #       OPT.aconly = 0

    print(" ")
    print("To confirm society committee details check:")
    print(
        "https://www.dcu.ie/portal/index.php3?club_soc_registration_function=8"
    )
    print("Continuing will mail a new password for this account,")
    print("and set the shell to /usr/local/shells/zsh")
    print(" ")

    usr = RBUser()
    get_username(usr)
    UDB.get_user_byname(usr)

    #       if we're activating them they're hardly newbies
    #       get_newbie(usr)
    defid = usr.id

    while 1:
        try:
            get_id(usr)
            newusr = RBUser(id=usr.id)
            if usr.id is not None:
                UDB.get_dcu_byid(newusr)
        except RBError as err:
            if not rberror(err, OPT.id is None):
                break
            usr.id = defid
        else:
            break

    get_email(usr, (newusr.altmail, ))

    # everyone likes zsh
    #        get_shell(usr)
    usr.loginShell = "/usr/local/shells/zsh"

    # Don't bother asking, assume we want to do it
    #       get_setpasswd(usr)

    # Again, we always want to do this.
    #       get_mailuser(usr)

    get_updatedby(usr)

    usr.passwd = rbconfig.gen_passwd()
    print(("Account password reset: %s password: %s" % (usr.uid, usr.passwd)))
    UDB.set_passwd(usr)

    print(("User mailed:", usr.altmail))
    mailuser(usr)

    # End of user interaction, set options for override & test mode.
    UDB.setopt(OPT)
    ACC.setopt(OPT)

    UDB.update(usr)
    print(('Account email & shell set for', usr.uid, '(%s)' % usr.loginShell))
    UDB.set_shell(usr)


def rename():
    """Rename user."""

    usr = RBUser()
    newusr = RBUser()
    get_username(usr)
    get_freeusername(newusr)
    get_updatedby(usr)

    # End of user interaction, set options for override & test mode.
    UDB.setopt(OPT)
    ACC.setopt(OPT)

    print(('User renamed: %s -> %s' % (usr.uid, newusr.uid)))
    UDB.rename(usr, newusr)
    print(('Account renamed: %s -> %s' % (usr.uid, newusr.uid)))
    ACC.rename(usr, newusr)


def convert():
    """Convert user."""

    usr = RBUser()
    newusr = RBUser()
    get_username(usr)
    get_convert_usertype(newusr)
    get_updatedby(usr)

    # End of user interaction, set options for override & test mode.
    UDB.setopt(OPT)
    ACC.setopt(OPT)

    if not OPT.aconly:
        print('User converted: %s -> %s' % (usr.uid, newusr.usertype))
        UDB.convert(usr, newusr)
    if not OPT.dbonly:
        print('Account converted: %s -> %s' % (usr.uid, newusr.usertype))
        ACC.convert(usr, newusr)


# --------------------------------------------------------------------------- #
# SINGLE ACCOUNT COMMANDS                                                     #
# --------------------------------------------------------------------------- #


def resetpw():
    """Set new random password and mail it to user."""

    usr = RBUser()
    get_username(usr)
    UDB.get_user_byname(usr)
    usr.passwd = rbconfig.gen_passwd()

    check_paid(usr)

    get_mailuser(usr)

    # End of user interaction, set options for override & test mode.
    UDB.setopt(OPT)

    # print "Account password reset: %s password: %s" % (usr.uid, usr.passwd)
    print("Account password reset: %s " % (usr.uid))
    UDB.set_passwd(usr)

    if OPT.mailuser:
        print("User mailed:", usr.altmail)
        mailuser(usr)


def resetsh():
    """Reset user's shell."""

    usr = RBUser()
    get_username(usr)
    UDB.get_user_byname(usr)

    check_paid(usr)

    # End of user interaction, set options for override & test mode.
    UDB.setopt(OPT)
    ACC.setopt(OPT)

    if UDB.reset_shell(usr):
        print('Account shell reset for', usr.uid, '(%s)' % usr.loginShell)
    else:
        print('Account', usr.uid,
              'already had valid shell, no action performed.')


def disuser():
    """Disuser a user."""

    raise RBFatalError("NOT IMPLEMENTED YET")

    usr = RBUser()
    get_username(usr)
    get_disuser_period(usr)
    get_disuser_message(usr)
    get_updatedby(usr)

    # End of user interaction, set options for override & test mode.
    UDB.setopt(OPT)
    ACC.setopt(OPT)

    ACC.disuser(usr.uid, usr.disuser_period)


def reuser():
    """Re-user a user."""

    raise RBFatalError("NOT IMPLEMENTED YET")

    usr = RBUser()
    get_username(usr)
    get_updatedby(usr)

    # End of user interaction, set options for override & test mode.
    UDB.setopt(OPT)
    ACC.setopt(OPT)


def setshell():
    """Set user's shell."""

    usr = RBUser()
    get_username(usr)
    UDB.get_user_byname(usr)

    check_paid(usr)

    get_shell(usr)

    # End of user interaction, set options for override & test mode.
    UDB.setopt(OPT)
    ACC.setopt(OPT)

    print('Account shell set for', usr.uid, '(%s)' % usr.loginShell)
    UDB.set_shell(usr)


# --------------------------------------------------------------------------- #
# SINGLE USER INFORMATION COMMANDS                                            #
# --------------------------------------------------------------------------- #


def show():
    """Show user's database and account details."""

    usr = RBUser()
    get_username(usr, check_user_exists=0)

    # End of user interaction, set options for override & test mode.
    UDB.setopt(OPT)

    UDB.get_user_byname(usr)
    print(header('User Information'))
    UDB.show(usr)
    print(header('Account Information'))
    ACC.show(usr)


def info():
    """Show user's database and account details."""

    usr = RBUser()
    get_username(usr, check_user_exists=0)
    # End of user interaction, set options for override & test mode.
    UDB.setopt(OPT)
    UDB.get_user_byname(usr)
    print(header('User Information'))
    UDB.info(usr)


def freename():
    """Check if a username is free."""

    usr = RBUser()
    if get_freeusername(usr):
        print("Username '%s' is free." % (usr.uid))


# --------------------------------------------------------------------------- #
# BATCH INTERACTIVE COMMANDS                                                  #
# --------------------------------------------------------------------------- #


def search():
    """Search user and/or DCU databases."""

    raise RBFatalError("NOT IMPLEMENTED YET")

    pager = os.environ.get('PAGER', 'more')

    username = None
    if OPT.args:
        username = OPT.args.pop(0)
    if not username and not OPT.id and not OPT.cn:
        username = ask('Enter username to search user database', optional=1)
        if not username:
            OPT.id = ask(
                'Enter DCU Id number to search user and DCU databases',
                optional=1)
            if not OPT.id:
                OPT.cn = ask(
                    'Enter name to search user and DCU databases', optional=1)

    if username:
        res = UDB.search_users_byusername(username)
        file_pager = os.popen(pager, 'w')
        file_pager.write(
            "User database search for username '%s' - %d match%s\n" %
            (username, len(res), "es" if len(res) > 1 else ''))
        show_search_results(res, file_pager)
        file_pager.close()
    elif OPT.id or OPT.cn:
        file_pager = os.popen(pager, 'w')
        if OPT.id:
            res = UDB.search_users_byid(OPT.id)
            file_pager.write(
                "User database search for id '%s' - %d match%s\n" %
                (OPT.id, len(res), len(res) != 1 and 'es' or ''))
        else:
            res = UDB.search_users_byname(OPT.cn)
            file_pager.write(
                "User database search for name '%s' - %d match%s\n" %
                (OPT.cn, len(res), len(res) != 1 and 'es' or ''))
        show_search_results(res, file_pager)
        file_pager.write('\n')
        if OPT.id:
            res = UDB.search_dcu_byid(OPT.id)
            file_pager.write("DCU database search for id '%s' - %d match%s\n" %
                             (OPT.id, len(res), len(res) != 1 and 'es' or ''))
        else:
            res = UDB.search_dcu_byname(OPT.cn)
            file_pager.write(
                "DCU database search for name '%s' - %d match%s\n" %
                (OPT.cn, len(res), len(res) != 1 and 'es' or ''))
        show_search_results(res, file_pager)
        file_pager.close()
    else:
        raise RBFatalError('No search term given!')


def show_search_results(res, file_pager):
    """Actual routine to display search results on given output steam."""

    if res:
        file_pager.write('%-*s %-*s %-8s %-30s %-6s %-4s %s' %
                         (rbconfig.maxlen_uname, 'username',
                          rbconfig.maxlen_group, 'usertype', 'id', 'name',
                          'course', 'year', 'email'), )
        file_pager.write('%s %s %s %s %s %s %s' %
                         ('-' * rbconfig.maxlen_uname,
                          '-' * rbconfig.maxlen_group, '-' * 8, '-' * 30,
                          '-' * 6, '-' * 4, '-' * 30), )
        for username, usertype, uid, name, course, year, email in res:
            file_pager.write("%-*s %-*s %-8s %-30.30s %-6.6s %-4.4s %s" %
                             (rbconfig.maxlen_uname, username or '-',
                              rbconfig.maxlen_group, usertype or '-',
                              uid is not None and id or '-', name,
                              course or '-', year or '-', email), )


def pre_sync():
    """Dump current LDAP information to a file for use by sync().

    This step is performed before the new LDAP accounts tree is loaded so
    that a bare minimum copy of the old tree is available."""

    get_pre_sync()

    print('Dumping...')

    file_presync = open(OPT.presync, 'w')
    file_presync.write('global old_ldap\nold_ldap = ', end=' ')
    pprint.pprint(UDB.list_pre_sync(), file_presync)
    file_presync.close()


def sync():
    """Synchronise accounts (i.e. no changes are made to userdb) after an
    offline update to user database with RRS. Needs rrs.log to process
    renames and password resets for existing accounts.

    Procedure:

    1. Process all renames, only applicable to existing accounts. Taken from
    rrs.log. Keep a mapping of username renewals. Note there may be
    multiple rename entries.

    2. Process all conversions, only applicable to existing accounts.
    Detected by comparing Unix group and usertype in database.

    3. Process all deletions, only applicable to existing accounts.
    Detected by checking for unix accounts missing a database entry. All
    accounts should be renamed all ready so the only accounts left with
    missing database entries must have been deleted. Confirmation is
    required for each deletion, however.

    4. Process all adds, only applicable to new users. Detected by user
    database entry being a newbie, paid and having no unix account.
    Password is generated on-the-fly and mailed.

    5. Process all renewals, only applicable to existing users. Detected by
    user database entry being a non-newbie, paid and having an existing
    unix account. Reset account shell if needed. Password is reset
    on-the-fly and mailed if flagged in rrs.log. The flag in the logfile
    will be marked on the original username so the rename map is used to
    map this to the current username.

    """

    get_rrslog()
    get_pre_sync()

    # Load in old_ldap dictionary.
    #
    old_ldap = exec(compile(open(OPT.presync).read(), OPT.presync, 'exec'))

    # fixme: Set override by default ?
    # Set options for override & test mode.
    UDB.setopt(OPT)
    ACC.setopt(OPT)

    # Build user_rename maps.

    user_convert = {}
    user_rename = {}
    user_rename_reverse = {}
    # user_rename_stages = {}
    reset_password = {}

    # Open log file to build map of renamed usernames, usernames flagged
    # for a new password and usernames that were converted.
    #
    rss_file = open(OPT.rrslog, 'r')
    for line in rss_file.readlines():
        tlog = line.rstrip().split(':')

        # We ignore renames of new accounts as we just go by the final
        # entry in the database.
        #
        if tlog[4] == 'rename-existing':
            olduid = tlog[5]
            newuid = tlog[6]

            # Remove old user rename mapping and add new one unless
            # it points back to the original username.
            #
            user_rename_reverse[newuid] = user_rename_reverse.pop(
                olduid, olduid)
            if user_rename_reverse[newuid] == newuid:
                user_rename_reverse.pop(newuid)

            # If this user was flagged for new password and/or a
            # conversion, remove the old user mapping and add the
            # new one.
            #
            if olduid in user_convert:
                user_convert[tlog[6]] = user_convert.pop(tlog[5])
            if tlog[5] in reset_password:
                reset_password[tlog[6]] = reset_password.pop(tlog[5])
        elif tlog[4] == 'convert':
            # User was converted, so we flag it. Don't care what
            # they're converted to, we check that later.
            #
            user_convert[tlog[5]] = 1
        elif tlog[4] == 'renew':
            # tlog[7] indicates whether a new password is required
            # or not. We take the last value of this in the log
            # file as the final decision.
            #
            reset_password[tlog[5]] = int(tlog[7])
    rss_file.close()

    # Now build olduid -> newuid map from the reverse one.
    #
    for newuid, olduid in list(user_rename_reverse.items()):
        user_rename[olduid] = newuid

    if OPT.test:
        print('rrs.log username maps')
        print()
        print('RENAME')
        print()
        for key, value in list(user_rename.items()):
            print(key, '->', value)
        print()
        print('CONVERT')
        print()
        for key in list(user_convert.keys()):
            print(key)
        print()
        print('RESETPW')
        print()
        for key, value in list(reset_password.items()):
            if value:
                print(key)
        print()

    # ----------- #
    # sync_rename #
    # ----------- #

    print('===> start sync_rename')
    pause()

    for olduid, newuid in list(user_rename.items()):
        oldusr = RBUser(
            uid=olduid, homeDirectory=old_ldap[olduid]['homeDirectory'])
        newusr = RBUser(uid=newuid)
        UDB.get_user_byname(newusr)
        try:
            ACC.check_account_byname(oldusr)
        except RBFatalError:
            # Old account doesn't exist, must be renamed already.
            if OPT.test:
                print('SKIPPED: account rename: %s -> %s' % (olduid, newuid))
        else:
            print('Account renamed: %s -> %s' % (olduid, newuid))
            ACC.rename(oldusr, newusr)
            # pause()

    # ------------ #
    # sync_convert #
    # ------------ #

    print('\n===> start sync_convert')
    pause()

    for newuid in list(user_convert.keys()):
        olduid = user_rename_reverse.get(newuid, newuid)
        if olduid not in old_ldap:
            print('WARNING: Existing non newbie user', newuid,
                  'not in previous copy of ldap tree!')
            continue

        oldusr = RBUser(
            uid=olduid,
            homeDirectory=old_ldap[olduid]['homeDirectory'],
            usertype=old_ldap[olduid]['usertype'])
        newusr = RBUser(uid=newuid)
        UDB.get_user_byname(newusr)

        # If old and new usertypes are the same, they were temporarily
        # or accidentally converted to a different usertype then
        # converted back.
        #
        if oldusr.usertype == newusr.usertype:
            continue

        try:
            ACC.check_account_byname(oldusr)
        except RBFatalError:
            # Old account doesn't exist, must be converted already.
            if OPT.test:
                print('SKIPPED: account convert: %s: %s -> %s' %
                      (oldusr.uid, oldusr.usertype, newusr.usertype))
        else:
            print('Account converted: %s: %s -> %s' %
                  (oldusr.uid, oldusr.usertype, newusr.usertype))
            ACC.convert(oldusr, newusr)
            # pause()

    # ----------- #
    # sync_delete #
    # ----------- #

    # print '\n===> start sync_delete'
    # pause()

    # for pw in pwd.getpwall():
    #       try:
    #               UDB.check_user_byname(pw[0])
    #       except RBError:
    #               # User doesn't exist in database, ask to delete it.
    #               #
    #               if yesno("Delete account %s" % pw[0]):
    #                       print 'Account deleted: %s' % pw[0]
    #                       ACC.delete(pw[0])
    #       else:
    #               # User exists in database, do nothing!
    #               pass

    # -------- #
    # sync_add #
    # -------- #

    print('\n===> start sync_add')
    pause()

    for username in UDB.list_newbies():
        usr = RBUser(uid=username)
        UDB.get_user_byname(usr)
        try:
            ACC.check_account_byname(usr)
        except RBFatalError:
            usr.passwd = rbconfig.gen_passwd()
            # print('Account password set for %s password: %s' % (usr.uid,
            #                                                     usr.passwd))
            UDB.set_passwd(usr)
            print("Account created: %s %s" % (usr.usertype, usr.uid))
            ACC.add(usr)
            print("User mailed:", usr.altmail)
            mailuser(usr)
            # pause()
        else:
            # New account exists, must be created already.
            if OPT.test:
                print('SKIPPED: account create:', usr.usertype, usr.uid)

    # ---------- #
    # sync_renew #
    # ---------- #

    print('\n===> start sync_renew')
    pause()

    if not os.path.isdir('renewal_mailed'):
        os.mkdir('renewal_mailed')

    for newuid in UDB.list_paid_non_newbies():
        # action = 0
        olduid = user_rename_reverse.get(newuid, newuid)
        if olduid not in old_ldap:
            print('WARNING: Existing non newbie user', newuid,
                  'not in previous copy of ldap tree!')
            continue

        newusr = RBUser(uid=newuid)
        UDB.get_user_byname(newusr)

        try:
            ACC.check_account_byname(newusr)
        except RBFatalError:
            # Accounts should be renamed & converted by now, so we
            # should never get here!
            #
            print("SKIPPED: User", newuid,
                  "missing account. Earlier rename/conversion not completed?")
            continue

        if not UDB.valid_shell(newusr.loginShell):
            newusr.loginShell = UDB.get_backup_shell(olduid)
            print('Account shell reset for:', newuid,
                  '(%s)' % newusr.loginShell)
            UDB.set_shell(newusr)
            # action = 1

        if not os.path.exists('renewal_mailed/%s' % newusr.uid):
            # Set a new password if they need one.
            #
            if reset_password.get(newuid):
                newusr.passwd = rbconfig.gen_passwd()
                print('Account password reset for %s password: %s' %
                      (newuid, newusr.passwd))
                UDB.set_passwd(newusr)
                action = 1

            # Send a mail to people who renewed. All renewals should have
            # an entry in reset_password i.e. 0 or 1.
            #
            if newuid in reset_password:
                print('User mailed:', newusr.uid, '(%s)' % newusr.altmail)
                mailuser(newusr)
                # action = 1

            # Flag this user as mailed so we don't do it again if
            # sync is rerun.
            #
            if not OPT.test:
                open('renewal_mailed/%s' % newusr.uid, 'w').close()
        elif OPT.test:
            print('SKIPPED: User mailed:', newusr.uid)

        # if action:
        #       pause()

    print()
    print('sync completed.')


def sync_dcu_info():
    """Interactive update of user database using dcu database information."""

    raise RBFatalError("NOT IMPLEMENTED YET")

    print('Comparing user and DCU databases. NOTE: please be patient')
    print('this takes some time...\n')

    # Set options for override & test mode.
    UDB.setopt(OPT)
    ACC.setopt(OPT)


# --------------------------------------------------------------------------- #
# BATCH INFORMATION COMMANDS                                                  #
# --------------------------------------------------------------------------- #


def list_users():
    """List all usernames."""

    for username in UDB.list_users():
        print(username)


def list_newbies():
    """List all paid newbies."""

    for username in UDB.list_paid_newbies():
        print(username)


def list_renewals():
    """List all paid renewals (non-newbie)."""

    for username in UDB.list_paid_non_newbies():
        print(username)


def list_unavailable():
    """List all usernames that are taken."""

    for username in UDB.list_reserved_all():
        print(username)


def list_unpaid():
    """Print list of all non-renewed users."""

    for username in UDB.list_unpaid():
        print(username)


def list_unpaid_normal():
    """Print list of all normal non-renewed users."""

    for username in UDB.list_unpaid_normal():
        print(username)


def list_unpaid_reset():
    """Print list of all normal non-renewed users with reset shells
    (i.e. not expired)."""

    for username in UDB.list_unpaid_reset():
        print(username)


def list_unpaid_grace():
    """Print list of all grace non-renewed users."""

    for username in UDB.list_unpaid_grace():
        print(username)


# --------------------------------------------------------------------------- #
# BATCH COMMANDS                                                              #
# --------------------------------------------------------------------------- #


def newyear():
    """Prepare database for start of new academic year."""

    raise RBFatalError("NOT IMPLEMENTED YET")

    # Set options for override & test mode.
    UDB.setopt(OPT)
    ACC.setopt(OPT)

    print('Prepared database for start of new academic year')
    UDB.newyear()


def unpaid_warn():
    """Mail a reminder/warning message to all non-renewed users."""

    # Set options for override & test mode.
    UDB.setopt(OPT)
    ACC.setopt(OPT)

    for username in UDB.list_unpaid():
        usr = RBUser(uid=username)
        UDB.get_user_byname(usr)
        print("Warned user:", username)
        mail_unpaid(usr)


def unpaid_disable():
    """Disable all normal non-renewed users."""

    # Set options for override & test mode.
    UDB.setopt(OPT)
    ACC.setopt(OPT)

    for username in UDB.list_unpaid_reset():
        print("Account disabled:", username)
        UDB.set_shell(RBUser(uid=username, loginShell=rbconfig.shell_expired))


def unpaid_delete():
    """Delete all grace non-renewed users."""

    # Set options for override & test mode.
    UDB.setopt(OPT)
    ACC.setopt(OPT)

    for username in UDB.list_unpaid_grace():
        usr = RBUser(uid=username)
        UDB.get_user_byname(usr)
        print('User deleted:', username)
        UDB.delete(usr)
        print('Account deleted:', username)
        ACC.delete(usr)


# --------------------------------------------------------------------------- #
# MISCELLANEOUS COMMANDS                                                      #
# --------------------------------------------------------------------------- #


def checkdb():
    """Check database for inconsistencies."""

    uidNumbers = {}
    re_mail = re.compile(r'.+@.*dcu\.ie', re.I)
    set_header('User database problems')
    unpaid_valid_shells = 0
    reserved = UDB.dict_reserved_desc()

    for uid in UDB.list_users():
        usr = RBUser(uid=uid)
        UDB.get_user_byname(usr)

        desc = reserved.get(uid)
        if desc:
            show_header()
            print('%-*s  is reserved: %s' % (rbconfig.maxlen_uname, uid, desc))

        if usr.uidNumber not in uidNumbers:
            uidNumbers[usr.uidNumber] = [uid]
        else:
            uidNumbers[usr.uidNumber].append(uid)

        if usr.usertype == 'member':
            try:
                UDB.get_student_byid(usr)
            except RBWarningError:
                show_header()
                print('%-*s  is a member without a valid DCU student id: %s' %
                      (rbconfig.maxlen_uname, uid, usr.id))

        if usr.yearsPaid is not None:
            if not -1 <= usr.yearsPaid <= 5:
                show_header()
                print('%-*s  has bogus yearsPaid: %s' % (rbconfig.maxlen_uname,
                                                         uid, usr.yearsPaid))

            if usr.newbie and usr.yearsPaid < 1:
                show_header()
                print('%-*s  is a newbie but is unpaid (yearsPaid = %s)' %
                      (rbconfig.maxlen_uname, uid, usr.yearsPaid))

            if usr.yearsPaid < 1 and UDB.valid_shell(usr.loginShell):
                unpaid_valid_shells += 1

            if usr.yearsPaid > 0 and not UDB.valid_shell(usr.loginShell):
                show_header()
                print('%-*s  is paid but has an invalid shell: %s' %
                      (rbconfig.maxlen_uname, uid, usr.loginShell))
            if usr.yearsPaid < -1:
                print('%-*s  has should have been deleted: %s' %
                      (rbconfig.maxlen_uname, uid, usr.yearsPaid))

        if usr.yearsPaid is None and usr.usertype in ('member', 'associat',
                                                      'staff'):
            show_header()
            print('%-*s  is missing a yearsPaid attribute' %
                  (rbconfig.maxlen_uname, uid))

        if usr.id is None and usr.usertype in ('member', 'associat', 'staff'):
            show_header()
            print('%-*s  is missing a DCU ID number' % (rbconfig.maxlen_uname,
                                                        uid))

        for directory, desc in (usr.homeDirectory,
                                'home'), (rbconfig.gen_webtree(uid),
                                          'webtree'):
            if not os.path.exists(directory) or not os.path.isdir(directory):
                show_header()
                print('%-*s  is missing %s directory: %s' %
                      (rbconfig.maxlen_uname, uid, desc, directory))
            else:
                stat = os.stat(directory)
                if (stat.st_uid, stat.st_gid) != (usr.uidNumber,
                                                  usr.gidNumber):
                    show_header()
                    print('%-*s  has wrong %s ownership' %
                          (rbconfig.maxlen_uname, uid, desc))
                if stat.st_mode & 0o020:
                    show_header()
                    print('%-*s  has group writeable %s' %
                          (rbconfig.maxlen_uname, uid, desc))
                if stat.st_mode & 0o002:
                    show_header()
                    print('%-*s  has WORLD writeable %s' %
                          (rbconfig.maxlen_uname, uid, desc))

        try:
            grp = UDB.get_group_byid(usr.gidNumber)
        except RBFatalError:
            grp = '#%d' % usr.gidNumber
            show_header()
            print('%-*s  has unknown gidNumber: %d' % (rbconfig.maxlen_uname,
                                                       uid, usr.gidNumber))

        if usr.usertype in ('member', 'staff', 'committe') and \
            (usr.altmail.lower().find('%s@redbrick.dcu.ie' % usr.uid) != -1 or
             not re.search(re_mail, usr.altmail)):
            show_header()
            print("%-*s  is a %s without a DCU altmail address: %s" %
                  (rbconfig.maxlen_uname, uid, usr.usertype, usr.altmail))

            # commented by receive, it makes stuff crash
            # if not usr.userPassword[7].isalnum(
            # ) and not usr.userPassword[7] in '/.':
            #     show_header()
            #     print('%-*s  has a disabled password: %s' %
            #           (rbconfig.maxlen_uname, uid, usr.userPassword))

        if usr.usertype != 'redbrick':
            if grp != usr.usertype:
                show_header()
                print('%-*s  has different group [%s] and usertype [%s]' %
                      (rbconfig.maxlen_uname, uid, grp, usr.usertype))

            if usr.homeDirectory != rbconfig.gen_homedir(uid, usr.usertype):
                show_header()
                print('%-*s  has wrong home directory [%s] for usertype [%s]' %
                      (rbconfig.maxlen_uname, uid, usr.homeDirectory,
                       usr.usertype))

    if unpaid_valid_shells > 0:
        show_header()
        print()
        print("There are %d shifty gits on redbrick. Unpaid users with valid" %
              unpaid_valid_shells)
        print("login shells, that is. Go get 'em.")

    set_header('Duplicate uidNumbers')

    for uidNumber, uids in list(uidNumbers.items()):
        if len(uids) > 1:
            show_header()
            print('%d  is shared by: %s' % (uidNumber, ', '.join(uids)))


def stats():
    """Show database and account statistics."""

    print(header('User database stats'))
    UDB.stats()


def create_uidNumber():
    """Find next available uidNumber and write it out to uidNumber
    text file."""

    next_number = UDB.uidNumber_findmax() + 1
    print('Next available uidNumber:', next_number)
    uid_file = open(rbconfig.file_uidNumber, 'w')
    uid_file.write('%s\n' % next_number)
    uid_file.close()


# --------------------------------------------------------------------------- #
# USER INPUT FUNCTIONS                                                        #
# --------------------------------------------------------------------------- #


def ask(prompt, default=None, optional=0, hints=None):
    """Ask a question using given prompt and return user's answer.

    A default answer maybe provided which is returned if no answer is given
    (i.e. user hits RETURN).

    If optional is false (the default) an answer is required. So if no
    default answer is given and the user presses RETURN, the question will
    be repeated.

    If optional is true, the first answer given is returned. If a default
    is provided an empty answer may be given by sending EOF (typically
    Control-D). If no default is provided an empty answer may be given by
    pressing RETURN.

    If there is more than one default answer these can be provided in the
    form of "hints" which the user can cycle through by hitting TAB. The
    default answer is also available by pressing TAB.

    """

    def complete(text, state):
        """Completion function used by readline module for ask().

        If no text typed in yet, offer all hints. Otherwise offer only
        hints that begin with the given text.

        """

        if not text and len(hints) > state:
            return str(hints[state])
        else:
            tmp = [i for i in hints if i.startswith(text)]
            if len(tmp) > state:
                return str(tmp[state])
        return None

    global INPUT_INSTRUCTIONS
    if INPUT_INSTRUCTIONS:
        print(INPUT_INSTRUCTIONS)
        INPUT_INSTRUCTIONS = None

    if hints is None:
        hints = []

    if default is None:
        defans = 'no default'
    else:
        defans = default

    hints = [i for i in hints if i is not None]
    num_hints = len(hints)

    if default is not None:
        if default not in hints:
            hints.insert(0, default)
        else:
            num_hints -= 1

    prompt = '%s\n%s%s[%s] >> ' % (prompt, optional and '(optional) ' or '',
                                   num_hints and '(hints) ' or '', defans)

    readline.parse_and_bind('tab: menu-complete')
    readline.set_completer(complete)

    ans = None
    while ans is None or ans == '':
        try:
            ans = input(prompt)
        except EOFError:
            print()
            ans = None
        else:
            if not ans:
                ans = default
        print()
        if optional:
            break
    return ans


def yesno(prompt, default=None):
    """Prompt for confirmation to a question. Returns boolean."""

    global INPUT_INSTRUCTIONS
    if INPUT_INSTRUCTIONS:
        print(INPUT_INSTRUCTIONS)
        INPUT_INSTRUCTIONS = None

    if default is None:
        defans = 'no default'
    else:
        if default:
            defans = 'yes'
        else:
            defans = 'no'

    prompt = '%s\n[%s] (Y/N) ? ' % (prompt, defans)

    ans = None
    while 1:
        try:
            ans = input(prompt)
        except EOFError:
            print()
            ans = None
        else:
            print()
            if ans and default is None:
                return default

        if ans:
            if re.search(r'^[yY]', ans):
                return 1
            elif re.search(r'^[nN]', ans):
                return 0


def pause():
    """Prompt for user input to continue."""

    print('Press RETURN to continue...')
    try:
        input()
    except EOFError:
        pass


# --------------------------------------------------------------------------- #
# MISCELLANEOUS FUNCTIONS                                                     #
# --------------------------------------------------------------------------- #


def header(mesg):
    """Return a simple header string for given message."""

    return '\n' + mesg + '\n' + '=' * len(mesg)


def set_header(mesg):
    """Set the heading for the next section."""

    global HEADER_MSG
    HEADER_MSG = header(mesg)


def show_header():
    """Display the heading for the current section as
    set by set_header(). Will only print header once."""

    global HEADER_MSG
    if HEADER_MSG:
        print(HEADER_MSG)
        HEADER_MSG = None


# --------------------------------------------------------------------------- #
# USER MAILING FUNCTIONS                                                      #
# --------------------------------------------------------------------------- #


def mailuser(usr):
    """Mail user's account details to their alternate email address."""

    file_descriptor = sendmail_open()
    file_descriptor.write("""From: Redbrick Admin Team <admins@redbrick.dcu.ie>
Subject: Welcome to Redbrick! - Your Account Details
To: %s
Reply-To: admin-request@redbrick.dcu.ie

""" % usr.altmail)
    if usr.newbie:
        file_descriptor.write("Welcome to Redbrick, \
            the DCU Networking Society! Thank you for joining.")
    else:
        file_descriptor.write("Welcome back to Redbrick, \
            the DCU Networking Society! Thank you for renewing.")
    file_descriptor.write("\n\nYour Redbrick Account details are:\n\n")

    file_descriptor.write('%21s: %s\n' % ('username', usr.uid))
    if usr.passwd:
        file_descriptor.write('%21s: %s\n\n' % ('password', usr.passwd))
    file_descriptor.write('%21s: %s\n' % ('account type', usr.usertype))
    file_descriptor.write('%21s: %s\n' % ('name', usr.cn))
    if usr.id is not None:
        file_descriptor.write('%21s: %s\n' % ('id number', usr.id))
    if usr.course:
        file_descriptor.write('%21s: %s\n' % ('course', usr.course))
    if usr.year is not None:
        file_descriptor.write('%21s: %s\n' % ('year', usr.year))

    file_descriptor.write("""
-------------------------------------------------------------------------------

your Redbrick webpage: https://www.redbrick.dcu.ie/~%s
your Redbrick email: %s@redbrick.dcu.ie

You can find out more about our services at:
https://www.redbrick.dcu.ie/about/welcome
""" % (usr.uid, usr.uid))

    file_descriptor.write("""
We recommend that you change your password as soon as you login.

Problems with your password or wish to change your username? Contact:
admin-request@redbrick.dcu.ie

Problems using Redbrick in general or not sure what to do? Contact:
helpdesk-request@redbrick.dcu.ie

Have fun!

- Redbrick Admin Team
""")

    sendmail_close(file_descriptor)


def mail_unpaid(usr):
    """Mail a warning to a non-renewed user."""

    file_descriptor = sendmail_open()
    file_descriptor.write("""From: Redbrick Admin Team <admins@redbrick.dcu.ie>
Subject: Time to renew your Redbrick account!
To: %s@redbrick.dcu.ie
""" % usr.uid)

    if usr.altmail.lower().find('%s@redbrick.dcu.ie' % usr.uid) == -1:
        file_descriptor.write('Cc:', usr.altmail)

    file_descriptor.write("""Reply-To: accounts@redbrick.dcu.ie

Hey there,

It's that time again to renew your Redbrick account!
Membership prices, as set by the SLC, are as follows:

Members      EUR 4
Associates   EUR 8
Staff        EUR 8
Guests       EUR 10

Note: if you have left DCU, you need to apply for associate membership.

You can pay in person, by lodging money into our account, electronic bank
transfer, or even PayPal! All the details you need are here:

https://www.redbrick.dcu.ie/help/joining/

Our bank details are:

a/c name: DCU Redbrick Society
IBAN: IE59BOFI90675027999600
BIC: BOFIIE2D
a/c number: 27999600
sort code: 90 - 67 - 50



Please Note!
------------""")
    # Change the message below every year

    if usr.yearsPaid == 0:
        file_descriptor.write("""
If you do not renew by the 30th October 2016, your account will be disabled.
Your account will remain on the system for a grace period of a year - you
just won't be able to login. So don't worry, it won't be deleted any time
soon! You can renew at any time during the year.
""")
    else:
        file_descriptor.write("""
If you do not renew within the following month, your account WILL BE
DELETED at the start of the new year. This is because you were not
recorded as having paid for last year and as such are nearing the end of
your one year 'grace' period to renew. Please make sure to renew as soon
as possible otherwise please contact us at: accounts@redbrick.dcu.ie.
""")
    file_descriptor.write("""
If in fact you have renewed and have received this email in error, it is
important you let us know. Just reply to this email and tell us how and
when you renewed and we'll sort it out.

For your information, your current Redbrick account details are:

         username: %s
     account type: %s
             name: %s
alternative email: %s
""" % (usr.uid, usr.usertype, usr.cn, usr.altmail))

    if usr.id is not None:
        file_descriptor.write('%21s: %s\n' % ('id number', usr.id))
    if usr.course:
        file_descriptor.write('%21s: %s\n' % ('course', usr.course))
    if usr.year is not None:
        file_descriptor.write('%21s: %s\n' % ('year', usr.year))

    file_descriptor.write("""
If any of the above details are wrong, please correct them when you
renew!

- Redbrick Admin Team
""")
    sendmail_close(file_descriptor)


def mail_committee(subject, body):
    """Email committee with given subject and message body."""

    file_descriptor = sendmail_open()
    file_descriptor.write("""From: Redbrick Admin Team <admins@redbrick.dcu.ie>
Subject: %s
To: committee@redbrick.dcu.ie

%s
""" % (subject, body))
    sendmail_close(file_descriptor)


def sendmail_open():
    """Return file descriptor to write email message to."""

    if OPT.test:
        sys.stderr.write(header('Email message that would be sent'))
        return sys.stderr
    else:
        return os.popen('%s -t -i' % rbconfig.command_sendmail, 'w')


def sendmail_close(file_descriptor):
    """Close sendmail file descriptor."""

    if not OPT.test:
        file_descriptor.close()


# --------------------------------------------------------------------------- #
# GET USER DATA FUNCTIONS                                                     #
# --------------------------------------------------------------------------- #


def get_username(usr, check_user_exists=1):
    """Get an existing username."""

    if len(OPT.args) > 0 and OPT.args[0]:
        usr.uid = OPT.uid = OPT.args.pop(0)
        interact = 0
    else:
        interact = 1

    while 1:
        if interact:
            usr.uid = ask('Enter username')
        try:
            UDB.check_username(usr.uid)

            if check_user_exists:
                print("Checking user exists")
                tmpusr = RBUser(uid=usr.uid)
                UDB.get_user_byname(tmpusr)
                UDB.check_user_byname(usr.uid)
                ACC.check_account_byname(tmpusr)
        except RBError as e:
            if not rberror(e, interact):
                break
        else:
            break
        if not interact:
            break


def get_freeusername(usr):
    """Get a new (free) username."""

    if len(OPT.args) > 0 and OPT.args[0]:
        usr.uid = OPT.uid = OPT.args.pop(0)
        interact = 0
    else:
        interact = 1

    while 1:
        if interact:
            usr.uid = ask('Enter new username')
        try:
            UDB.check_username(usr.uid)
            UDB.check_userfree(usr.uid)
        except RBError as e:
            if not rberror(e, interact):
                break
        else:
            break
        if not interact:
            return 0
    return 1


def get_usertype(usr):
    """Get usertype."""

    usr.oldusertype = usr.usertype

    if OPT.usertype:
        usr.usertype = OPT.usertype
        interact = 0
    else:
        interact = 1
        print("Usertype must be specified. List of valid usertypes:\n")
        for i in rbconfig.usertypes_list:
            if OPT.mode != 'renew' or i in rbconfig.usertypes_paying:
                print(" %-12s %s" % (i, rbconfig.usertypes[i]))
        print()

    defans = usr.usertype or 'member'

    while 1:
        if interact:
            usr.usertype = ask(
                'Enter usertype',
                defans,
                hints=[
                    i for i in rbconfig.usertypes_list
                    if OPT.mode != 'renew' or i in rbconfig.usertypes_paying
                ])
        try:
            if OPT.mode == 'renew':
                UDB.check_renewal_usertype(usr.usertype)
            else:
                UDB.check_usertype(usr.usertype)
        except RBError as e:
            if not rberror(e, interact):
                break
        else:
            break


def get_convert_usertype(usr):
    """Get usertype to convert to."""

    if OPT.usertype:
        usr.usertype = OPT.usertype
        interact = 0
    else:
        interact = 1
        print(
            "Conversion usertype must be specified. List of valid usertypes:\n"
        )
        for i in rbconfig.usertypes_list:
            print(" %-12s %s" % (i, rbconfig.usertypes[i]))

        print("\nSpecial committee positions (usertype is 'committe'):\n")
        for i, j in list(rbconfig.convert_usertypes.items()):
            print(" %-12s %s" % (i, j))
        print()

    while 1:
        if interact:
            usr.usertype = ask(
                'Enter conversion usertype',
                hints=list(rbconfig.usertypes_list) +
                list(rbconfig.convert_usertypes.keys()))
        try:
            UDB.check_convert_usertype(usr.usertype)
        except RBError as e:
            if not rberror(e, interact):
                break
        else:
            break


def get_id(usr):
    """Get DCU ID."""

    if usr.usertype not in rbconfig.usertypes_dcu and OPT.mode != 'update':
        return

    if OPT.id is not None:
        usr.id = OPT.id
        interact = 0
    else:
        interact = 1

    defans = usr.id

    while 1:
        if interact:
            usr.id = ask(
                'Enter student/staff id',
                defans,
                optional=OPT.mode == 'update' or usr.usertype == 'committe')
        try:
            if usr.id:
                usr.id = int(usr.id)
                UDB.check_id(usr)
        except (ValueError, RBError) as e:
            if not rberror(e, interact):
                break
        else:
            break


def get_name(usr, hints=None):
    """Get name (or account description)."""

    if OPT.cn:
        usr.cn = OPT.cn
        interact = 0
    else:
        interact = 1

    defans = usr.cn

    while 1:
        if interact:
            usr.cn = ask(
                "Enter name (or account description)", defans, hints=hints)
        try:
            UDB.check_name(usr)
        except RBError as e:
            if not rberror(e, interact):
                break
        else:
            break


def get_mailuser(usr):
    """Ask wheter to mail user their details."""

    if OPT.mailuser is not None:
        return

    if not usr.usertype == 'reserved':
        # By default mail them.
        OPT.mailuser = 1

        # If only adding database entry, don't mail.
        if OPT.mode == 'add' and OPT.dbonly:
            OPT.mailuser = 0

        OPT.mailuser = yesno('Mail account details to user', OPT.mailuser)
    else:
        OPT.mailuser = 0


def get_createaccount(usr):
    """Ask if account should be created."""

    if OPT.dbonly is not None and OPT.aconly is not None:
        return

    if not yesno('Create account', 1):
        OPT.dbonly = 1
        OPT.aconly = 0


def get_setpasswd(usr):
    """Ask if new random password should be set."""

    if OPT.setpasswd is not None:
        return

    # fixme
    # if OPT.dbonly != None:
    #       OPT.setpasswd = not OPT.dbonly
    #       return

    if OPT.mode == 'renew':
        OPT.setpasswd = 0
    else:
        OPT.setpasswd = 1
    OPT.setpasswd = yesno('Set new random password', OPT.setpasswd)


def get_newbie(usr):
    """Get newbie boolean."""

    if OPT.newbie is not None:
        usr.newbie = OPT.newbie
        return

    usr.newbie = yesno('Flag as a new user', usr.newbie)


def get_years_paid(usr):
    """Get years paid."""

    if usr.usertype not in rbconfig.usertypes_paying and OPT.mode != 'update':
        return

    if OPT.yearsPaid is not None:
        usr.yearsPaid = OPT.yearsPaid
        interact = 0
    else:
        interact = 1

    if OPT.mode == 'add' and usr.yearsPaid is None:
        usr.yearsPaid = 1
    defans = usr.yearsPaid

    while 1:
        if interact:
            usr.yearsPaid = ask(
                'Enter number of years paid',
                defans,
                optional=OPT.mode == 'update' or
                usr.usertype in ('committe', 'guest'))
        try:
            if usr.yearsPaid:
                usr.yearsPaid = int(usr.yearsPaid)
                UDB.check_years_paid(usr)
        except (ValueError, RBError) as e:
            if not rberror(e, interact):
                break
        else:
            break


def get_course(usr, hints=None):
    """Get DCU course."""

    if usr.usertype not in ('member', 'committee') and OPT.mode != 'update':
        return
    if OPT.course:
        usr.course = OPT.course
        return
    usr.course = ask(
        'Enter course',
        usr.course,
        optional=OPT.mode == 'update' or usr.usertype == 'committe',
        hints=hints)


def get_year(usr, hints=None):
    """Get DCU year."""

    if usr.usertype not in ('member', 'committee') and OPT.mode != 'update':
        return
    if OPT.year is not None:
        usr.year = OPT.year
        return
    usr.year = ask(
        'Enter year',
        usr.year,
        optional=OPT.mode == 'update' or usr.usertype == 'committe',
        hints=hints)


def get_email(usr, hints=None):
    """Get alternative email address."""

    if OPT.altmail:
        usr.altmail = OPT.altmail
        interact = 0
    else:
        interact = 1

    defans = usr.altmail

    while 1:
        if interact:
            usr.altmail = ask('Enter email', defans, hints=hints)
        try:
            UDB.check_email(usr)
        except RBError as e:
            if not rberror(e, interact):
                break
        else:
            break


def get_updatedby(usr):
    """Get username of who is performing the action.

    Uses LOGNAME environment variable by default unless it's 'root' in
    which case no default is provided. There is no actual restriction on
    using 'root', although its use (or any other generic username) is
    strongly not recommended.

    """

    if OPT.updatedby:
        usr.updatedby = OPT.updatedby
        interact = 0
    else:
        interact = 1
        usr.updatedby = os.environ.get('LOGNAME') or os.environ.get('SU_FROM')

    defans = usr.updatedby

    while 1:
        if interact:
            usr.updatedby = ask(
                'Enter who updated this user (give Unix username)', defans)
        try:
            UDB.check_updatedby(usr.updatedby)
        except RBError as e:
            if not rberror(e, interact):
                break
        else:
            break


def get_birthday(usr):
    """Get (optional) birthday."""

    if usr.usertype not in rbconfig.usertypes_paying:
        return

    if OPT.birthday is not None:
        usr.birthday = OPT.birthday or None
        interact = 0
    else:
        interact = 1

    defans = usr.birthday

    while 1:
        if interact:
            usr.birthday = ask(
                "Enter birthday as 'YYYY-MM-DD'", defans, optional=1)
        try:
            UDB.check_birthday(usr)
        except RBError as e:
            if not rberror(e, interact):
                break
        else:
            break


def get_disuser_period(usr):
    """Get (optional) period of disuserment."""

    if len(OPT.args) > 0:
        usr.disuser_period = OPT.args[0]
        interact = 0
    else:
        interact = 1

    while 1:
        if interact:
            usr.disuser_period = ask(
                '''
                If the account is to be automatically re-enabled,
                enter a valid at(1) timespec,
                e.g: '5pm', '12am + 2 weeks', 'now + 1 month' (see man page).
                ''',
                optional=1)
        try:
            UDB.check_disuser_period(usr)
        except RBError as e:
            if not rberror(e, interact):
                break
        else:
            break


def get_disuser_message(usr):
    """Get message to display when disusered user tries to log in."""

    file = os.path.join(rbconfig.dir_daft, usr.uid)
    editor = os.environ.get('EDITOR', os.environ.get('VISUAL', 'vi'))

    while 1:
        if not os.path.isfile(file):
            file_descriptor = open(file, "w")
            file_descriptor.write(
                "The contents of this file will be displayed when %s logs in.\n\
                 The reason for disuserment should be placed here.\n" %
                (usr.uid))
            file_descriptor.close()
        mtime = os.path.getmtime(file)
        os.system("%s %s" % (ACC.shquote(editor), ACC.shquote(file)))

        if not os.path.isfile(file) or not os.path.getsize(
                file) or mtime == os.path.getmtime(file):
            if not rberror(
                    RBWarningError('Unchanged disuser message file detected'),
                    1):
                break
        else:
            break
    os.chmod(file, 0o644)


def get_rrslog():
    """Get name of RRS log file."""

    if len(OPT.args) > 0 and OPT.args[0]:
        OPT.rrslog = OPT.args.pop(0)
        interact = 0
    else:
        interact = 1

    while 1:
        if interact:
            OPT.rrslog = ask('Enter name of RRS logfile', rbconfig.file_rrslog)
        try:
            open(OPT.rrslog, 'r').close()
        except IOError as e:
            if not rberror(e, interact):
                break
        else:
            break


def get_pre_sync():
    """Get name of pre_sync file."""

    if len(OPT.args) > 0 and OPT.args[0]:
        OPT.presync = OPT.args.pop(0)
        interact = 0
    else:
        interact = 1

    while 1:
        if interact:
            OPT.presync = ask('Enter name of pre_sync file',
                              rbconfig.file_pre_sync)
        try:
            open(OPT.presync, 'r').close()
        except IOError as e:
            if not rberror(e, interact):
                break
        else:
            break


def get_shell(usr):
    """Get user shell."""

    if len(OPT.args) > 0 and OPT.args[0]:
        usr.loginShell = OPT.args.pop(0)
        interact = 0
    else:
        interact = 1

    defans = usr.loginShell

    # fixme: gross hack to make dizer happy. preloads /etc/shells so we can
    # pass it as hints below
    #
    UDB.valid_shell('fuzz')

    while 1:
        if interact:
            usr.loginShell = ask(
                'Enter shell',
                defans,
                hints=[defans] + list(UDB.valid_shells.keys()))
        try:
            # fixme: valid_shell should raise an exception?
            if not UDB.valid_shell(usr.loginShell):
                raise RBWarningError('Not a valid shell')
        except RBError as e:
            if not rberror(e, interact):
                break
        else:
            break


def check_paid(usr):
    if usr.yearsPaid is not None and usr.yearsPaid < 1 and not yesno(
            'WARNING: This user has not renewed, continue?', 0):
        raise RBFatalError('Aborting, user has not paid.')


# --------------------------------------------------------------------------- #
# ERROR HANDLING                                                              #
# --------------------------------------------------------------------------- #


def rberror(e, interactive=0):
    """rberror(e[, interactive]) -> status

    Handle (mostly) RBError exceptions.

    Interactive: If e is a RBWarningError, prompt to override this error.
    If overridden, return false. Otherwise and for all other errors,
    return true.

    Not interactive: If e is a RBWarningError and the override option was
    set on the command line, return false. Otherwise and for all other
    errors, exit the program.

    """

    if not isinstance(e, RBError):
        print("FATAL: ")
    print(e)

    if not isinstance(e, RBWarningError):
        if interactive:
            print()
            return 1
    else:
        if interactive:
            print()
            if yesno('Ignore this error?'):
                OPT.override = 1
                return 0
            else:
                return 1
        elif OPT.override:
            print("[IGNORED]\n")
            return 0

    # If we reach here we're not in interactive mode and the override
    # option wasn't set, so all errors result in program exit.
    #
    print()
    sys.exit(1)


def error(e, mesg=None):
    """error(e[, mesg])

    Handle general exceptions: prints the 'FATAL:' prefix, optional
    message followed by the exception message. Exits program.

    """

    print("FATAL: ")
    if mesg:
        print(mesg)
    print(e)
    print()
    sys.exit(1)


# --------------------------------------------------------------------------- #
# If module is called as script, run main()                                   #
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    main()
