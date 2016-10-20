# Useradm
### Modular Python User Management Tool

Useradm is used to manage Redbrick's membership.

## Functions
### New User Creation

1. Queries DCU's AD server for User information;
	- Fullname
	- Student ID
	- DCU altmail
	- Course of Study
	- Year of Study.
2. Asks user for nickname, queries if nick exists in Redbrick LDAP.

3. If the user doesn't exist.
	- Creates the user's homedir
	- populates .forward with altmail address
	- assigns quotas.
	- *broken* adds the user to the announce-redbrick mailman list
	- mails user's password and account details.

### Renew User

