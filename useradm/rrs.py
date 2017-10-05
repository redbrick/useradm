# --------------------------------------------------------------------------- #
# MODULE DESCRIPTION                                                          #
# --------------------------------------------------------------------------- #
"""RedBrick Registration System CGI."""

# System modules

import atexit
import cgi
import cgitb
import os
import re
import sys
import time
from xml.sax.saxutils import quoteattr

import ldap
from rberror import RBError, RBFatalError, RBWarningError
from rbopt import RBOpt
from rbuser import RBUser
from rbuserdb import RBUserDB

# --------------------------------------------------------------------------- #
# DATA                                                                        #
# --------------------------------------------------------------------------- #

__version__ = '$Revision: 1.6 $'
__author__ = 'Cillian Sharkey'

cmds = {
    'card': 'Card reader interface',
    'add': 'Add new user',
    'delete': 'Delete user',
    'renew': 'Renew user',
    'update': 'Update user',
    'rename': 'Rename user',
    'convert': 'Convert user to new usertype',
    'show': 'Show user information',
    'freename': 'Check if a username is free',
    'search': 'Search user and DCU databases',
    'stats': 'Database statistics',
    'log': 'Log of all actions'
}

cmds_list = ('card', 'add', 'delete', 'renew', 'update', 'rename', 'convert',
             'show', 'freename', 'search', 'stats', 'log')

cmds_noform = {'stats': 1, 'log': 1}

cmds_custom = {'show': 1, 'search': 1}

fields = (
    ('updatedby', 'Updated By', ('card', 'add', 'delete', 'renew', 'update',
                                 'rename', 'convert')),
    ('cardid', 'DCU card id', ('card', )),
    ('uid', 'Username', ('card', 'add', 'delete', 'renew', 'update', 'rename',
                         'convert', 'show', 'search')),
    ('newuid', 'New username', ('renew', 'rename', 'freename')),
    ('newbie', 'New user?', ('update', )),
    ('birthday', 'Birthday', ('add', 'renew', 'update')),
    ('id', 'DCU ID', ('add', 'renew', 'update', 'search')),
    ('usertype', 'Usertype', ('add', 'renew', 'convert')),
    ('cn', 'Name', ('add', 'renew', 'update', 'search')),
    ('altmail', 'Email', ('add', 'renew', 'update')),
    ('course', 'Course Code', ('add', 'renew', 'update')),
    ('year', 'Course Year', ('add', 'renew', 'update')),
    ('yearsPaid', 'Years Paid', ('add', 'renew', 'update')),
    ('setpasswd', 'Set new password?', ('renew', )),
    ('override', 'Override errors?', ('card', 'add', 'renew', 'update',
                                      'rename')),
    ('dummyid', "Use 'dummy' ID?", ('card', )), )

# Optional side note for form fields. For a particular mode only, use
# "fieldname.mode".
#
fields_note = {
    'updatedby': 'your RedBrick username',
    'birthday': 'DD-MM-YYYY',
    'year': "'X' for exchange students",
    'yearsPaid': '5 is only for associates',
    'dummyid': 'New members only',
    'uid.search': 'Search user database',
    'id.search': 'Search user & DCU databases',
    'cn.search': 'Search user & DCU databases'
}

# Fields that are simple yes/no choices. These are implemented using radio
# dialogs instead of a checkbox, as they allow neither yes nor no to be set
# (i.e. None).
#
fields_yesno = {'setpasswd': 1, 'override': 1, 'dummyid': 1, 'newbie': 1}

# HTML for custom form input fields.
#
fields_input = {
    'cardid': 'class=fixed size=18 maxlength=16',
    'cn': 'size=30',
    'altmail': 'size=30',
    'course': 'size=10 maxlength=50',
    'year': 'size=10 maxlength=10'
}

# Global variables.
#
usr = RBUser()
opt = RBOpt()
udb = form = None  # Initalised later in main()
okay = 0
start_done = end_done = 0
error_string = notice_string = okay_string = ''

# --------------------------------------------------------------------------- #
# MAIN                                                                        #
# --------------------------------------------------------------------------- #


