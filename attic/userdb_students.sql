-- $Id$

CREATE TABLE "students" (
	id	 	INT       PRIMARY KEY,
	name 		VARCHAR   NOT NULL,
	email	 	VARCHAR   NOT NULL,
	course 		VARCHAR   NOT NULL,
	year 		VARCHAR   NOT NULL
);

GRANT ALL ON students TO root;
