-- $Id$

CREATE TABLE "reserved" (
	username	VARCHAR(8) NOT NULL PRIMARY KEY,
	info	 	VARCHAR    NOT NULL
);

GRANT ALL ON reserved TO root;
GRANT SELECT ON users TO webgroup;
GRANT SELECT ON users TO www;