def main():
    """Program entry function."""

    # XXX: Stupid Apache on shrapnel has TZ set to US/Eastern, no idea why!
    os.environ['TZ'] = 'Eire'

    print("Content-type: text/html")
    print()

    atexit.register(shutdown)

    # Sets up an exception handler for uncaught exceptions and saves
    # traceback information locally.
    #
    cgitb.enable(logdir='%s/tracebacks' % os.getcwd())

    global form
    form = cgi.FieldStorage()

    opt.mode = form.getfirst('mode')
    if opt.mode not in cmds:
        opt.mode = 'card'
    opt.action = form.getfirst('action')
    # XXX remove usr.override
    # usr.override = opt.override = form.getfirst('override') == '1'
    opt.override = form.getfirst('override') == '1'

    # Start HTML now only for modes that print output *before* html_form is
    # called (which calls start_html itself). We delay the printing of the
    # header for all other modes as mode switching may occur (e.g.
    # cardid <-> add/renew).
    #
    if opt.mode in cmds_noform or (opt.mode in cmds_custom and opt.action):
        html_start()

    global udb
    udb = RBUserDB()
    udb.setopt(opt)

    # Open database and call function for specific command only if action
    # is required or the command needs no user input (i.e. no blank form
    # stage).
    #
    if opt.mode in cmds_noform or opt.action:
        try:
            udb.connect()
        except ldap.LDAPError as err:
            error(err, 'Could not connect to user database')
            # not reached
        try:
            eval(opt.mode + '()')
        except (ldap.LDAPError, RBError) as err:
            error(err)
            # not reached
    html_form()
    sys.exit(0)


def shutdown():
    """Cleanup function registered with atexit."""

    html_end()
    if udb:
        udb.close()


def html_start():
    """Start HTML output."""

    global start_done
    if start_done:
        return
    start_done = 1

    print("""<html>
<head>
<title>RedBrick Registration System v3.0 - %s</title>
<link rel="stylesheet" href="common.css" type="text/css">
<script language="JavaScript" type="text/javascript">
<!--
function page_load () {
    if (document.mainform) {
        f = document.mainform;
    } else {
        return;
    }
    if (f.updatedby && f.updatedby.value.length == 0) {
        f.updatedby.focus();
    } else if (f.cardid && f.cardid.value.length == 0) {
        f.cardid.focus();
    } else if (f.uid && f.uid.value.length == 0) {
        f.uid.focus();
    } else if (f.newuid && f.newuid.value.length == 0) {
        f.newuid.focus();
    } else if (f.cardid) {
        f.cardid.focus();
    } else if (f.uid) {
        f.uid.focus();
    } else if (f.newuid) {
        f.newuid.focus();
    }
}

function radio_value (r) {
    for (var i = 0; i < r.length; i++) {
        if (r[i].checked == true) {
            return (r[i].value);
        }
    }
    return (null);
}

function check_form (f) {
    if (f.updatedby && f.updatedby.value.length == 0) {
        alert("updatedby must be given");
        f.updatedby.focus();
        return false;
    }

    return true;
}
// -->
</script>
</head>
<body text=black bgcolor=white onLoad="javascript:page_load()">

<div id=top>RedBrick Registration System v3.0</div>

<div id=menu>
<form name=menuform action='rrs.cgi' method=get>""" % opt.mode.capitalize())
    if form.getfirst('updatedby'):
        print("<input type=hidden name=updatedby value=%s>" % quoteattr(
            form.getfirst('updatedby') or ''))
    for i in cmds_list:
        print("<input id=button type=submit name=mode value=%s> " % i)
    print("""</form>
</div>

<div id=top>%s</div>

<div id=main>
""" % cmds[opt.mode])


