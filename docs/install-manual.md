# Installation Manual: RedBrick Registration System

*Cillian Sharkey, CASE3, 50716197*

1. Introduction
2. Pre-requisites
    - Requirements for all setups
    - Requirements for main setup
    - Requirements for web setup
3. Installation
    - Installing software
    - Setting up database
4. Configuration
	

## Introduction

There are essentially two kinds of setups for RRS:
	
        1. Main setup - this is the setup of the machine where the user
	database and accounts permanently reside. There is at a minimum, full
	use of `useradm` for both database and account
	administration.
	
	2. Web setup - this is the machine used for hosting the clubs &amp;
	societies day system. Full use of the `rrs` cgi for database
	administration and limited use of useradm for database only
	administration.


Note that the web setup could also be used on the main setup, so that full use
of `useradm` and the `rrs` cgi would be available.

The installation requirements and steps below will indicate if they only
pertain to one of the given setups ('main' or 'web') above, otherwise it can be
assumed that they are required for both types of setup.

It is also worth noting that much of RRS is very specific to the RedBrick
and DCU environment and so as such is not designed for widespread use on
generic machines. The web setup mentioned above however, is not as specific in
its requirements and is intended to be reasonably 'portable'.

## Pre-requisites

### Requirements for all setups

#### Platform

RRS is designed primarily to run on a Unix platform however, it should be
possible to run the web interface part on a non-Unix platform although this has
not been tested. Note that root (superuser) access is required for performing
any account or filesystem operations with `useradm`, everything else
can be performed using a user / unprivileged account (assuming it has access to
the user database).

#### PostgresSQL

PostgresSQL version 7.2 or higher must be installed. Details on doing this vary
depending on the operating system and is outside the scope of this document
however, full instructions can be found on the
PostgresSQL website.

#### Python

Python version 2.2 or higher must be installed. Details on doing this vary
depending on the operating system and is outside the scope of this document
however, full instructions can be found on the
Python website.

The following Python modules are included in the standard Python release,
but may need to be installed or configured to work:

	* readline - provides command line editing and completion functionality for useradm. Requires GNU readline to be installed.

The following additional 3rd party Python modules must be installed:

	1. [PyGresSQl](http://www.druid.net/pygresql/) - Python
	interface to PostgresSQL database. Note that this is actually included
	in the PostgresSQL database release, however ensure that version 3.2 or
	later is installed.
	
	2. [Python-LDAP](http://python-ldap.sourceforge.net/)- a
	Python interface to LDAP. Requires
	[OpenLDAP](http://www.openldap.org) to be installed.
	Tested with Python-LDAP version 1.10alpha3 and OpenLDAP 1.2.13. This
	module is currently only used by
	<a href=rebuild_userdb_students.html>rebuild_userdb_student</a> and the
	<a href=rebuild_userdb_staff.html>rebuild_userdb_staff</a> scripts.

### Requirements for main setup

#### Account utilities

The account utilities `useradd`, `usermod` and
`userdel` need to be installed. Typically, these are provided as
part of the native operating system and have been found to have a consistent
interface on Solaris, Linux and NetBSD.

#### Setquota

The 3rd party utility `setquota` must be installed for the
manipulation of disk quotas. There appear to be a number of implementations of
this command each with different command line syntax for different operating
systems. Tested with a setquota utility for Solaris written by David Mitchell
of Dept of Computer Science, Sheffield University.

#### Mailman

RRS automatically subscribes (and unsubscribes) users to a variety of
RedBrick mailing lists, specifically the announce-redbrick,
redbrick-newsletter, comittee, rb-admins and admin-discuss lists. For this
reason the mailing list software [Mailman](http://www.list.org) should be installed with the above mentioned lists created and working. It is
not entirely necessary however as "dummy" scripts can be used in place of the
`add_members` and `remove_members` mailman commands.

#### Mail Transfer Agent

Any MTA that provides the generic `sendmail` command line
interface will suffice, e.g. Exim, Postfix, Sendmail, etc.

### Requirements for web setup

#### Apache

A web server is required for the `rrs` cgi. Web servers other
than Apache should work as the CGI standard is web server independant. Tested
against Apache 1.3.26.

## Installation

### Installing software

The installation of RRS simply involves unpacking the RRS distribution tarball in a filesystem location
of your choosing. Say you have downloaded the tarball to
`/tmp/rrs.tar.gz`. Installation to the directory
`/usr/local/rrs` is as follows:

```
# cd /usr/local
# tar zxf /tmp/rrs.tar.gz
```

### Setting up database

A database `userdb` needs to be created with the postgres command
"`createdb userdb`" run as the postgres user. For the account setup,
the root user will need access to the database. For the web setup, the user the
web server runs as will need access to the database. This is achieved by first
creating the users if they don't already exist with the postgres
`createuser` command and making sure that postgres is setup to grant
access to the `userdb` database for these users by appropriate
editing of the `pg_hba.conf` and possibly `pg_ident.conf`
files.

#### Creating database [main setup]

This step sets up a new database from scratch.

Create the tables for the database:

```bash
main$ cat userdb_reserved.sql userdb_staff.sql userdb_students.sql \
userdb_usertypes.sql userdb_users.sql | psql userdb
```

Make sure that access to these tables is granted to all users who need it.
The above scripts include full access for root and SELECT (read only) access
for users `www` and `webgroup` as this is the default
used on the RedBrick system.

Then populate the student, staff and reserved tables by running each of the
rebuild scripts, e.g:

```
main$ ./rebuild_userdb_reserved
userdb/reserved: Purge. Populate. Done [45]
main$ ./rebuild_userdb_students
userdb/students: Search [19523]. Purge. Populate. Done [19436/19523].
main$ ./rebuild_userdb_staff
userdb/staff: Search [1829]. Purge. Populate. Done [397/1829].
```


#### Creating database [web setup]

If the web setup is on a seperate machine to the main system machine, the
database must be copied across. This can be achieved as follows:

```
main$ pg_dump -f userdb.dump userdb
[copy file userdb.dump to the web machine]
web$ psql userdb &; userdb.dump
```

You will need to grant full access to the users table to the user the web
server runs as. The "`GRANT ALL ON users TO username`" SQL command
achieves this when run as the owner of the userdb.

An empty `rrs.log` file needs to be created before any actions
can be performed with the web interface. This can be achieved by:

```
[create rrs.log in directory that rrs is installed]*
web$ touch rrs.log
[make sure web server user can write to file]
web$ chown www rrs.log
```

## Configuration

Local configuration can be performed by editing the rbconfig.py file. The majority of this configuration
file is for providing local account and filesystem location paths to the rbaccount module. The defaults provided are of
course suited for the RedBrick system.

At this point, all necessary installation and configuration should be
complete for use of RRS.

$Id: install-manual.html,v 1.1 2003/03/28 16:33:07 cns Exp $
