#!/bin/sh
#
# Dump databases to committee folder.
#
# $Id: update_userdb_dumps.sh,v 1.4 2002/02/16 21:50:54 cns Exp cns $
#

OUT=/local/committee/userdb
PSQL="/usr/local/pgsql/bin/psql -h localhost -d userdb"
PG_DUMP="/usr/local/pgsql/bin/pg_dump -h localhost -d userdb"
USERDB_BACKUP="/local/admin/scripts/users/backup-of-userdb.dump"

printf "$OUT dumps: "

# Dump each database and keep a copy of yesterday's database
# (for doing comparisons/diffs).
#
for i in users students reserved; do
	$PSQL -c "select * from $i" > $OUT/$i.new
	
	# Only rotate them if there was no error from psql
	# and a non-empty dump was generated.
	#
	if [ $? -eq 0 -a -s $OUT/$i.new ]; then
		printf "$i "
		mv $OUT/$i $OUT/$i.yesterday
		mv $OUT/$i.new $OUT/$i
	else
		printf "$i (FAILED) "
		rm -f $OUT/$i.new
	fi
done

echo "Done."

# Make sure committee can read 'em.
#
chmod 640 $OUT/*
chgrp committe $OUT/*

printf "Full dump: "

$PG_DUMP > $USERDB_BACKUP

echo "Done."
