#!/usr/bin/perl
use warnings;
use strict;

open USERLIST,"userlist";
my @users = <USERLIST>;
close USERLIST;

foreach my $user(@users) {
	chomp $user;
	my @info = `/local/admin/scripts/rrs/useradm show $user`;

	# get uidNumber
	my $uidNumber;
	foreach my $infoline(@info) {
		if($infoline =~ /uidNumber: (\d*)/) {
			$uidNumber = $1;
		}
	}
	print $uidNumber . "\n";
}

