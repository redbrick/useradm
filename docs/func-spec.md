# Functional Specification: RedBrick Registration System

*Cillian Sharkey, CASE3, 50716197*

1. Introduction
    - Scope and purpose of this document
2. Overview of project
    - Background
    - Users
    - Objectives
    - Constraints
3. Functional and data description
    - System architecture
    - User data
    - Software and Hardware Boundaries
4. Projected schedule
5. References

## Introduction

### Scope and purpose of this document
	
This document is a functional specification for my 3<sup>rd</sup> year
project: a user registration and administration system for use by the DCU
Networking Society ([Redbrick](http://www.redbrick.dcu.ie)). It
will attempt to describe the functional aspects of the project: its
objectives, constraints, system architecture, and functional data description
so that there is enough information for the actual implementation of the
project.

## Overview of project

### Background

There are just over 1,800 accounts on the RedBrick UNIX system and so the
administration of user accounts forms a large part of the system
administrators' workload. As one of the system administrators for RedBrick
myself, I have first hand experience of the amount of work required in
administrating user accounts and dealing with account requests on an often
daily basis. In addition to this, each year at the clubs &amp; societies day
the registration of new and renewal of existing users takes place. Hundreds
of users are processed on a small isolated network of computers. The goal of
this project is to reduce the workload of system administrators and ease the
administration and registration of users both on a daily basis and for the annual
clubs and societies day.

### Users

The users of the system will be restricted to the system administrators
for day to day user administration as it requires root (superuser) access, however
for registration on clubs &amp; societies day it is usual for other members of the
society committee to help out.

### Objectives

* Provide an automated and consistent (UNIX command line) interface
for performing both common day-to-day and occassional "batch" user
administration operations on the actual accounts (home directories,
mail spools, disk quotas etc.), the UNIX `/etc/passwd`
"database" and the user database ensuring that all are kept in sync.
Single user account operations would include:
    * adding new accounts,
    * deleting existing accounts,
    * renaming existing accounts,
    * converting existing accounts "usertype",
    * renewing existing accounts,
    * reseting accounts with new random password (and emailing password to user)
    * retrieving account information for display,
    * checking the availability of usernames for new accounts,
* Batch account operations would include:
    * emailing renewal reminders to non-renewed accounts
    * expiring non-renewed accounts (i.e. disabling login shell)
    * deleting non-renewed accounts after a grace period
    * checking for inconsistencies between the user database and the UNIX `/etc/passwd` database
    * interactive update of the user database from the latest copy of the public DCU student database
* Provide a web interface to offer a similar set of single user administration operations for use on the clubs &amp; societies day. The setup is generally that of a small number of networked computers that are isolated from the RedBrick servers so changes would be made to a local (seperate) copy of the user database and at the end of the day all of these changes (i.e. new, renewed, renamed, converted, etc. accounts) must be detected and	synchronised with the actual accounts and UNIX `/etc/passwd` database on the system. This needs to be done in batch as hundreds of accounts are processed on clubs &amp; societies day. This would be implemented as one of the command line interface's batch operations.
* Prevent username conflicts with other namespaces on the system e.g. email aliases, mailing lists.

### Constraints

* All accounts must have a name (or description) and an alternate
	email address for contact purposes (and as such all UNIX accounts must
	have a corresponding entry in the user database).

* Users may only have one account on the system (i.e. one student ID
	per account).
	
* Member, staff and associate accounts must have a valid DCU
	student/staff ID associated with them.

* Usernames will be limited to what the underlying UNIX OS supports
	in terms of acceptable characters, length etc.

## Functional and data description

### System architecture

The system will be 3 tier in nature:

**Front end**

There will be two client applications: a CGI web interface (primarily for
use on the annual clubs &amp; societies day to register new members and renew
existing members) and a UNIX command line interface for day-to-day user
administration.

**Middle end**

There will be two modules which the two client applications (and any
potential future applications) will use. One will be for performing database
operations (RBUserDB) and the other for UNIX account operations (RBAccount).
The web interface will not make use of the UNIX account module however, as it
operates on the database only.

**Back end**

Database (likely to be PostgreSQL) which will contain tables for the actual
user database and associated information, e.g. local copy of the public DCU
student database, table of valid usertypes, additional reserved usernames,
etc. Will also contain copies of user database from previous years for
reference/archival purposes.

### User data

The traditional UNIX `/etc/passwd` database doesn't contain
enough information for user accounts for RedBrick's needs (nor does it support
complex queries that a database can) hence the need for a user database. The
following additional information will be kept for all UNIX accounts:

<dt>Username</dt>

<dd>Unique UNIX username.<dd>

<dt>Name/Description</dt>

<dd>User's full name or a description for non-user accounts (e.g.
project/system accounts).</dd>

<dt>Usertype</dt>

<dd>Corresponds to both UNIX group and type of user. The following usertypes
will be used: member, staff, associate, project, club, society, committee,
project, guest, system, reserved.</dd>

<dt>Email</dt>

<dd>Alternate contact address (typically DCU email address).</dd>

<dt>Student ID</dt>

<dd>DCU student (or staff) ID number, compulsory for member, staff and
associates.</dd>

<dt>Years paid</dt>

<dd>Number of years paid. (Non-renewed accounts will be zero).</dd>

<dt>Updated by</dt>

<dd>Username of the administrator who last updated the database entry.</dd>

<dt>Updated at</dt>

<dd>Date &amp; time of when the database entry was last updated.</dd>

<dt>Created by</dt>

<dd>Username of the administrator who first created the account.</dd>

<dt>Created at</dt>

<dd>Date &amp; time of when the database entry was first created.</dd>

### Software and Hardware Boundaries

The project will use the OS native command line tools for performing all
UNIX `/etc/passwd` operations and the majority of account
operations. The 3rd party utility `setquota` will be used for
the modification of disk quotas. DCU student information will be retrieved
from the publically accessible LDAP service on `atlas.dcu.ie`.

## Projected schedule

<dt>Week 1</dt>

<dd>Design database (SQL schema &amp; populating with sample data). Code
middle end database module (addition, retrieval and updation of user
information, user data checking functions).</dd>

<dt>Week 2</dt>

<dd>Code middle end account module (interaction with UNIX account utilities
&amp; filesystem manipulation of user accounts).</dd>

<dt>Week 3</dt>

<dd>Code command line interface (single user operations) in parallel with
'unit testing' of the various database and account module functions.</dd>

<dt>Week 4</dt>

<dd>Code web interface.</dd>

<dt>Week 5</dt>

<dd>Work on batch operations.</dd>

<dt>Week 6</dt>

<dd>Final testing. Write up documentation: Technical manual, User manual,
Installation manual.</dd>

## References

### UNIX (Solaris) user administration tool manpages


$Id: func-spec.html,v 1.1 2003/03/28 16:33:07 cns Exp $
