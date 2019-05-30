# User Manual: RedBrick Registration System

*Cillian Sharkey, CASE3, 50716197*

1. Using useradm
	* Running useradm
	* Using useradm
	* Common command line options
2. Using rrs web interface
	* card - card reader interface
	* add - Add new user
	* delete - Delete user
	* renew - Renew user
	* update - Update user
	* rename - Rename user
	* convert - Convert user to new usertype
	* show - Show user information
	* freename - Check if a username is free
	* search - Search user and DCU databases
	* stats - Database statistics
	* log - Log of all actions

## Using useradm

### Running useradm

For performing any account operations, `useradm` must be run as
root (superuser). For accessing only database information, an unprivilged user
account (that has been granted access to the database) can be used. All
examples below assume running as root on the main server where both accounts
and user database live.

The `useradm` script can be run from anywhere, as long as it is
in the same directory as the rest of the rrs distribution. Say rrs is installed
in `/usr/local/rrs`. It could be run as follows:

```
main# <b>/usr/local/rrs/useradm</b>
Usage: useradm command [options]
'useradm -h' for more info on available commands
```
 
*[OR]*

```
main# <b>cd /usr/local/rrs</b>
main# <b>./useradm</b>
Usage: useradm command [options]
'useradm -h' for more info on available commands
```

"`useradm -h`" gives a full listing of all commands available. For
full usage and command line options for a given command, use "`useradm
command -h`" e.g:

```
main# <b>./useradm -h</b>
Usage: useradm command [options]
Single user commands:
  add                  Add new user
  delete               Delete user
  renew                Renew user
  update               Update user
  rename               Rename user
  convert              Change user to a different usertype
Single account commands:
  resetpw              Set new random password and mail it to user
  resetsh              Reset user's shell
  disuser              Disuser a user
  reuser               Re-user a user
Single user information commands:
  show                 Show user details
  freename             Check if a username is free
Interactive batch commands:
  search               Search user and dcu databases
  sync                 Synchronise accounts with userdb (for RRS)
  sync_dcu_info        Interactive update of userdb using dcu database info
Batch commands:
  newyear              Prepare database for start of new academic year
  unpaid_warn          Warn (mail) all non-renewed users
  unpaid_disable       Disable all normal non-renewed users
  unpaid_delete        Delete all grace non-renewed users
Batch information commands
  newbies_list         List all paid newbies
  renewals_list        List all paid renewals (non-newbie)
  freename_list        List all usernames that are taken
  unpaid_list          List all non-renewed users
  unpaid_list_normal   List all normal non-renewed users
  unpaid_list_reset    List all normal non-renewed users with reset shells
  unpaid_list_grace    List all grace non-renewed users
Miscellaneous commands:
  checkdb              Check database for inconsistencies
  stats                Show database and account statistics
'useradm command -h' for more info on a command's options &amp; usage.
main# <b>./useradm add -h</b>
Add new user
Usage: useradm add [options] [username]
 -h                Display this usage
 -T                Test mode, show what would be done
 -d                Perform database operations only
 -a                Perform unix account operations only
 -u username       Unix username of who updated this user
 -f                Set newbie (fresher) to true
 -F                Opposite of -f
 -m                Send account details to user's alternate email address
 -M                Opposite of -m
 -o                Override warning errors
 -p                Set new random password
 -P                Opposite of -p
 -t usertype       Type of account
 -n name           Real name or account description
 -e email          Alternative email address
 -i id             Student/Staff ID
 -c course         DCU course (abbreviation)
 -y year           DCU year
 -s years          paid Number of years paid (subscription)
 -b birthday       Birthday (format YYYY-MM-DD)
```

While useradm is primarily designed for user interaction, all required user
input can be provided on the command line by the use of options and
arguments as shown above.

### Using useradm

The basic operation involves the prompting of the user for information. Examples
of the prompt follow:

```
Enter usertype
(hints) [member] &gt;&gt; 

Enter new username
[no default] &gt;&gt; 