def html_form():
    """Output HTML form for current mode."""

    global usr

    html_start()

    if notice_string or error_string or okay_string:
        print("<table align=center id=msgs><tr><td>")
        if error_string:
            print("<span id=warn>%s</span>" % error_string.replace(
                '\n', '<br>\n'))
        if notice_string:
            print("<span id=notice>%s</span>" % notice_string.replace(
                '\n', '<br>\n'))
        if okay_string:
            print("<span id=okay>%s</span>" % okay_string.replace(
                '\n', '<br>\n'))
        print("</td></tr></table>")

    # Modes that never use a form or don't want a form when action has been
    # requested and successful.
    #
    if opt.mode in cmds_noform or (opt.mode in cmds_custom and opt.action
                                   and okay):
        return

    if okay:
        # Need a blank form, so create new user but keep updatedby set.
        # Set override & setpassword options back to default (off).
        #
        usr = RBUser(updatedby=form.getfirst('updatedby'))
        opt.override = 0
        opt.setpasswd = 0
    else:
        # We want to preserve the form input so fill in as much data on
        # the form as possible.
        #
        for k in list(form.keys()):
            if hasattr(usr, k) and getattr(usr, k) is None:
                setattr(usr, k, form.getfirst(k))
    print("""
        <form name=mainform onSubmit="javascript:return check_form(this)"
        action="rrs.cgi" method=get>
        <input type=hidden name=mode value=%s>
        <input type=hidden name=action value=1>""" % opt.mode)

    print(
        '<table align=center class=main border=0 cellpadding=1 cellspacing=5>')

    for field, desc, modes in fields:
        if opt.mode not in modes:
            # If updatedby isn't an actual visible field on the
            # form, add it as a hidden field so its value gets
            # passed on.
            #
            if field == 'updatedby' and form.getfirst('updatedby'):
                print('<input type=hidden name=updatedby value=%s>' %
                      quoteattr(form.getfirst('updatedby') or ''))
        else:
            usrval = ''
            if hasattr(usr, field) and getattr(usr, field) is not None:
                usrval = getattr(usr, field)
            if field == 'override':
                usrval = opt.override
            elif field == 'cardid' and not usrval and usr.id:
                usrval = usr.id

            print('<tr>')
            print('  <td class=side>%s</td>' % desc)
            print('  <td>', end=' ')

            if field in fields_input:
                print('<input %s name=%s value=%s>' %
                      (fields_input[field], field, quoteattr(str(usrval))))
            elif field in fields_yesno:
                print('''
                <input name=%s type=radio value=1%s> Yes <input
                name=%s type=radio value=0%s> No
                ''' % (field, usrval == 1 and ' checked' or '', field,
                       usrval == 0 and ' checked' or ''))
            elif field == 'usertype':
                # Show default usertype of member if none set.
                if not usr.usertype:
                    usr.usertype = 'member'

                print('<select name=usertype>')
                for i in rbconfig.usertypes_paying:
                    print('<option value=%s' % i, end=' ')
                    if usr.usertype == i:
                        print(' selected', end=' ')
                    print('>', i.capitalize())
                print('</select>')
            elif field == 'birthday':
                if usr.birthday:
                    res = re.search(r'^(\d{4})-(\d{2})-(\d{2})', usr.birthday)
                    if res:
                        usr.bday = res.group(3)
                        usr.bmonth = res.group(2)
                        usr.byear = res.group(1)
                print('''
                    <input size=2 maxlength=2 name=bday value='%s'>-<input
                    size=2 maxlength=2 name=bmonth value='%s'>-<input size=4
                    maxlength=4 name=byear value='%s'>
                    ''' % (usr.bday or '', usr.bmonth or '', usr.byear or ''))
            else:
                print(
                    "<input class=fixed size=10 maxlength=8 name=%s value=%s" %
                    (field, quoteattr(str(usrval))),
                    end=' ')
                if field == 'uid' and usr.uid and opt.mode in ('renew',
                                                               'update'):
                    print(' readonly', end=' ')
                print('>')

            print('</td>')
            print('  <td><span id=note>', end=' ')
            if '%s.%s' % (field, opt.mode) in fields_note:
                print(fields_note['%s.%s' % (field, opt.mode)], end=' ')
            elif field in fields_note:
                print(fields_note[field], end=' ')
            print('</span></td>')
            print('</tr>')
    print("""</table>
<p><input id=button type=submit value='%s &gt;&gt;'></p>
</form>""" % opt.mode.capitalize())


def html_end():
    """Finish HTML output."""

    global end_done
    if end_done:
        return
    end_done = 1

    print("""</div>
</body>
</html>""")


# --------------------------------------------------------------------------- #
# MAIN FUNCTIONS                                                              #
# --------------------------------------------------------------------------- #


