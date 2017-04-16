-- $Id$

CREATE TABLE "staff" (
	id 		INT       PRIMARY KEY,
	name 		VARCHAR   NOT NULL,
	email	 	VARCHAR   NOT NULL
);

GRANT ALL ON staff TO root;
