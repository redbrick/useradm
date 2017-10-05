#! /bin/bash

HOST=atlas.dcu.ie
ATTRS="dn cn sn givenName gecos mail l objectClass"
TREES="students staff alumni"
OUTPUT=rb-dcu-tree.ldif

for i in $TREES; do
  echo "Getting $i..."
  ldapsearch -LLL -x -h $HOST -b ou="$i",o=dcu objectClass=person "$ATTRS" > "$i"
done

echo "Generating $OUTPUT"

(cat << EOF
dn: ou=dcu,o=redbrick
ou: dcu
objectClass: organizationalUnit
objectClass: top
structuralObjectClass: organizationalUnit

dn: ou=Students,ou=dcu,o=redbrick
ou: Students
objectClass: organizationalUnit
objectClass: top
structuralObjectClass: organizationalUnit

dn: ou=Alumni,ou=dcu,o=redbrick
ou: Alumni
objectClass: organizationalUnit
objectClass: top
structuralObjectClass: organizationalUnit

dn: ou=Staff,ou=dcu,o=redbrick
ou: Staff
objectClass: organizationalUnit
objectClass: top
structuralObjectClass: organizationalUnit

EOF
./fixup-rb-dcu-tree.py < "$TREES") > $OUTPUT