def card():
    """Process input from card reader form. Mode will be switched to add or
    renew as appropriate if there were no problems with user input."""

    get_updatedby(usr)
    get_cardid(usr)
    newmode = None

    # We have an ID, is it a newbie or a renewal?
    #
    if usr.id is not None:
        try:
            udb.check_user_byid(usr.id)
        except RBError:
            # Doesn't exist, must be new user.
            newmode = 'add'
        else:
            # Exists, must be renewal.
            newmode = 'renew'
    elif form.getfirst('dummyid'):
        get_dummyid(usr)
        newmode = 'add'
    elif form.getfirst('uid'):
        usr.uid = form.getfirst('uid')
        udb.check_username(usr.uid)
        try:
            udb.check_user_byname(usr.uid)
        except RBError:
            # Doesn't exist, must be new user.
            newmode = 'add'
        else:
            # Exists, must be renewal.
            newmode = 'renew'
    else:
        raise RBFatalError("DCU Card ID, username or dummy ID must be given")

    if newmode == 'add':
        if usr.id is not None:
            udb.get_userinfo_new(usr)
        udb.get_userdefaults_new(usr)
    elif newmode == 'renew':
        curusr = RBUser()
        udb.get_userinfo_renew(usr, curusr, override=1)
        udb.check_unpaid(curusr)
        udb.get_userdefaults_renew(usr)
    if newmode:
        opt.mode = newmode


def add():
    """Add a new user."""

    global okay, okay_string

    get_updatedby(usr)
    get_usertype(usr)
    get_newusername(usr)
    get_id(usr)

    udb.get_userinfo_new(usr)
    udb.get_userdefaults_new(usr)

    get_name(usr)
    get_email(usr)
    get_course(usr)
    get_year(usr)
    get_years_paid(usr)
    get_birthday(usr)

    # Add user to database.
    #
    udb.add(usr)

    # If we reached here, operation was successful, so show result of
    # operation, log it and switch back to card mode.
    #
    okay = 1
    okay_string += 'OKAY: User added: %s %s (%s)' % (usr.usertype, usr.uid,
                                                     usr.cn)
    rrs_log_add('add:%s:%s:%s:%s:%s:%s:%s:%s:%s' %
                (usr.uid, usr.usertype, usr.id is not None and usr.id or '',
                 usr.cn, usr.course or '', usr.year or '', usr.altmail,
                 usr.birthday or '', usr.yearsPaid))
    opt.mode = 'card'


def delete():
    """Delete user."""

    global okay, okay_string

    get_updatedby(usr)
    get_username(usr)

    udb.delete(usr)

    okay = 1
    okay_string += 'OKAY: User deleted: %s\n' % usr.uid
    rrs_log_add('delete:%s' % (usr.uid))


def renew():
    """Renew user."""

    global okay, okay_string

    newusr = RBUser()
    curusr = RBUser()

    get_updatedby(usr)
    get_username(usr)
    get_newusername(newusr)

    udb.get_userinfo_renew(usr, curusr)
    udb.get_userdefaults_renew(usr)

    get_setpasswd(usr)
    get_usertype(usr)
    get_id(usr)

    udb.get_userinfo_renew(usr)

    get_name(usr)
    get_email(usr)
    get_course(usr)
    get_year(usr)
    get_years_paid(usr)
    get_birthday(usr)

    udb.renew(usr)

    okay_string += 'OKAY: User renewed: %s %s%s\n' % (
        usr.oldusertype, usr.uid,
        opt.setpasswd and ' [new password set]' or '')
    rrs_log_add('renew:%s:%s:%s:%s:%s:%s:%s:%s:%s:%s:%s' %
                (usr.uid, newusr.uid or '', opt.setpasswd and 1 or 0,
                 usr.usertype, usr.id is not None and usr.id or '', usr.cn,
                 usr.course or '', usr.year is not None and usr.year or '',
                 usr.altmail, usr.birthday or '', usr.yearsPaid))

    # NOTE: We don't actually generate/set a password here, just flag it in
    # the 'transaction log' so that sync_renew in useradm will set it
    # instead.

    # NOTE: If a renewal changed usertype, convert it and log it.
    # sync_renew in useradm will detect the usertype change and convert the
    # account.
    #
    if usr.oldusertype != usr.usertype:
        udb.convert(curusr, usr)
        okay_string += 'OKAY: User converted: %s -> %s\n' % (usr.uid,
                                                             usr.usertype)
        rrs_log_add('convert:%s:%s' % (usr.uid, usr.usertype))

    # NOTE: If new username is given, rename database entry and log it.
    # sync_rename in useradm will use this log entry to rename the account
    # but only if it's a rename of an existing user only (i.e newbie is
    # false).
    #
    if newusr.uid:
        udb.rename(usr, newusr)
        okay_string += 'OKAY: User renamed: %s -> %s\n' % (usr.uid, newusr.uid)
        rrs_log_add('rename-%s:%s:%s' % (usr.newbie and 'new' or 'existing',
                                         usr.uid, newusr.uid))

    okay = 1
    opt.mode = 'card'


