"""Data for the rbuser to_string test"""

MEMBER_ONE_ATTR = {'cn': 'Member One',
                   'id': 15358462,
                   'uid': 'memberOne',
                   'bday': 12,
                   'host': 'carbon',
                   'year': 3,
                   'gecos': 'new member',
                   'byear': 2017,
                   'bmonth': 2,
                   'passwd': 'e1NTSEF9WlBURGtJdmZJSld0WUlrak9zdGxscXYySTRRVEhBYj=',
                   'newbie': True,
                   'course': 'CASE',
                   'created': '2009-10-06 11:20:13',
                   'altmail': 'memberOne@example.dcu.ie',
                   'updated': '2015-09-28 01:42:21',
                   'birthday': '12 02 2017',
                   'usertype': 'member',
                   'updatedby': 'admin',
                   'uidNumber': 102007,
                   'createdby': 'admin',
                   'gidNumber': 1017,
                   'yearsPaid': 1,
                   'loginShell': '/usr/local/shells/zsh',
                   'objectClass': ['redbrick', 'posixAccount', 'top', 'shadowAccount'],
                   'oldusertype': 'newb',
                   'userPassword': 'e1NTSEF9WlBURGtJdmZJSld0WUlrak9zdGxscXYySTRRVEhj=',
                   'homeDirectory': '/home/redbrick/memberOne',
                   'disuser_period': 0,
                   'shadowLastChange': 17073, }
MEMBER_ONE_OUTPUT = \
    'cn                :  Member One\n' + \
    'id                :  15358462\n' + \
    'uid               :  memberOne\n' + \
    'bday              :  12\n' + \
    'host              :  carbon\n' + \
    'year              :  3\n' + \
    'byear             :  2017\n' + \
    'gecos             :  new member\n' + \
    'bmonth            :  2\n' + \
    'course            :  CASE\n' + \
    'newbie            :  True\n' + \
    'passwd            :  e1NTSEF9WlBURGtJdmZJSld0WUlrak9zdGxscXYySTRRVEhBYj=\n' + \
    'altmail           :  memberOne@example.dcu.ie\n' + \
    'created           :  2009-10-06 11:20:13\n' + \
    'updated           :  2015-09-28 01:42:21\n' + \
    'birthday          :  12 02 2017\n' + \
    'usertype          :  member\n' + \
    'createdby         :  admin\n' + \
    'gidNumber         :  1017\n' + \
    'uidNumber         :  102007\n' + \
    'updatedby         :  admin\n' + \
    'yearsPaid         :  1\n' + \
    'loginShell        :  /usr/local/shells/zsh\n' + \
    'objectClass       :  [\'redbrick\', \'posixAccount\', \'top\', ' + \
    '\'shadowAccount\']\n' + \
    'oldusertype       :  newb\n' + \
    'userPassword      :  e1NTSEF9WlBURGtJdmZJSld0WUlrak9zdGxscXYySTRRVEhj=\n' + \
    'homeDirectory     :  /home/redbrick/memberOne\n' + \
    'disuser_period    :  0\n' + \
    'shadowLastChange  :  17073\n'

ASSOCIATE_ONE_ATTR = {'cn': 'Associate One',
                      'id': 15358478,
                      'uid': 'associateOne',
                      'bday': 12,
                      'host': 'carbon',
                      'year': 3,
                      'gecos': 'new associate',
                      'byear': 2017,
                      'bmonth': 2,
                      'passwd': 'e1NTSEF9WlBURGtJdmZJSld0WUlrak9zdGxscXYySTRRVEhBYj=',
                      'newbie': False,
                      'course': 'CPSSD',
                      'created': '2010-09-06 11:69:69',
                      'altmail': 'associateOne@example.dcu.ie',
                      'updated': '2015-09-28 01:42:21',
                      'birthday': '09 07 1732',
                      'usertype': 'associate',
                      'updatedby': 'admin',
                      'uidNumber': 102009,
                      'createdby': 'admin',
                      'gidNumber': 1019,
                      'yearsPaid': 1,
                      'loginShell': '/usr/local/shells/bash',
                      'objectClass': ['redbrick', 'posixAccount', 'top', 'shadowAccount'],
                      'oldusertype': 'member',
                      'userPassword': 'e1NTSEF9WlBURGtJdmZJSld0WUlrak9zdGxscXYySTRRVEhj=',
                      'homeDirectory': '/home/redbrick/associateOne',
                      'disuser_period': 0,
                      'shadowLastChange': 17064, }
ASSOCIATE_ONE_OUTPUT = \
    'cn                :  Associate One\n' + \
    'id                :  15358478\n' + \
    'uid               :  associateOne\n' + \
    'bday              :  12\n' + \
    'host              :  carbon\n' + \
    'year              :  3\n' + \
    'byear             :  2017\n' + \
    'gecos             :  new associate\n' + \
    'bmonth            :  2\n' + \
    'course            :  CPSSD\n' + \
    'newbie            :  False\n' + \
    'passwd            :  e1NTSEF9WlBURGtJdmZJSld0WUlrak9zdGxscXYySTRRVEhBYj=\n' + \
    'altmail           :  associateOne@example.dcu.ie\n' + \
    'created           :  2010-09-06 11:69:69\n' + \
    'updated           :  2015-09-28 01:42:21\n' + \
    'birthday          :  09 07 1732\n' + \
    'usertype          :  associate\n' + \
    'createdby         :  admin\n' + \
    'gidNumber         :  1019\n' + \
    'uidNumber         :  102009\n' + \
    'updatedby         :  admin\n' + \
    'yearsPaid         :  1\n' + \
    'loginShell        :  /usr/local/shells/bash\n' + \
    'objectClass       :  [\'redbrick\', \'posixAccount\', \'top\', ' + \
    '\'shadowAccount\']\n' + \
    'oldusertype       :  member\n' + \
    'userPassword      :  e1NTSEF9WlBURGtJdmZJSld0WUlrak9zdGxscXYySTRRVEhj=\n' + \
    'homeDirectory     :  /home/redbrick/associateOne\n' + \
    'disuser_period    :  0\n' + \
    'shadowLastChange  :  17064\n'
