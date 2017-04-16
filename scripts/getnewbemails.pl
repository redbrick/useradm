#!/usr/bin/perl
use warnings;
use strict;

open NEWBS,"newbies";
my @newbies = <NEWBS>;
close NEWBS;

foreach(@newbies) {
	chomp;
	my $altmail_line = `/local/admin/scripts/rrs/useradm show $_ | grep altmail`;
	$altmail_line =~ m/altmail:\s(\S*?)\n/igs;
	print $1. "\n";
}