def update():
    """Update user."""

    global okay, okay_string

    get_updatedby(usr)
    get_username(usr)
    udb.get_user_byname(usr)
    get_newbie(usr)
    get_id(usr)
    get_name(usr)
    get_email(usr)
    get_course(usr)
    get_year(usr)
    get_years_paid(usr)
    get_birthday(usr)

    udb.update(usr)

    okay = 1
    okay_string += 'OKAY: User updated: %s\n' % usr.uid
    rrs_log_add('update:%s:%s:%s:%s:%s:%s:%s:%s:%s' %
                (usr.uid, usr.newbie and 1 or 0,
                 usr.id is not None and usr.id or '', usr.cn, usr.course or '',
                 usr.year is not None and usr.year or '', usr.altmail,
                 usr.birthday or '', usr.yearsPaid))


def rename():
    """Rename user."""

    global okay, okay_string

    newusr = RBUser()
    get_updatedby(usr)
    get_username(usr)
    udb.get_user_byname(usr)
    get_newusername(newusr)

    udb.rename(usr, newusr)

    okay = 1
    okay_string += 'OKAY: User renamed: %s -> %s\n' % (usr.uid, newusr.uid)
    rrs_log_add('rename-%s:%s:%s' % (usr.newbie and 'new' or 'existing',
                                     usr.uid, newusr.uid))


def convert():
    """Convert user."""

    global okay, okay_string

    newusr = RBUser()
    get_updatedby(usr)
    get_username(usr)
    get_usertype(newusr)

    udb.convert(usr, newusr)

    okay = 1
    okay_string += 'OKAY: User converted: %s -> %s\n' % (usr.uid,
                                                         newusr.usertype)
    rrs_log_add('convert:%s:%s' % (usr.uid, newusr.usertype))


def show():
    """Show user's details."""

    global okay

    get_username(usr)
    udb.get_user_byname(usr)
    print('<pre>')
    udb.show(usr)
    print('</pre>')
    okay = 1


def freename():
    """Check if a username is free."""

    global okay_string

    get_newusername(usr)
    if usr.uid:
        okay_string += "OKAY: Username '%s' is free.\n" % usr.uid


def search():
    """Search user and/or DCU databases."""

    global okay

    if form.getfirst('uid'):
        uid = form.getfirst('uid')
        res = udb.search_users_byusername(uid)
        print('''<p align=center
            >User database search for username '%s' - %d match%s</p>
            ''' % (uid, len(res), len(res) != 1 and 'es' or ''))
        show_search_results(res)
        okay = 1
    elif 'id' in form or 'cn' in form:
        id = form.getfirst('id')
        cn = form.getfirst('cn')
        if id is not None:
            res = udb.search_users_byid(id)
            print('''<p align=center
                >User database search for ID '%s' - %d match%s</p>
                ''' % (id, len(res), len(res) != 1 and 'es' or ''))
        else:
            res = udb.search_users_byname(cn)
            print('''<p align=center
                >User database search for name '%s' - %d match%s</p>
                ''' % (cn, len(res), len(res) != 1 and 'es' or ''))

        show_search_results(res)

        if id is not None:
            res = udb.search_dcu_byid(id)
            print('''<p align=center
                >DCU database search for ID '%s' - %d match%s</p>
                ''' % (id, len(res), len(res) != 1 and 'es' or ''))
        else:
            res = udb.search_dcu_byname(cn)
            print('''<p align=center
                >DCU database search for name '%s' - %d match%s</p>
                ''' % (cn, len(res), len(res) != 1 and 'es' or ''))

        show_search_results(res)
        okay = 1
    else:
        raise RBFatalError('No search term given!')


