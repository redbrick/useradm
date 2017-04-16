#!/bin/bash

noobs=`/srv/admin/scripts/rrs/useradm list_newbies`

for noob in $noobs; do
	echo $noob@redbrick.dcu.ie >> noob_list.txt
done
