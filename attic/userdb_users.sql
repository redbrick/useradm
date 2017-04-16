-- $Id$

CREATE TABLE "users" (
	username	VARCHAR(8)   PRIMARY KEY,
	usertype	VARCHAR      NOT NULL CONSTRAINT valid_usertype REFERENCES usertypes,
	name 		VARCHAR      NOT NULL CONSTRAINT require_name CHECK (name != ''),
	newbie		BOOLEAN      NOT NULL,
	email	 	VARCHAR      NOT NULL CONSTRAINT require_email CHECK (email != ''),

	id	 	INT 	     UNIQUE   CONSTRAINT require_id CHECK ((usertype != 'member' AND usertype != 'associat' AND usertype != 'staff') OR (id IS NOT NULL AND id > 0)),
	course 		VARCHAR               CONSTRAINT require_course CHECK (usertype != 'member' OR (course IS NOT NULL AND course != '')),
	year 		VARCHAR               CONSTRAINT require_year CHECK (usertype != 'member' OR year IS NOT NULL),
	years_paid	INT                   CONSTRAINT require_years_paid CHECK ((usertype != 'member' AND usertype != 'associat' AND usertype != 'staff') OR (years_paid IS NOT NULL)),

	created_by	VARCHAR(8)   NOT NULL CONSTRAINT require_created_by CHECK (created_by != ''),
	created_at 	TIMESTAMP(0) NOT NULL DEFAULT now(),
	updated_by	VARCHAR(8)   NOT NULL CONSTRAINT require_updated_by CHECK (updated_by != ''),
	updated_at 	TIMESTAMP(0) NOT NULL DEFAULT now(),

        -- Following are optional or non-essential additions
	birthday  	DATE
);

GRANT ALL ON users TO root;
GRANT SELECT ON users TO webgroup;
GRANT SELECT ON users TO www;

/*
 * Set updated_at to current time for each update
 */

CREATE FUNCTION users_updated_at_stamp () RETURNS OPAQUE AS '
	DECLARE
		curtime timestamp;
	BEGIN
		curtime = ''now'';
		NEW.updated_at := curtime;
		RETURN NEW;
	END;
' LANGUAGE 'plpgsql';
                                                                                        
CREATE TRIGGER users_updated_at BEFORE UPDATE ON users
	FOR EACH ROW EXECUTE PROCEDURE users_updated_at_stamp();