Enter birthday as 'YYYY-MM-DD'
(optional) [1982-06-20] &gt;&gt;
```

The prompt has the following features:


* Line editing (provided by readline) - this allows for easy editing
of data at the prompt and provides a history of previously input data
that is accessible by using the up and down arrow keys.

* Default answer - if a default answer is provided, it is shown in
square brackets `[like this]`. To accept the default, simply
hit `RETURN`. If no default is provided it will be shown as
`[no default]`. In this case hitting `RETURN` is
equivalent to giving an empty answer.

* Optional questions - indicated by "`(optional)`" beside
the prompt. Giving an empty answer is taken as not answering the
question. If however, a default answer is provided and you want to give
an empty answer, you must use the End Of File (`EOF`)
control sequence (instead of `RETURN` which will give the
default answer). `EOF` is typically Control-D on UNIX
systems.

* Tab completion - if a default answer is provided or a set of hints
(indicated by "`(hints)`" beside the prompt) then pressing
`TAB` will cycle through all possible answers when no text
has been entered at the prompt. When some text has been entered and
`TAB` is pressed, it will only cycle through possible answers
that start with the given text.

* Error handling - if an error occurs during the input of user data
it will be displayed and the question will be asked again until correct
or valid input is provided. If however, the error is only a
`WARNING` and not `FATAL`, then the option to
override (i.e.  essentially "ignore") the error is provided. If you
answer No, you go back to the question prompt again. If you answer Yes,
you advance to the next question or step.  Answering yes also sets the
'override' option so any `WARNING` errors that occur when
action is performed after all user input is complete will also be
ignored (they will be displayed however).



### Common command line options

A number of command line options are common to all commands:

* `-T` test mode. This runs through all user input and
questions but it does not perform any actions. Rather, it prints out
exactly what would be done. Any SQL INSERTs, UPDATEs or DELETEs that
would be sent to the database, what local commands (and their
arguments) would be executed (and any input that would be given to
them) the contents of any email messages that would be sent, etc. This
is extremely handy if you are unsure as to what a command will do or if
you just want to be careful before performing any of the batch
operations, like `unpaid_delete` or `sync` for
example.

* `-d` database only mode. This ensures that only database
actions will be performed. This is especially useful when using useradm
with the web setup where the local accounts don't exist. It is also
useful for making changes to the database so that is up to date with
the corresponding account(s) if they are out of sync.

* `-a` account only mode. This ensures that only account
actions will be performed. This is especially useful if for example
a database &amp; account operation failed on the account operation and
needed to be completed later after fixing the source of the problem. An
example of this is a `rename` or a `convert` of a
user who was currently logged in at the time. In this case the database
operation would complete succesfully however the account operation which
uses `usermod` would fail as it would not operate on a
currently logged-in user. Note that this was only apparent with the Solaris
implementation of the command. Other uses would be to operate on an account
that does not exist in the database for whatever reasons.


## Using rrs web interface

The web interface is designed to be rather intuitive and easy to use. The
top of the page contains a menu with the following commands available:

### card - card reader interface

This is designed to be the main interface when using rrs. The card ID input
field is automatically focused on page load so it is ready to accept input from
either a magnetic card reader, barcode scanner or plain user input.

If the given DCU ID number is already in the database it will present the
user renewal form with the users' current details along with any updated
details from the DCU databases (e.g. course and year will change for students,
or an invalid email address may have been fixed, etc.). If the user has already
paid however, it will issue a warning message and remain on the card reader
page. This is prevents users accidentally paying again for an already paid
account. The new username input field is automatically focused to allow for
quick entry of the user's preferred choice of new username (if any). Typically
nothing needs to be changed so simply pressing `RETURN` is enough to
renew the user after checking that their user details are correct.

Otherwise it must be a new user so details are loaded in from the DCU
databases along with reasonable default values (e.g. years paid will be 1). The
username input field will be automatically focused to allow for quick entry of
the user's preferred choice of username.

### add	- Add new user

A more 'manual' approach to adding new users. It provides a blank form for
adding a new user. Leaving out details and submitting the form will fill in any
missing information if possible until there is enough information to add the
user succesfully.

### delete - Delete user

Simply deletes user from database. Note that in reality it should be very
rare for anyone to request an account deletion but the feature is provided just
in case.

### renew - Renew user

A more 'manual' approach to renewing users. It provides a blank form for
renewing a new user. Leaving out details and submitting the form will fill in
any missing information if possible until there is enough information to renew
the user succesfully.

### update - Update user

Similar to the renewal form except only the users' current database
information is displayed for easy modification. No new information from the DCU
databases or defaults are provided so an update of a user without changing any
of the input fields has no visible change of the users' information other than
the updating of the `updated_by` and `updated_at`
attributes.

### rename - Rename user

Simply changes a user's username. Note that currently the old username
becomes available as soon as it is renamed.

### convert - Convert user to new usertype

Note that only conversions for "paying" usertypes are supported.

### show - Show user information

Shows database information for given username.

### freename - Check if a username is free

Simply checks for a free new username.

### search - Search user and DCU databases

Allows for searching by username, name or ID number. Note that the SQL
wildcard characters '_' for a single character and '%' for any number of
characters can be used. Any student or staff entries that have a RedBrick
account (i.e. a datbase entry with the *same* DCU ID number) will appear
with a 'show' button so that their database entry can be displayed quickly and
easily.

### stats - Database statistics

Simply displays database statistics.

### log	- Log of all actions

Shows a detailed log of all user actions that were performed and all user
input that was given including a time stamp.

$Id: user-manual.html,v 1.1 2003/03/28 16:39:08 cns Exp $
