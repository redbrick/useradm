## This tool is under heavy construction
### There is no guarantee it is working but work is commencing on it

# Useradm

[![CircleCI](https://circleci.com/gh/redbrick/useradm.svg?style=shield)](https://circleci.com/gh/redbrick/useradm)
[![Code Climate](https://codeclimate.com/github/redbrick/useradm/badges/gpa.svg)](https://codeclimate.com/github/redbrick/useradm)

### Modular Python User Management Tool

Useradm is used to manage Redbrick's membership.

## Testing RRS

To test rrs run

```
python server.py
```

Then open [localhost:8000/rrs.cgi](http://localhost:8000/rrs.cgi)

## Functions

### New User Creation

1. Queries DCU's AD server for User information:
	- Fullname
	- Student ID
	- DCU altmail
	- Course of Study
	- Year of Study.
2. Asks user for nickname, queries if nick exists in Redbrick LDAP.

3. If the user doesn't exist.
	- [x] Creates the user's homedir
	- [x] Populates .forward with altmail address
	- [x] Assigns quotas.
	- [ ] Adds the user to the announce-redbrick mailman list
	- [x] Mails user's password and account details.

### Renew User

1. [x] Queries RB LDAP using user nickname.
2. [x] Set yearsPaid=1 Set yeats paid to 1 if less than 1
3. [x] Reset user shell from `/usr/local/shell/expired` back to previous user's shell
4. [ ] Restores the correct user type before expiration (committee/associate)

## Installation Manual:

Cillian Sharkey, CASE3, 50716197

1. [Introduction](#introduction)
2. [Pre-requisites](#pre-requisites)
   1. Requirements for all setups
   2. Requirements for main setup
   3. Requirements for web setup
3. [Installation](#installation)
   1. Installing software
   2. Setting up database
4. [Configuration](#configuration)

### Introduction

There are essentially two kinds of setups for RRS:
- Main setup - this is the setup of the machine where the user database and
  accounts permanently reside. There is at a minimum, full use of useradm for
	both database and account administration.
- Web setup - this is the machine used for hosting the clubs & societies day
  system. Full use of the rrs cgi for database administration and limited use of
	useradm for database only administration.

Note that the web setup could also be used on the main setup, so that full use
of useradm and the rrs cgi would be available.

The installation requirements and steps below will indicate if they only pertain
to one of the given setups ('main' or 'web') above, otherwise it can be assumed
that they are required for both types of setup.

It is also worth noting that much of RRS is very specific to the RedBrick and
DCU environment and so as such is not designed for widespread use on generic
machines. The web setup mentioned above however, is not as specific in its
requirements and is intended to be reasonably 'portable'.

### Pre-requisites

#### Requirements for all setups

##### Platform

RRS is designed primarily to run on a Unix platform however, it should be
possible to run the web interface part on a non-Unix platform although this has
not been tested. Note that root (superuser) access is required for performing
any account or filesystem operations with useradm, everything else can be
performed using a user / unprivileged account (assuming it has access to the
user database).

##### PostgresSQL

PostgresSQL version 7.2 or higher must be installed. Details on doing this vary
depending on the operating system and is outside the scope of this document
however, full instructions can be found on the PostgresSQL website.

##### Python

Python version 3 or higher must be installed. Details on doing this vary
depending on the operating system and is outside the scope of this document
however, full instructions can be found on the Python website.

The following Python modules are included in the standard Python release, but
may need to be installed or configured to work:

* `readline` - provides command line editing and completion functionality for
  useradm. Requires GNU readline to be installed.

The following additional 3rd party Python modules must be installed:

* `PyGresSQL` - Python interface to PostgresSQL database. Note that this is
  actually included in the PostgresSQL database release, however ensure that
	version 3.2 or later is installed.
* `pyldap` - a Python interface to LDAP, and a fork of python-ldap.
   OpenLDAP > 2.4 is required.
   This module is currently only used by rebuild_userdb_student and the 
   rebuild_userdb_staff scripts.

#### Requirements for main setup

##### Account utilities

The account utilities useradd, usermod and userdel need to be installed.
Typically, these are provided as part of the native operating system and have
been found to have a consistent interface on Solaris, Linux and NetBSD.

##### Setquota

The 3rd party utility setquota must be installed for the manipulation of disk
quotas. There appear to be a number of implementations of this command each with
different command line syntax for different operating systems. Tested with a
setquota utility for Solaris written by David Mitchell of Dept of Computer
Science, Sheffield University.

##### Mailman

RRS automatically subscribes (and unsubscribes) users to a variety of RedBrick
mailing lists, specifically the `announce-redbrick`, `redbrick-newsletter`,
`comittee`, `rb-admins` and `admin-discuss` lists. For this reason the mailing
list software Mailman should be installed with the above mentioned lists created
and working. It is not entirely necessary however as "dummy" scripts can be used
in place of the `add_members` and `remove_members` mailman commands.

##### Mail Transfer Agent

Any MTA that provides the generic sendmail command line interface will suffice,
e.g. Exim, Postfix, Sendmail, etc.

#### Requirements for web setup

##### Apache

A web server is required for the rrs cgi. Web servers other than Apache should
work as the CGI standard is web server independant. Tested against Apache
1.3.26.

### Installation

#### Installing software

The installation of RRS simply involves unpacking the RRS distribution tarball
in a filesystem location of your choosing. Say you have downloaded the tarball
to `/tmp/rrs.tar.gz`. Installation to the directory `/usr/local/rrs` is as
follows:

```
cd /usr/local
tar zxf /tmp/rrs.tar.gz
```

#### Setting up database

A database userdb needs to be created with the postgres command
"createdb userdb" run as the postgres user. For the account setup, the root user
will need access to the database. For the web setup, the user the web server
runs as will need access to the database. This is achieved by first creating the
users if they don't already exist with the postgres createuser command and
making sure that postgres is setup to grant access to the userdb database for
these users by appropriate editing of the pg_hba.conf and possibly
`pg_ident.conf` files.

#### Creating database [main setup]

This step sets up a new database from scratch.

Create the tables for the database:

```
cat userdb_reserved.sql userdb_staff.sql userdb_students.sql \
userdb_usertypes.sql userdb_users.sql | psql userdb
  ```

Make sure that access to these tables is granted to all users who need it. The
above scripts include full access for root and SELECT (read only) access for
users `www` and `webgroup` as this is the default used on the RedBrick system.

Then populate the student, staff and reserved tables by running each of the
rebuild scripts, e.g:

```shell
$ ./rebuild_userdb_reserved
userdb/reserved: Purge. Populate. Done [45]
$ ./rebuild_userdb_students
userdb/students: Search [19523]. Purge. Populate. Done [19436/19523].
$ ./rebuild_userdb_staff
userdb/staff: Search [1829]. Purge. Populate. Done [397/1829].
```

#### Creating database [web setup]

If the web setup is on a seperate machine to the main system machine, the
database must be copied across. This can be achieved as follows:

```
pg_dump -f userdb.dump userdb
```

copy file `userdb.dump` to the web machine

```
psql userdb < userdb.dump
```

You will need to grant full access to the users table to the user the web server
runs as. The `GRANT ALL ON users TO <username>` SQL command achieves this when
run as the owner of the userdb.

An empty `rrs.log` file needs to be created before any actions can be performed
with the web interface. This can be achieved by creating `rrs.log` in a
directory that `rrs` is installed and making sure the web server user can write
to that file:

```
touch rrs.log
chown www rrs.log
```

### Configuration

Local configuration can be performed by editing the `rbconfig.py` file. The
majority of this configuration file is for providing local account and
filesystem location paths to the `rbaccount` module. The defaults provided are
of course suited for the RedBrick system.

At this point, all necessary installation and configuration should be complete
for use of RRS.


### Contribution

Our [open issues](https://github.com/redbrick/useradm/issues) can be found [here](https://github.com/redbrick/useradm/issues)!
