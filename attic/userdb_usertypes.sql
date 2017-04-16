-- $Id$

CREATE TABLE "usertypes" (
	usertype	VARCHAR(8)    PRIMARY KEY
);

GRANT ALL ON usertypes TO root;

INSERT INTO "usertypes" VALUES ('reserved');
INSERT INTO "usertypes" VALUES ('system');
INSERT INTO "usertypes" VALUES ('founders');
INSERT INTO "usertypes" VALUES ('member');
INSERT INTO "usertypes" VALUES ('associat');
INSERT INTO "usertypes" VALUES ('club');
INSERT INTO "usertypes" VALUES ('society');
INSERT INTO "usertypes" VALUES ('intersoc');
INSERT INTO "usertypes" VALUES ('projects');
INSERT INTO "usertypes" VALUES ('redbrick');
INSERT INTO "usertypes" VALUES ('guest');
INSERT INTO "usertypes" VALUES ('staff');
INSERT INTO "usertypes" VALUES ('dcu');