def show_search_results(res):
    """Actual routine to display search results."""

    if res:
        print('<table align=center class=search>')
        print('''
            <tr><td></td>
            <td class=top>Username</td>
            <td class=top>Usertype</td>
            <td class=top>Id</td>
            <td class=top>Name</td>
            <td class=top>Course</td>
            <td class=top>Year</td>
            <td class=top>Email</td></tr>''')
        for uid, usertype, id, cn, course, year, altmail in res:
            print('<tr><td class=button>', end=' ')
            if uid:
                print(
                    '''
                    <form action=rrs.cgi method=get>
                    <input type=hidden name=updatedby value=%s>
                    <input type=hidden name=uid value=%s>
                    <input type=hidden name=action value=1>
                    <input id=button type=submit name=mode value=show>
                    </form>
                    ''' % (quoteattr(form.getfirst('updatedby') or ''), uid),
                    end=' ')
            print('''</td>
                <td>%s</td>
                <td>%s</td>
                <td>%s</td>
                <td>%s</td>
                <td>%s</td>
                <td>%s</td>
                <td>%s</td>
                </tr>''' % (uid or '-', usertype or '-', id or '-', cn,
                            course or '-', year or '-', altmail))
        print('</table>')


def stats():
    """Show database statistics."""

    print("<pre>")
    udb.stats()
    print("</pre>")


def log():
    """Show contents of rrs log file."""

    try:
        fd = open('rrs.log', 'r')
    except IOError as e:
        error(e, 'Could not open rrs.log')

    print('<pre>\n')
    if os.path.getsize('rrs.log') == 0:
        print('Logfile is empty.')
    else:
        for line in fd:
            print(line, end=' ')
    print('</pre>')
    fd.close()


# --------------------------------------------------------------------------- #
# GET USER DATA FUNCTIONS                                                     #
# --------------------------------------------------------------------------- #


def get_username(usr):
    """Get an existing username."""

    if form.getfirst('uid'):
        usr.uid = form.getfirst('uid')
    else:
        raise RBFatalError('Username must be given')

    udb.check_username(usr.uid)
    udb.check_user_byname(usr.uid)


def get_newusername(usr):
    """Get a new (free) username."""

    if opt.mode == 'add':
        if form.getfirst('uid'):
            usr.uid = form.getfirst('uid')
    else:
        if form.getfirst('newuid'):
            usr.uid = form.getfirst('newuid')

    # New username is optional for renewals but compulsory for all other
    # modes that require it (add, rename, freename).
    #
    if opt.mode == 'renew' and not usr.uid:
        return

    if not usr.uid:
        raise RBFatalError('New username must be given')

    try:
        udb.check_username(usr.uid)
        udb.check_userfree(usr.uid)
    except RBWarningError as e:
        error(e)


def get_cardid(usr):
    """Set usr.id to DCU ID number in cardid field.

    The ID will either be the 8 digit number when entered manually or the
    13 digit code produced by barcode and magnetic readers of the form
    xxIDNUMBERnnn with possible start and/or end sentinel characters such
    as ';' or '?'. Some readers will output a code number at the start,
    (to indicate the type of barcode or something) so we assume the 13 digit
    number is at the end (i.e. right-hand side) of the string.

    If invalid input is given, raises RBFatalError.

    NOTE: It is up to the caller to check if usr.id has been set,
    get_cardid does not require it to be set.

    """

    usr.id = form.getfirst('cardid')
    if usr.id is not None:
        res = re.search(r'\d{2}(\d{8})\d{3}\D*$', usr.id)
        if res:
            usr.id = int(res.group(1))
            return
        res = re.search(r'^(\d{8})$', usr.id)
        if res:
            usr.id = int(usr.id)
            return
        raise RBFatalError('Invalid ID number/card reader input')


def get_updatedby(usr):
    """Get username of who is performing the action."""

    if form.getfirst('updatedby'):
        usr.updatedby = form.getfirst('updatedby')
    else:
        raise RBFatalError('Updated by must be given')
    if usr.updatedby == 'root':
        raise RBFatalError('root not allowed for updatedby')

    udb.check_updatedby(usr.updatedby)


def get_usertype(usr):
    """Get usertype."""

    usr.oldusertype = usr.usertype

    if form.getfirst('usertype'):
        usr.usertype = form.getfirst('usertype')
    else:
        raise RBFatalError('Usertype must be given')

    udb.check_usertype(usr.usertype)


