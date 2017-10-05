# --------------------------------------------------------------------------- #
# MODULE DESCRIPTION                                                          #
# --------------------------------------------------------------------------- #
"""RedBrick User Database Module; contains RBUserDB class."""
import crypt
import fcntl
import math
import os
import random
import re
import sys
import time

import ldap
import rbconfig
from rberror import RBError, RBFatalError, RBWarningError
from rbopt import RBOpt
from rbuser import RBUser

# --------------------------------------------------------------------------- #
# DATA                                                                        #
# --------------------------------------------------------------------------- #

__version__ = '$Revision: 1.10 $'
__author__ = 'Cillian Sharkey'

# --------------------------------------------------------------------------- #
# CLASSES                                                                     #
# --------------------------------------------------------------------------- #


class RBUserDB:
    """Class to interface with user database."""
    valid_shells = None
    backup_shells = None

    def __init__(self):
        """Create new RBUserDB object."""
        self.opt = RBOpt()
        self.ldap = None
        self.ldap_dcu = None

    def connect(self,
                uri=rbconfig.LDAP_URI,
                dn=rbconfig.LDAP_ROOT_DN,
                password=None,
                dcu_uri=rbconfig.LDAP_DCU_URI,
                dcu_dn=rbconfig.LDAP_DCU_RBDN,
                dcu_pw=None):
        """Connect to databases.
        Custom URI, DN and password may be given for RedBrick LDAP.
        Password if not given will be read from shared secret file set
        in rbconfig.
        Custom URI may be given for DCU LDAP. """
        if not password:
            try:
                pw_file = open(rbconfig.LDAP_ROOTPW_FILE, 'r')
                password = pw_file.readline().rstrip()
            except IOError:
                raise RBFatalError("Unable to open LDAP root password file")
            pw_file.close()

        if not dcu_pw:
            try:
                pw_file = open(rbconfig.LDAP_DCU_RBPW, 'r')
                dcu_pw = pw_file.readline().rstrip()
            except IOError:
                raise RBFatalError("Unable to open DCU AD root password file")
            pw_file.close()

        # Default protocol seems to be 2, set to 3.
        ldap.set_option(ldap.OPT_PROTOCOL_VERSION, 3)

        # Connect to RedBrick LDAP.
        self.ldap = ldap.initialize(uri)
        self.ldap.simple_bind_s(dn, password)

        # Connect to DCU LDAP (anonymous bind).
        self.ldap_dcu = ldap.initialize(dcu_uri)
        #       self.ldap_dcu.simple_bind_s('', '')
        self.ldap_dcu.simple_bind_s(dcu_dn, dcu_pw)

    def close(self):
        """Close database connections."""
        if self.ldap:
            self.ldap.unbind()
        if self.ldap_dcu:
            self.ldap_dcu.unbind()

    def setopt(self, opt):
        """Use given RBOpt object to retrieve options."""
        self.opt = opt

    # ------------------------------------------------------------------- #
    # USER CHECKING AND INFORMATION RETRIEVAL METHODS                     #
    # ------------------------------------------------------------------- #

    def check_userfree(self, uid):
        """Check if a username is free.
        If username is already used or is an LDAP group, an
        RBFatalError is raised. If the username is in the additional
        reserved LDAP tree, an RBWarningError is raised and checked if
        it is to be overridden. """
        res = self.ldap.search_s(rbconfig.ldap_accounts_tree,
                                 ldap.SCOPE_ONELEVEL, 'uid=%s' % uid)
        if res:
            raise RBFatalError(
                "Username '%s' is already taken by %s account (%s)" %
                (uid, res[0][1]['objectClass'][0].decode(),
                 res[0][1]['cn'][0].decode()))
        res = self.ldap.search_s(rbconfig.ldap_group_tree, ldap.SCOPE_ONELEVEL,
                                 'cn=%s' % uid)
        if res:
            raise RBFatalError("Username '%s' is reserved (LDAP Group)" % uid)
        res = self.ldap.search_s(rbconfig.ldap_reserved_tree,
                                 ldap.SCOPE_ONELEVEL, 'uid=%s' % uid)
        if res:
            self.rberror(
                RBWarningError("Username '%s' is reserved (%s)" % (uid, res[0][
                    1]['description'][0].decode())))

    def check_user_byname(self, uid):
        """Raise RBFatalError if given username does not exist in user
        database."""
        if not self.ldap.search_s(rbconfig.ldap_accounts_tree,
                                  ldap.SCOPE_ONELEVEL, 'uid=%s' % uid):
            raise RBFatalError("User '%s' does not exist" % uid)

    def check_user_byid(self, user_id):
        """Raise RBFatalError if given id does not belong to a user in
        user database."""
        if not self.ldap.search_s(rbconfig.ldap_accounts_tree,
                                  ldap.SCOPE_ONELEVEL, 'id=%s' % user_id):
            raise RBFatalError("User with id '%s' does not exist" % user_id)

    def check_group_byname(self, group):
        """Raise RBFatalError if given group does not exist in group
        database."""
        if not self.ldap.search_s(rbconfig.ldap_group_tree,
                                  ldap.SCOPE_ONELEVEL, 'cn=%s' % group):
            raise RBFatalError("Group '%s' does not exist" % group)

    def check_group_byid(self, gid):
        """Raise RBFatalError if given id does not belong to a group in
        group database."""
        if not self.ldap.search_s(rbconfig.ldap_group_tree,
                                  ldap.SCOPE_ONELEVEL, 'gidNumber=%s' % gid):
            raise RBFatalError("Group with id '%s' does not exist" % gid)

    # ------------------------------------------------------------------- #
    # INFORMATION RETRIEVAL METHODS                                       #
    # ------------------------------------------------------------------- #

    # fixme still needed ?

    # def get_usertype_byname(self, uid):
    #     """Return usertype for username in user database. Raise
    #     RBFatalError if user does not exist."""
    #     res = self.ldap.search_s(rbconfig.ldap_accounts_tree,
    #                              ldap.SCOPE_ONELEVEL, 'uid=%s' % usr.uid,
    #                              ('objectClass', ))
    #     if res:
    #         for i in res[0][1]['objectClass']:
    #             if i in rbconfig.usertypes:
    #                 return i
    #             else:
    #                raise RBFatalError("Unknown usertype for user '%s'" % uid)
    #         else:
    #             raise RBFatalError("User '%s' does not exist" % uid)

    def get_user_byname(self, usr):
        """Populate RBUser object with data from user with given
        username in user database. Raise RBFatalError if user does not
        exist."""
        res = self.ldap.search_s(rbconfig.ldap_accounts_tree,
                                 ldap.SCOPE_ONELEVEL, 'uid=%s' % usr.uid)
        if res:
            self.set_user(usr, res[0])
        else:
            raise RBFatalError("User '%s' does not exist" % usr.uid)

    def get_user_byid(self, usr):
        """Populate RBUser object with data from user with given id in
        user database. Raise RBFatalError if user does not exist."""
        res = self.ldap.search_s(rbconfig.ldap_accounts_tree,
                                 ldap.SCOPE_ONELEVEL, 'id=%s' % usr.id)
        if res:
            self.set_user(usr, res[0])
        else:
            raise RBFatalError("User with id '%s' does not exist" % usr.id)

    def get_userinfo_new(self, usr, override=0):
        """Checks if ID already belongs to an existing user and if so
        raises RBFatalError. Populates RBUser object with data for new
        user from DCU databases otherwise raises RBWarningError."""
        if usr.id is not None:
            tmpusr = RBUser(id=usr.id)
            try:
                self.get_user_byid(tmpusr)
            except RBError:
                pass
            else:
                raise RBFatalError("Id '%s' is already registered to %s (%s)" %
                                   (usr.id, tmpusr.uid, tmpusr.cn))
            self.get_dcu_byid(usr, override)

    def get_userinfo_renew(self, usr, curusr=None, override=0):
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
        usr.id = usr.id if usr.id is not None else curusr.id
        self.check_renewal_usertype(usr.usertype)

        if usr.usertype in rbconfig.usertypes_dcu:
            # Load the dcu data using usertype and ID set in the given usr
            # or failing that from the current user database.
            #
            dcuusr = RBUser(uid=usr.uid, usertype=usr.usertype, id=usr.id)
            try:
                self.get_dcu_byid(dcuusr, override=1)
            except RBError as err:
                self.rberror(err)

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
            if usr.usertype == 'associat':
                dcuusr.altmail = None
            usr.merge(dcuusr, override=override)

        usr.merge(RBUser(curusr, updatedby=None))

    @classmethod
    def get_userdefaults_new(cls, usr):
        """Populate RBUser object with default values for a new user.
        Usertype should be provided, but a default of member will be
        assumed."""
        if not usr.usertype:
            usr.usertype = 'member'
        if usr.newbie is None:
            usr.newbie = 1
        if (usr.yearsPaid is None and
                (usr.usertype in rbconfig.usertypes_paying) and
                usr.usertype not in ('committe', 'guest')):
            usr.yearsPaid = 1

    @classmethod
    def get_userdefaults_renew(cls, usr):
        """Populate RBUser object with some reasonable default values
        for renewal user"""
        if usr.usertype in rbconfig.usertypes_paying:
            if usr.yearsPaid is None or usr.yearsPaid < 1:
                usr.yearsPaid = 1

    def get_dcu_byid(self, usr, override=0):
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
            except RBError as err:
                try:
                    self.get_student_byid(usr, override)
                except RBError as err:
                    if usr.usertype not in ('associat', 'staff'):
                        self.rberror(err)
                else:
                    usertype = 'member'
            else:
                usertype = 'associat'
        else:
            usertype = 'staff'

        # fixme: this overrides committe people (typically back to member)
        # which probably shouldn't be done?
        if usertype and (override or not usr.usertype):
            usr.usertype = usertype

        return

        # Graduates now remain in the (currently student, but may
        # change) LDAP tree for their life long email accounts so try
        # to load in information for associates (but don't fail if we
        # can't).
        #

        # if usr.usertype in ('member', 'associat', 'committe'):
        #     try:
        #         self.get_student_byid(usr, override)
        #     except RBError, e:
        #         if usr.usertype != 'associat':
        #             self.rberror(e)
        # # Not all staff may be in the LDAP tree, so don't fail if we
        # # can't get their information either.
        # #
        # elif usr.usertype == 'staff':
        #     try:
        #         self.get_staff_byid(usr, override)
        #     except RBError:
        #         pass

    def get_student_byid(self, usr, override=0):
        """Populate RBUser object with data from user with given id in
        student database.
        By default will only populate RBUser attributes that have no
        value (None) unless override is enabled.
        Note that all students *should* be in the database, but only
        raise a RBWarningError if user does not exist."""
        res = self.ldap_dcu.search_s(rbconfig.ldap_dcu_students_tree,
                                     ldap.SCOPE_SUBTREE,
                                     'employeeNumber=%s' % usr.id)
        if res:
            self.set_user_dcu(usr, res[0], override)
            self.set_user_dcu_student(usr, res[0], override)
        else:
            raise RBWarningError(
                "Student id '%s' does not exist in database" % usr.id)

    def get_alumni_byid(self, usr, override=0):
        """Populate RBUser object with data from user with given id in
        alumni database.
        By default will only populate RBUser attributes that have no
        value (None) unless override is enabled.
        Not all alumni will be in the database, so only raise a
        RBWarningError if user does not exist."""

        res = self.ldap_dcu.search_s(rbconfig.ldap_dcu_alumni_tree,
                                     ldap.SCOPE_SUBTREE, 'cn=%s' % usr.id)
        if res:
            self.set_user_dcu(usr, res[0], override)
            self.set_user_dcu_alumni(usr, res[0], override)
        else:
            raise RBWarningError(
                "Alumni id '%s' does not exist in database" % usr.id)

    def get_staff_byid(self, usr, override=0):
        """Populate RBUser object with data from user with given id in
        staff database.
        By default will only populate RBUser attributes that have no
        value (None) unless override is enabled.
        Not all staff are in the database, so only raise a
        RBWarningError if user does not exist."""

        # Staff ID is not consistently set. It will either be in the cn
        # or in the gecos, so try both.
        #
        res = self.ldap_dcu.search_s(
            rbconfig.ldap_dcu_staff_tree, ldap.SCOPE_SUBTREE,
            '(|(cn=%s)(gecos=*,*%s))' % (usr.id, usr.id))
        if res:
            self.set_user_dcu(usr, res[0], override)
            self.set_user_dcu_staff(usr, res[0], override)
        else:
            raise RBWarningError(
                "Staff id '%s' does not exist in database" % usr.id)

    def get_dummyid(self, usr):
        """Set usr.id to unique 'dummy' DCU ID number."""
        raise RBFatalError('NOT YET IMPLEMENTED')
        res = self.ldap.search_s(rbconfig.ldap_accounts_tree,
                                 ldap.SCOPE_ONELEVEL,
                                 '(&(id>=10000000)(id<20000000))"' % (usr.uid))
        if res:
            usr.id = int(res[0][1]['id'][0]) + 1
        else:
            usr.id = 10000000

    def get_gid_byname(self, group):
        """Get gid for given group name.
        Raise RBFatalError if given name does not belong to a group in
        group database."""
        res = self.ldap.search_s(rbconfig.ldap_group_tree, ldap.SCOPE_ONELEVEL,
                                 'cn=%s' % group)
        if res:
            return int(res[0][1]['gidNumber'][0])
        else:
            raise RBFatalError("Group '%s' does not exist" % group)

    def get_group_byid(self, gid):
        """Get group name for given group ID.
        Raise RBFatalError if given id does not belong to a group in
        group database."""
        res = self.ldap.search_s(rbconfig.ldap_group_tree, ldap.SCOPE_ONELEVEL,
                                 'gidNumber=%s' % gid)
        if res:
            return res[0][1]['cn'][0]
        else:
            raise RBFatalError("Group with id '%s' does not exist" % gid)

    def get_backup_shell(self, username):
        """Return shell for given user from previous year's LDAP tree
        or failing that, the default shell."""
        # fixme Use old passwd.backup file FTTB. Should use
        # ou=<prevyear>,ou=accounts tree instead.
        if self.backup_shells is None:
            self.backup_shells = {}
            backup = open(rbconfig.file_backup_passwd, 'r')
            for line in backup.readlines():
                passwd = line.split(':')
                self.backup_shells[passwd[0]] = passwd[6].rstrip()
            backup.close()

        return self.backup_shells.get(username, rbconfig.shell_default)

    # ------------------------------------------------------------------- #
    # USER DATA SYNTAX CHECK METHODS                                      #
    # ------------------------------------------------------------------- #

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

    @classmethod
    def check_username(cls, uid):
        """Raise RBFatalError if username is not valid."""
        if not uid:
            raise RBFatalError('Username must be given')
        if re.search(r'[^a-z0-9_.-]', uid):
            raise RBFatalError("Invalid characters in username")
        if len(uid) > rbconfig.maxlen_uname:
            raise RBFatalError("Username can not be longer than %d characters"
                               % rbconfig.maxlen_uname)
        if re.search(r'^[^a-z0-9]', uid):
            raise RBFatalError("Username must begin with letter or number")

    @classmethod
    def check_usertype(cls, usertype):
        """Raise RBFatalError if usertype is not valid."""
        if not usertype:
            raise RBFatalError('Usertype must be given')
        if usertype not in rbconfig.usertypes:
            raise RBFatalError("Invalid usertype '%s'" % usertype)

    @classmethod
    def check_convert_usertype(cls, usertype):
        """Raise RBFatalError if conversion usertype is not valid."""
        if not (usertype in rbconfig.usertypes or
                usertype in rbconfig.convert_usertypes):
            raise RBFatalError("Invalid conversion usertype '%s'" % usertype)

    @classmethod
    def check_renewal_usertype(cls, usertype):
        """Raise RBFatalError if renewal usertype is not valid."""
        if usertype not in rbconfig.usertypes_paying:
            raise RBFatalError("Invalid renewal usertype '%s'" % usertype)

    @classmethod
    def check_id(cls, usr):
        """Raise RBFatalError if ID is not valid for usertypes
        that require one."""
        if usr.usertype in rbconfig.usertypes_dcu:
            if usr.id is not None:
                if not isinstance(usr.id, int):
                    raise RBFatalError('ID must be an integer')
                if usr.id >= 100000000:
                    raise RBFatalError("Invalid ID '%s'" % (usr.id))
            elif usr.usertype not in ('committe', 'guest'):
                raise RBFatalError('ID must be given')

    @classmethod
    def check_years_paid(cls, usr):
        """Raise RBFatalError if years_paid is not valid."""
        if usr.usertype in rbconfig.usertypes_paying:
            if usr.yearsPaid is not None:
                if not isinstance(usr.yearsPaid, int):
                    raise RBFatalError('Years paid must be an integer')
                if usr.yearsPaid < -1:
                    raise RBFatalError('Invalid number of years paid')
            elif usr.usertype not in ('committe', 'guest'):
                raise RBFatalError('Years paid must be given')

    @classmethod
    def check_name(cls, usr):
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
        if (usr.usertype in ('member', 'staff') and not
                re.search(r'.+@.*dcu\.ie', usr.altmail, re.I)):
            self.rberror(
                RBWarningError("%s users should have a DCU email address" % (
                    usr.usertype)))

    def check_updatedby(self, updatedby):
        """Raise RBFatalError if updatedby is not a valid username."""

        if not updatedby:
            raise RBFatalError('Updated by must be given')
        try:
            self.check_user_byname(updatedby)
        except RBError:
            raise RBFatalError(
                "Updated by username '%s' is not valid" % updatedby)

    @classmethod
    def check_birthday(cls, usr):
        """Raise RBFatalError if the birthday is not valid,
        if set (it's optional)."""

        if usr.birthday:
            if not re.search(r'^\d{4}-\d{1,2}-\d{1,2}$', usr.birthday):
                raise RBFatalError('Birthday format must be YYYY-MM-DD')

    @classmethod
    def check_disuser_period(cls, usr):
        """Raise RBFatalError if the period of disuserment is not valid."""

        if usr.disuser_period and not re.search(r'^[-0-9a-zA-Z:"\'+ ]+$',
                                                usr.disuser_period):
            raise RBFatalError("Invalid characters in disuser period")

    def check_unpaid(self, usr):
        """Raise RBWarningError if the user is already paid up."""

        if usr.yearsPaid is not None and usr.yearsPaid > 0:
            self.rberror(
                RBWarningError("User '%s' is already paid!" % usr.uid))

    # ------------------------------------------------------------------- #
    # SINGLE USER METHODS                                                 #
    # ------------------------------------------------------------------- #

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
        self.set_updated(usr)

        usr_uid, usr.uidNumber = self.uidNumber_getnext()

        if not usr.objectClass:
            usr.objectClass = [usr.usertype
                               ] + rbconfig.ldap_default_objectClass

        self.wrapper(self.ldap.add_s,
                     self.uid2dn(usr.uid), self.usr2ldap_add(usr))

        self.uidNumber_savenext(usr_uid, usr.uidNumber + 1)
        self.uidNumber_unlock(usr_uid)

    def delete(self, usr):
        """Delete user from database."""

        self.check_user_byname(usr.uid)
        self.wrapper(self.ldap.delete_s, self.uid2dn(usr.uid))

    def renew(self, usr):
        """Renew and update RBUser object in database."""

        curusr = RBUser()

        self.get_userinfo_renew(usr, curusr)
        self.check_unpaid(curusr)
        self.get_userdefaults_renew(usr)
        self.check_userdata(usr)
        self.set_updated(usr)

        self.wrapper(self.ldap.modify_s,
                     self.uid2dn(usr.uid), self.usr2ldap_renew(usr))

    def update(self, usr):
        """Update RBUser object in database."""

        self.get_user_byname(usr)
        self.check_updatedby(usr.updatedby)
        self.check_userdata(usr)
        self.set_updated(usr)

        self.wrapper(self.ldap.modify_s,
                     self.uid2dn(usr.uid), self.usr2ldap_update(usr))

    def rename(self, usr, newusr):
        """Rename a user.

        Renamed additonal attributes (homeDirectory, updated,
        updatedby) are set in newusr.

        Requires: usr.uid, usr.updatedby, newusr.uid.

        """

        self.check_username(usr.uid)
        self.check_username(newusr.uid)
        self.get_user_byname(usr)
        self.check_userfree(newusr.uid)
        self.check_updatedby(usr.updatedby)

        # Rename DN first.
        #
        self.wrapper(self.ldap.rename_s,
                     self.uid2dn(usr.uid), 'uid=%s' % newusr.uid)

        # Rename homedir and update the updated* attributes.
        #
        self.set_updated(newusr)
        newusr.homeDirectory = rbconfig.gen_homedir(newusr.uid, usr.usertype)
        newusr.merge(usr)
        self.wrapper(self.ldap.modify_s,
                     self.uid2dn(newusr.uid), self.usr2ldap_rename(newusr))

    def convert(self, usr, newusr):
        """Convert a user to a different usertype."""

        self.get_user_byname(usr)
        self.check_convert_usertype(newusr.usertype)
        self.check_updatedby(usr.updatedby)

        # If usertype is one of the pseudo usertypes, change the
        # usertype to 'committe' for the database conversion.
        #
        if newusr.usertype in rbconfig.convert_usertypes:
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

        self.wrapper(self.ldap.modify_s,
                     self.uid2dn(usr.uid), self.usr2ldap_convert(newusr))

    def set_passwd(self, usr):
        """Set password for given user from the plaintext password
        in usr.passwd."""

        usr.userPassword = self.userPassword(usr.passwd)
        self.wrapper(self.ldap.modify_s,
                     self.uid2dn(usr.uid), ((ldap.MOD_REPLACE, 'userPassword',
                                             usr.userPassword), ))

    def set_shell(self, usr):
        """Set shell for given user."""

        self.wrapper(self.ldap.modify_s,
                     self.uid2dn(usr.uid), ((ldap.MOD_REPLACE, 'loginShell',
                                             usr.loginShell), ))

    def reset_shell(self, usr):
        """Reset shell for given user."""

        tmpusr = RBUser(uid=usr.uid)
        self.get_user_byname(tmpusr)
        if self.valid_shell(tmpusr.loginShell):
            return 0

        # usr.loginShell = self.get_backup_shell(usr.uid)
        usr.loginShell = rbconfig.shell_default
        self.set_shell(usr)
        return 1

    # ------------------------------------------------------------------- #
    # SINGLE USER INFORMATION METHODS                                     #
    # ------------------------------------------------------------------- #

    @classmethod
    def show(cls, usr):
        """Show RBUser object information on standard output."""

        for i in usr.attr_list_all:
            if getattr(usr, i) is not None:
                print("%13s: %s" % (i, getattr(usr, i)))

    @classmethod
    def info(cls, usr):
        """Show passwordless RBUser object information on standard output."""

        for i in usr.attr_list_info:
            if getattr(usr, i) is not None:
                print("%13s: %s" % (i, getattr(usr, i)))

    @classmethod
    def show_diff(cls, usr, oldusr):
        """
        Show RBUser object information on standard output.

        Show any attributes in usr which differ in value from those in
        oldusr.
        """

        for i in ('uid', 'usertype', 'newbie', 'cn', 'altmail', 'id', 'course',
                  'year', 'yearsPaid'):
            info = getattr(usr, i)
            if info is not None:
                old_info = getattr(oldusr, i, None)
                print("%15s: %s" % (old_info != info and "(NEW) " + i or i,
                                    info))
                if old_info != info:
                    print("%15s: %s" % ("(OLD) " + i, getattr(oldusr, i)))

    # ------------------------------------------------------------------- #
    # BATCH INFORMATION METHODS                                           #
    # ------------------------------------------------------------------- #

    # ----------------------- #
    # METHODS RETURNING LISTS #
    # ----------------------- #

    def list_pre_sync(self):
        """Return dictionary of all users for useradm pre_sync() dump."""

        res = self.ldap.search_s(
            rbconfig.ldap_accounts_tree, ldap.SCOPE_ONELEVEL,
            'objectClass=posixAccount', ('uid', 'homeDirectory',
                                         'objectClass'))
        tmp = {}
        for data in res:
            for i in data['objectClass']:
                i = i.decode()
                if i in rbconfig.usertypes:
                    break
            else:
                raise RBFatalError(
                    "Unknown usertype for user '%s'" % data['uid'][0])

            tmp[data['uid'][0]] = {
                'homeDirectory': data['homeDirectory'][0],
                'usertype': data['uid'][0]
            }
        return tmp

    def list_users(self):
        """Return list of all usernames."""
        res = self.ldap.search_s(rbconfig.ldap_accounts_tree,
                                 ldap.SCOPE_ONELEVEL,
                                 'objectClass=posixAccount', ('uid', ))
        return [data['uid'][0] for dn, data in res]

    def list_paid_newbies(self):
        """Return list of all paid newbie usernames."""
        res = self.ldap.search_s(rbconfig.ldap_accounts_tree,
                                 ldap.SCOPE_ONELEVEL,
                                 '(&(yearsPaid>=1)(newbie=TRUE))', ('uid', ))
        return [data['uid'][0] for dn, data in res]

    def list_paid_non_newbies(self):
        """Return list of all paid renewal (non-newbie) usernames."""
        res = self.ldap.search_s(rbconfig.ldap_accounts_tree,
                                 ldap.SCOPE_ONELEVEL,
                                 '(&(yearsPaid>=1)(newbie=FALSE))', ('uid', ))
        return [data['uid'][0] for dn, data in res]

    def list_non_newbies(self):
        """Return list of all non newbie usernames."""
        res = self.ldap.search_s(rbconfig.ldap_accounts_tree,
                                 ldap.SCOPE_ONELEVEL, 'newbie=FALSE',
                                 ('uid', ))
        return [data['uid'][0] for dn, data in res]

    def list_newbies(self):
        """Return list of all newbie usernames."""
        res = self.ldap.search_s(rbconfig.ldap_accounts_tree,
                                 ldap.SCOPE_ONELEVEL, 'newbie=TRUE', ('uid', ))
        return [data['uid'][0] for dn, data in res]

    def list_groups(self):
        """Return list of all groups."""
        res = self.ldap.search_s(rbconfig.ldap_group_tree, ldap.SCOPE_ONELEVEL,
                                 'objectClass=posixGroup', ('cn', ))
        return [data['cn'][0] for dn, data in res]

    def list_reserved(self):
        """Return list of all reserved entries."""
        res = self.ldap.search_s(rbconfig.ldap_reserved_tree,
                                 ldap.SCOPE_ONELEVEL, 'objectClass=reserved',
                                 ('uid', ))
        return [data['uid'][0] for dn, data in res]

    def list_reserved_static(self):
        """Return list of all static reserved names."""
        res = self.ldap.search_s(
            rbconfig.ldap_reserved_tree, ldap.SCOPE_ONELEVEL,
            '(&(objectClass=reserved)(flag=static))', ('uid', ))
        return [data['uid'][0] for dn, data in res]

    def list_reserved_dynamic(self):
        """Return list of all dynamic reserved names."""
        res = self.ldap.search_s(
            rbconfig.ldap_reserved_tree, ldap.SCOPE_ONELEVEL,
            '(&(objectClass=reserved)(!(flag=static)))', ('uid', ))
        return [data['uid'][0] for dn, data in res]

    def list_reserved_all(self):
        """Return list of all usernames that are taken or reserved.
        This includes all account usernames, all reserved usernames and
        all groupnames."""
        return self.list_users() + self.list_reserved() + self.list_groups()

    def list_unpaid(self):
        """Return list of all non-renewed users."""
        res = self.ldap.search_s(rbconfig.ldap_accounts_tree,
                                 ldap.SCOPE_ONELEVEL, 'yearsPaid<=0',
                                 ('uid', ))
        return [data['uid'][0] for dn, data in res]

    def list_unpaid_normal(self):
        """Return list of all normal non-renewed users."""
        res = self.ldap.search_s(rbconfig.ldap_accounts_tree,
                                 ldap.SCOPE_ONELEVEL, 'yearsPaid=0', ('uid', ))
        return [data['uid'][0] for dn, data in res]

    def list_unpaid_grace(self):
        """Return list of all grace non-renewed users."""
        res = self.ldap.search_s(rbconfig.ldap_accounts_tree,
                                 ldap.SCOPE_ONELEVEL, 'yearsPaid<=-1',
                                 ('uid', ))
        return [data['uid'][0] for dn, data in res]

    def list_unpaid_reset(self):
        """Return list of all non-renewed users with reset shells
        (i.e. not expired)."""
        res = self.ldap.search_s(
            rbconfig.ldap_accounts_tree, ldap.SCOPE_ONELEVEL,
            '(&(yearsPaid<=0)(!(loginShell=%s)))' % rbconfig.shell_expired,
            ('uid', ))
        return [data['uid'][0] for dn, data in res]

    # ------------------------------ #
    # METHODS RETURNING DICTIONARIES #
    # ------------------------------ #

    def dict_reserved_desc(self):
        """Return dictionary of all reserved entries with their
        description."""
        res = self.ldap.search_s(rbconfig.ldap_reserved_tree,
                                 ldap.SCOPE_ONELEVEL, 'objectClass=reserved',
                                 ('uid', 'description'))
        tmp = {}
        for data in res:
            tmp[data['uid'][0]] = data['description'][0]
        return tmp

    def dict_reserved_static(self):
        """Return dictionary of all static reserved entries with their
        description."""
        res = self.ldap.search_s(
            rbconfig.ldap_reserved_tree, ldap.SCOPE_ONELEVEL,
            '(&(objectClass=reserved)(flag=static))', ('uid', 'description'))
        tmp = {}
        for data in res:
            tmp[data['uid'][0]] = data['description'][0]
        return tmp

    # -------------------------------- #
    # METHODS RETURNING SEARCH RESULTS #
    # -------------------------------- #

    def search_users_byusername(self, uid):
        """Search user database by username and return results
        ((username, usertype, id, name, course, year, email), ...)"""
        raise RBFatalError("NOT IMLEMENTED YET")
        self.cur.execute(
            ('SELECT username, usertype, id, name, course, year, email '
             'FROM users WHERE username LIKE %s'), ('%%%s%%' % uid, ))
        return self.cur.fetchall()

    def search_users_byid(self, user_id):
        """Search user database by id and return results
        ((username, id, name, course, year), ...)"""
        raise RBFatalError("NOT IMLEMENTED YET")
        return self.search_users('id LIKE', user_id)

    def search_users_byname(self, name):
        """Search user database by name and return results as per
        search_users_byid()."""
        raise RBFatalError("NOT IMLEMENTED YET")
        return self.search_users('name ILIKE', name)

    def search_users(self, where, var):
        """Performs actual user database search with given where clause
        and data."""
        raise RBFatalError("NOT IMLEMENTED YET")
        self.cur.execute(
            ('SELECT username, usertype, id, name, course, year, email '
             'FROM users WHERE ') + where + ' %s', ('%%%s%%' % var, ))
        return self.cur.fetchall()

    def search_dcu_byid(self, user_id):
        """Search user & DCU databases by id and return results
        ((username, id, name, course, year), ...)"""
        raise RBFatalError("NOT IMLEMENTED YET")
        return self.search_dcu('s.id LIKE', user_id)

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
        self.cur.execute('''
            SELECT u.username, u.usertype, s.id,
                   s.name, s.course, s.year, s.email
            FROM students s LEFT JOIN users u USING (id) WHERE''' + where +
                         ' %s', (var, ))
        res = self.cur.fetchall()
        self.cur.execute(
            ('SELECT u.username, u.usertype, s.id, s.name, s.email '
             'FROM staff s LEFT JOIN users u USING (id) WHERE ') + where +
            '%s', (var, ))
        return [(username, usertype, id, name, None, None, email)
                for username, usertype, id, name, email in self.cur.fetchall()
                ] + res

    # ------------------------------------------------------------------- #
    # BATCH METHODS                                                       #
    # ------------------------------------------------------------------- #

    def newyear(self):
        """Prepare database for start of new academic year.
        This involves the following: creating a backup of the current
        users table for the previous academic year for archival
        purposes, reducing all paying users subscription by one year
        and setting the newbie field to false for all users."""
        raise RBFatalError("NOT IMLEMENTED YET")
        year = time.localtime()[0] - 1
        self.execute('CREATE TABLE users%d AS SELECT * FROM users', (year, ))
        self.execute('CREATE INDEX users%d_username_key ON users%d (username)',
                     (year, year))
        self.execute('CREATE INDEX users%d_id_key ON users%d (id)', (year,
                                                                     year))
        self.execute('''
            UPDATE users
            SET years_paid = years_paid - 1
            WHERE years_paid IS NOT NULL
            ''')
        self.execute("UPDATE users SET newbie = 'f'")
        self.dbh.commit()

    # ------------------------------------------------------------------- #
    # MISCELLANEOUS METHODS                                               #
    # ------------------------------------------------------------------- #

    def stats(self):
        """Print database statistics on standard output."""
        usertypes = {}
        categories = ('paid', 'unpaid', 'nonpay', 'newbie', 'signed_paid',
                      'signed_unpaid', 'signed_nonpay', 'signed_newbie',
                      'nosign_paid', 'nosign_unpaid', 'nosign_nonpay',
                      'nosign_newbie', 'TOTAL')
        for k in rbconfig.usertypes:
            usertypes[k] = dict([(c, 0) for c in categories])

        for uid in self.list_users():
            usr = RBUser(uid=uid)
            self.get_user_byname(usr)
            usertypes[usr.usertype]['TOTAL'] += 1
            signed = not self.opt.dbonly and os.path.exists(
                os.path.join(rbconfig.dir_signaway_state, uid))
            pay = (usr.yearsPaid is None and 'nonpay' or
                   usr.yearsPaid > 0 and 'paid' or 'unpaid')
            usertypes[usr.usertype][pay] += 1
            usertypes[usr.usertype]['%s_%s' %
                                    (not signed and 'nosign' or 'signed',
                                     pay)] += 1

            if usr.newbie:
                usertypes[usr.usertype]['newbie'] += 1
                usertypes[usr.usertype]['%s_newbie' % (
                    not signed and 'nosign' or 'signed')] += 1

        ordered_usertypes = list(rbconfig.usertypes_list) + [
            i for i in rbconfig.usertypes if i not in rbconfig.usertypes_list
        ]

        # Print out table.
        print(" " * 9, end=' ')
        for cat in categories:
            if len(cat) > 6:
                print("%7s" % cat[:6], end=' ')
            else:
                print(" " * 7, end=' ')
        print()

        print(" " * 9, end=' ')
        for cat in categories:
            if len(cat) > 6:
                print("%7.6s" % cat[-(len(cat) - 6):], end=' ')
            else:
                print("%7s" % cat, end=' ')
        print()

        print(" " * 9, end=' ')
        for _ in range(len(categories)):
            print(' ', '=' * 5, end=' ')
        print()

        # Work out category totals.
        #
        category_totals = dict([(c, 0) for c in categories])

        for usertype in ordered_usertypes:
            print("%9s" % usertype, end=' ')
            usertype = usertypes[usertype]
            for cat in categories:
                print("%7d" % usertype[cat], end=' ')
                category_totals[cat] += usertype[cat]
            print()

        print(" " * 9, end=' ')
        for _ in range(len(categories)):
            print(' ', '=' * 5, end=' ')
        print()
        print('%9s' % 'ALL', end=' ')
        for cat in categories:
            print("%7d" % category_totals[cat], end=' ')
        print('\n\n')

        total_paid = 0
        for user in 'member', 'committe', 'staff':
            total_paid += usertypes[user]['paid']

        print("Total paid members, committee & staff:", total_paid)
        print("Quorum (rounded-up square root of above):",
              math.ceil(math.sqrt(total_paid)))
        print(
            "'Active' users (paid and non-paying signed-in users):",
            category_totals['signed_paid'] + category_totals['signed_nonpay'])
        print("%d of %d newbies signed-in (%d%%)\n" %
              (category_totals['signed_newbie'], category_totals['newbie'],
               100.0 * category_totals['signed_newbie'] / category_totals[
                   'newbie']))

    @classmethod
    def crypt(cls, password):
        """Return crypted DES password."""

        saltchars = "./0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrs\
                    tuvwxyz"

        return crypt.crypt(password,
                           saltchars[random.randrange(len(saltchars))] +
                           saltchars[random.randrange(len(saltchars))])

    @classmethod
    def userPassword(cls, password):
        """Return string suitable for LDAP userPassword attribute based on given
        plaintext password."""

        if password:
            return "{CRYPT}" + cls.crypt(password)

        # fixme: is this correct way to disable password?
        return "{CRYPT}*"

    @classmethod
    def uid2dn(cls, uid):
        """Return full Distinguished Name (DN) for given username."""

        return "uid=%s,%s" % (uid, rbconfig.ldap_accounts_tree)

    def uidNumber_findmax(self):
        """Return highest uidNumber found in LDAP accounts tree.
        This is only used to create the uidNumber file, the
        uidNumber_readnext() function should be used for getting the
        next available uidNumber."""

        res = self.ldap.search_s(rbconfig.ldap_accounts_tree,
                                 ldap.SCOPE_ONELEVEL,
                                 'objectClass=posixAccount', ('uidNumber', ))

        maxuid = -1
        for i in res:
            tmp = int(i[1]['uidNumber'][0])
            if tmp > maxuid:
                maxuid = tmp

        return maxuid

    def uidNumber_getnext(self):
        """Get the next available uidNumber for adding a new user.
        Locks uidNumber file, reads number. Returns (file descriptor,
        uidNumber). uidNumber_savenext() must be called once the
        uidNumber is used successfully."""

        uid_num_file = os.open(rbconfig.file_uidNumber, os.O_RDWR)
        retries = 0

        while 1:
            try:
                fcntl.lockf(uid_num_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except IOError:
                retries += 1
                if retries == 20:
                    raise RBFatalError(
                        ('Could not lock uidNumber.txt file after 20 attempts.'
                         'Please try again!'))
                time.sleep(0.5)
            else:
                break
        num_uid = int(os.read(uid_num_file, 32))
        return uid_num_file, num_uid

    def uidNumber_savenext(self, fd, uidNumber):
        """Save next uidNumber.

        Writes uidNumber to file descriptor fd, which must be the one
        returned by uidNumber_getnext(). Does not write anything if in
        test mode."""

        if not self.opt.test:
            os.lseek(fd, 0, 0)
            os.write(fd, '%s\n' % uidNumber)
            os.fdatasync(fd)

    def uidNumber_unlock(self, fd):
        """Unlock uidNumber text file.
        This must be called after the last call to uidNumber_save() so
        that other processes can now obtain a lock on this file.
        The file will be unlocked after process termination though."""
        os.close(fd)

    def valid_shell(self, shell):
        """Check if given shell is valid by checking against /etc/shells."""

        if not shell:
            return 0

        if self.valid_shells is None:
            self.valid_shells = {}
            re_shell = re.compile(r'^([^\s#]+)')
            shell_file = open(rbconfig.file_shells, 'r')
            for line in shell_file.readlines():
                if line.strip() != rbconfig.shell_expired:
                    res = re_shell.search(line)
                    if res:
                        self.valid_shells[res.group(1)] = 1
            shell_file.close()
        return shell in self.valid_shells

    # ------------------------------------------------------------------ #
    # INTERNAL METHODS                                                   #
    # ------------------------------------------------------------------ #

    @classmethod
    def usr2ldap_add(cls, usr):
        """Return a list of (type, attribute) pairs for given user.
        This list is used in LDAP add queries."""

        tmp = [('uid', usr.uid), ('objectClass', usr.objectClass),
               ('newbie', usr.newbie and 'TRUE' or
                'FALSE'), ('cn', usr.cn), ('altmail', usr.altmail),
               ('updatedby', usr.updatedby), ('updated', usr.updated),
               ('createdby',
                usr.updatedby), ('created', usr.created), ('uidNumber',
                                                           str(usr.uidNumber)),
               ('gidNumber',
                str(usr.gidNumber)), ('gecos', usr.gecos), ('loginShell',
                                                            usr.loginShell),
               ('homeDirectory',
                usr.homeDirectory), ('userPassword',
                                     usr.userPassword), ('host', usr.host)]
        if usr.id is not None:
            tmp.append(('id', str(usr.id)))
        if usr.course:
            tmp.append(('course', usr.course))
        if usr.year is not None:
            tmp.append(('year', usr.year))
        if usr.yearsPaid is not None:
            tmp.append(('yearsPaid', str(usr.yearsPaid)))
        if usr.birthday:
            tmp.append(('birthday', usr.birthday))
        return tmp

    @classmethod
    def usr2ldap_renew(cls, usr):
        """Return a list of (type, attribute) pairs for given user.
        This list is used in LDAP modify queries for renewing."""

        tmp = [
            (ldap.MOD_REPLACE, 'newbie', usr.newbie and 'TRUE' or 'FALSE'),
            (ldap.MOD_REPLACE, 'cn', usr.cn),
            (ldap.MOD_REPLACE, 'altmail', usr.altmail),
            (ldap.MOD_REPLACE, 'updatedby', usr.updatedby),
            (ldap.MOD_REPLACE, 'updated', usr.updated),
        ]
        if usr.id is not None:
            tmp.append((ldap.MOD_REPLACE, 'id', str(usr.id)))
        if usr.course:
            tmp.append((ldap.MOD_REPLACE, 'course', usr.course))
        if usr.year is not None:
            tmp.append((ldap.MOD_REPLACE, 'year', usr.year))
        if usr.yearsPaid is not None:
            tmp.append((ldap.MOD_REPLACE, 'yearsPaid', str(usr.yearsPaid)))
        if usr.birthday:
            tmp.append((ldap.MOD_REPLACE, 'birthday', usr.birthday))
        return tmp

    @classmethod
    def usr2ldap_update(cls, usr):
        """Return a list of (type, attribute) pairs for given user.
        This list is used in LDAP modify queries for updating."""

        tmp = [(ldap.MOD_REPLACE, 'newbie', usr.newbie and 'TRUE' or
                'FALSE'), (ldap.MOD_REPLACE, 'cn', usr.cn),
               (ldap.MOD_REPLACE, 'altmail',
                usr.altmail), (ldap.MOD_REPLACE, 'updatedby', usr.updatedby),
               (ldap.MOD_REPLACE, 'updated', usr.updated)]
        if usr.id is not None:
            tmp.append((ldap.MOD_REPLACE, 'id', str(usr.id)))
        if usr.course:
            tmp.append((ldap.MOD_REPLACE, 'course', usr.course))
        if usr.year is not None:
            tmp.append((ldap.MOD_REPLACE, 'year', usr.year))
        if usr.yearsPaid is not None:
            tmp.append((ldap.MOD_REPLACE, 'yearsPaid', str(usr.yearsPaid)))
        if usr.birthday:
            tmp.append((ldap.MOD_REPLACE, 'birthday', usr.birthday))
        return tmp

    @classmethod
    def usr2ldap_rename(cls, usr):
        """Return a list of (type, attribute) pairs for given user.
        This list is used in LDAP modify queries for renaming."""

        return ((ldap.MOD_REPLACE, 'homeDirectory', usr.homeDirectory),
                (ldap.MOD_REPLACE, 'updatedby',
                 usr.updatedby), (ldap.MOD_REPLACE, 'updated', usr.updated))

    @classmethod
    def usr2ldap_convert(cls, usr):
        """Return a list of (type, attribute) pairs for given user.
        This list is used in LDAP modify queries for converting."""

        return ((ldap.MOD_REPLACE, 'objectClass', usr.objectClass),
                (ldap.MOD_REPLACE, 'gidNumber', str(usr.gidNumber)),
                (ldap.MOD_REPLACE, 'homeDirectory',
                 usr.homeDirectory), (ldap.MOD_REPLACE, 'updatedby',
                                      usr.updatedby), (ldap.MOD_REPLACE,
                                                       'updated', usr.updated))

    def gen_accinfo(self, usr):
        """Generate information for user account"""
        if not usr.userPassword:
            usr.userPassword = self.userPassword(usr.passwd)
        if not usr.homeDirectory:
            usr.homeDirectory = rbconfig.gen_homedir(usr.uid, usr.usertype)
        if usr.gidNumber is None:
            usr.gidNumber = self.get_gid_byname(usr.usertype)
        if not usr.gecos:
            # Hide a user's identity for paying accounts.
            if usr.usertype in rbconfig.usertypes_paying:
                usr.gecos = usr.uid
            else:
                usr.gecos = usr.cn
        if not usr.loginShell:
            usr.loginShell = rbconfig.shell_default
        if not usr.host:
            usr.host = rbconfig.ldap_default_hosts

    @classmethod
    def set_updated(cls, usr):
        """Set updated in given usr to current local time.
        Also sets created and createdby if not set in given usr."""

        usr.updated = time.strftime('%Y-%m-%d %H:%M:%S')
        if not usr.created:
            usr.created = usr.updated
            usr.createdby = usr.updatedby

    @classmethod
    def set_user(cls, usr, res):
        """Populate RBUser object with information from LDAP query.
        By default will only populate RBUser attributes that have no
        value (None)."""

        if not usr.usertype:
            for i in res[1]['objectClass']:
                i = i.decode()
                if i in rbconfig.usertypes:
                    usr.usertype = i
                    break
            else:
                raise RBFatalError("Unknown usertype for user '%s'" % usr.uid)

        for k, var in list(res[1].items()):
            if getattr(usr, k) is None:
                if k == 'newbie':
                    usr.newbie = var[0].decode == 'TRUE'
                elif k not in RBUser.attr_list_value:
                    setattr(usr, k, var[0].decode())
                else:
                    setattr(usr, k, var)

        # LDAP returns everything as strings, so booleans and integers
        # need to be converted:
        if usr.id:
            usr.id = int(usr.id)
        if usr.yearsPaid:
            usr.yearsPaid = int(usr.yearsPaid)
        usr.uidNumber = int(usr.uidNumber)
        usr.gidNumber = int(usr.gidNumber)

    @classmethod
    def set_user_dcu(cls, usr, res, override=0):
        """Populate RBUser object with common information from DCU LDAP query.
        By default will only populate RBUser attributes that have no
        value (None) unless override is enabled."""

        # Construct their full name from first name ('givenName')
        # followed by their surname ('sn') or failing that, from their
        # gecos up to the comma.
        if override or usr.cn is None:
            if res[1].get('givenName') and res[1].get('sn'):
                usr.cn = '%s %s' % (res[1]['givenName'][0], res[1]['sn'][0])
            elif res[1].get('gecos'):
                usr.cn = res[1].get('gecos')[:res[1].get('gecos').find(',')]

        if override or usr.altmail is None:
            usr.altmail = res[1]['mail'][0]

    @classmethod
    def set_user_dcu_student(cls, usr, res, override=0):
        """Populate RBUser object with student information from DCU
        LDAP query."""

        # Extract course & year from 'l' attribute if set. Assumes last
        # character is the year (1, 2, 3, 4, X, O, C, etc.) and the
        # rest is the course name. Uppercase course & year for
        # consistency.
        if res[1].get('l'):
            if override or usr.course is None:
                usr.course = res[1]['l'][0][:-1].upper()
            if override or usr.year is None:
                usr.year = res[1]['l'][0][-1].upper()

    @classmethod
    def set_user_dcu_staff(cls, usr, res, override=0):
        """Populate RBUser object with staff information from DCU
        LDAP query."""
        # Set course to department name from 'l' attribute if set.
        if res[1].get('l'):
            if override or usr.course is None:
                usr.course = res[1]['l'][0]

    @classmethod
    def set_user_dcu_alumni(cls, usr, res, override=0):
        """Populate RBUser object with alumni information from DCU
        LDAP query."""
        # Extract course & year from 'l' attribute if set. Assumes
        # syntax of [a-zA-Z]+[0-9]+ i.e. course code followed by year
        # of graduation. Uppercase course for consistency.
        if res[1].get('l'):
            tmp = res[1].get('l')[0]
            for i, _ in enumerate(tmp):
                if tmp[i].isdigit():
                    if override or usr.year is None:
                        usr.year = tmp[i:]
                    if override or usr.course is None:
                        usr.course = tmp[:i].upper()
                    break
            else:
                if override or usr.course is None:
                    usr.course = tmp.upper()

    def wrapper(self, function, *keywords, **arguments):
        """Wrapper method for executing other functions.
        If test mode is set, print function name and arguments.
        Otherwise call function with arguments."""
        if self.opt.test:
            sys.stderr.write("TEST: %s(" % function.__name__)
            for i in keywords:
                sys.stderr.write("%s, " % (i, ))
            for k, var in list(arguments.items()):
                sys.stderr.write("%s = %s, " % (k, var))
            sys.stderr.write(")\n")
        else:
            return function(*keywords, **arguments)

    def execute(self, sql, params=None):
        """Wrapper method for executing given SQL query."""
        if params is None:
            params = ()
        if self.opt.test:
            print("TEST:", (sql % params), file=sys.stderr)
        else:
            self.cur.execute(sql, params)

    # ------------------------------------------------------------------ #
    # ERROR HANDLING                                                     #
    # ------------------------------------------------------------------ #

    def rberror(self, err):
        """Handle RBError exceptions.
        If e is an RBWarningError and the override option is set,
        ignore the exception and return. Otherwise, raise the exception
        again."""
        if self.opt.override and isinstance(err, RBWarningError):
            return
        # If we reach here it's either a FATAL error or there was no
        # override for a WARNING error, so raise it again to let the
        # caller handle it.
        raise err