def get_id(usr):
    """Get DCU ID."""

    if usr.usertype in rbconfig.usertypes_dcu:
        if form.getfirst('id'):
            usr.id = int(form.getfirst('id'))
        else:
            raise RBFatalError('ID must be given')

        udb.check_id(usr)


def get_dummyid(usr):
    """Get 'dummy' DCU ID."""

    if form.getfirst('dummyid'):
        udb.get_dummyid(usr)
        # XXX remove usr.override
        # usr.override = opt.override = 1
        opt.override = 1


def get_name(usr):
    """Get name."""

    if form.getfirst('cn'):
        usr.cn = form.getfirst('cn')
    else:
        raise RBFatalError('Name must be given')

    udb.check_name(usr)


def get_years_paid(usr):
    """Get years paid."""

    if usr.usertype not in rbconfig.usertypes_paying:
        return
    if form.getfirst('yearsPaid'):
        usr.yearsPaid = int(form.getfirst('yearsPaid'))
    else:
        raise RBFatalError('Years paid must be given')

    udb.check_years_paid(usr)


def get_course(usr):
    """Get DCU course."""

    if usr.usertype not in ('member', 'committe'):
        return
    if form.getfirst('course'):
        usr.course = form.getfirst('course')
    else:
        raise RBFatalError('Course must be given')


def get_year(usr):
    """Get DCU year."""

    if usr.usertype not in ('member', 'committe'):
        return
    if form.getfirst('year'):
        usr.year = form.getfirst('year')
    else:
        raise RBFatalError('Year must be given')


def get_email(usr):
    """Get alternative email address."""

    if form.getfirst('altmail'):
        usr.altmail = form.getfirst('altmail')
    else:
        raise RBFatalError('Email must be given')
    try:
        udb.check_email(usr)
    except RBWarningError as e:
        error(e)


def get_birthday(usr):
    """Get (optional) birthday."""

    if form.getfirst('byear') or form.getfirst('bmonth') or form.getfirst(
            'bday'):
        if not (form.getfirst('byear') and form.getfirst('bmonth')
                and form.getfirst('bday')):
            raise RBFatalError('Incomplete birthday given')
        try:
            usr.birthday = '%.4d-%0.2d-%0.2d' % (int(form.getfirst('byear')),
                                                 int(form.getfirst('bmonth')),
                                                 int(form.getfirst('bday')))
        except ValueError:
            raise RBFatalError('Invalid birthday given')

        udb.check_birthday(usr)


def get_setpasswd(usr):
    """Get set new password boolean."""

    if form.getfirst('setpasswd') is not None:
        opt.setpasswd = form.getfirst('setpasswd') == '1'


def get_newbie(usr):
    """Get newbie boolean."""

    if form.getfirst('newbie') is not None:
        usr.newbie = form.getfirst('newbie') == '1'


# --------------------------------------------------------------------------- #
# LOGFILE HANDLING                                                            #
# --------------------------------------------------------------------------- #


def rrs_log_add(msg):
    """Add an entry for the current command to the logfile."""

    if not msg:
        msg = "%s:EMPTY MESSAGE" % opt.mode
    msg = "%s:%s:%s" % (time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                        usr.updatedby, msg)
    try:
        fd = open('rrs.log', 'a')
    except IOError as err:
        error('Could not write to rrs.log', err)
    print(msg, file=fd)
    fd.close()


# --------------------------------------------------------------------------- #
# ERROR HANDLING                                                              #
# --------------------------------------------------------------------------- #


def error(err, mesg=''):
    """Handle (mainly) RBError exceptions."""

    if not isinstance(err, RBError):
        prefix = 'FATAL: %s' % (mesg and mesg + '\n' or '')
    elif isinstance(err, RBWarningError) and opt.override:
        prefix = 'IGNORED: '
    else:
        prefix = ''

    global error_string
    error_string += '%s%s\n' % (prefix, err)

    if isinstance(err, RBWarningError) and opt.override:
        return

    # If we reach here the override option wasn't set, so all errors result
    # in program exit.
    #
    html_form()
    sys.exit(1)


# --------------------------------------------------------------------------- #
# If module is called as script, run main()                                   #
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    main()
