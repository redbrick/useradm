#!/usr/bin/perl

# Perl Sucks The Proverbial Donkey Dick.

use POSIX;

$USERDB = "./users";
$AUTOFLUSH = 1;
$CLEAR = `clear`;
$LINE =  "===========================================\n";
$LOG = "./voters.log";
$COLORS = 1;

my %stats; 

print $CLEAR;
print "Redbrick voting system\n";
print $LINE;
print "Reading userdb...";
open(IN, $USERDB) or error("Could not open userdb");

my %users;
my %registered;

%usertypes = (100 => 'committe', 103 => 'member', 109 => 'staff', 107 => 'associat', 108 => 'guest');
$total = 0;
$user = "";
$usertype = "";
$yearsPaid = "";
$id = "";
$email = "";
$cn = "";

foreach $line (<IN>)
{
	if ($line =~ /^dn: uid=(.+),ou=accounts,o=redbrick/) {
		$user = $1;
		#print "\n$1|";
	} elsif ($line =~ /^\s*$/) {
		if ($user and $yearsPaid > 0 and ($usertype eq "member" or $usertype eq "staff" or $usertype eq "committe")) {
			$total++;
			#print "\n|$user|$yearsPaid|$id|$usertype|$cn|$email\n";
			my @tmp = ($user, $usertype, $cn, '', $email, $id, '', '', $yearsPaid);
			$users{$id} = \@tmp;
		}
		$user = "";
	} elsif ($user) {
		if ($line =~ /^gidNumber: (.+)$/) {
			#print "$1|";
			$usertype = $usertypes{$1} or "non-voter";
		} elsif ($line =~ /^yearsPaid: (.+)$/) {
			#print "$1|";
			$yearsPaid = $1;
		} elsif ($line =~ /^cn: (.+)$/) {
			#print "$1|";
			$cn = $1;
		} elsif ($line =~ /^id: (.+)$/) {
			#print "$1|";
			$id = $1;
		} elsif ($line =~ /^altmail: (.+)$/) {
			#print "$1|";
			$email = $1;
		}
	}
}

$quorom = ceil(sqrt($total)); 

close IN;
print "done\n";

if(-e $LOG)
{


	while(!($ans =~ /^[yY]/) and !($ans =~ /^[nN]/))
	{
		print "\nA voting log has been found, do you want to register all the voters\nfrom this log? [Y/N]: ";
		$ans = <STDIN>
	}

	if($ans =~ /^[yY]/)
	{
		readStatus();
	}
	else
	{
		system("rm $LOG") and warning("Could not remove voter log");
	}
}

do
{
	print "Please enter a student number/card-swipe/username: ";
	$input = <STDIN>;	
	chomp $input;
	print $CLEAR;

	
	if($input =~ /^\;\d{13}\?$/)
	{
		# Read the format the Redbrick Magreader produces
		$input = substr($input, 3, 8);
	}
	elsif(!($input =~ /^\d{8}$/))
	{
		# Read a username
		# Search database for the user
		
		foreach $key (keys %users)
		{
			if($users{$key}[0] eq "$input")
			{
				$input = $key;
				last;
			}
		}
	}
	
	# At this stage if I don't have the student number something bad
	# has happened
	
	if($input =~ /^\d{8}$/)
	{
		printDetails($input);
		checkEligibility($input);
		if(!exists($registered{$input}))
		{
			saveStatus($input);
			doStats($input);
		}
		else
		{
			warning("Duplicate entry");
		}
		
		printStats();
		$registered{"$input"} = 1;
	}
	else
	{
		warning("Invalid entry or entry not found");
		printStats();
	}
}
while(1);

#================ SUBROUTINES ==================#

sub trim($)
{
	$input = $_[0];
	$input =~ s/^\s+//;
	$input =~ s/\s+$//;
	return $input;
}

sub printStats()
{
	print $LINE;
	foreach $type ("member", "committe", "staff", "associat", "guest")
	{
		print ("$type: " . ($stats{"$type"} or 0). "\n");
	}
	
	print $LINE;

	print ("Paid eligible voters: " . (($stats{"member"} + $stats{"staff"} + $stats{"committe"}) or 0) . "\n");
	print ("Quorom: $quorom\n");
}

sub doStats($)
{
	$input = $_[0];
	if(exists($users{"$input"}))
	{
		@bits = @{$users{"$input"}};
		$usertype = lc($bits[1]);
		$stats{"$usertype"}++ if($usertype ne "");
	}
}

sub printDetails($)
{
	unless(exists $users{$_[0]} and ref($users{$_[0]}) eq "ARRAY")
	{
		warning("User is not a redbrick member");
		return 0;
	}	
	
	@bits = @{$users{$_[0]}};
	print $LINE;
	print "Username:   $bits[0]\n";
	print "Realname:   $bits[2]\n";
	print "Usertype:   $bits[1]\n";
	print "Email:      $bits[4]\n";
	print "Years paid: $bits[8]\n";
	print "Number:     $bits[5]\n";
	print $LINE;
}

sub saveStatus($)
{
	$id = "$_[0]";
	if(exists($users{$id}))
	{
		@bits = @{$users{$id}};  
		open(OUT, ">>$LOG");
		print OUT "$bits[5] $bits[0]\n";
		close OUT;
	}
}

sub readStatus
{
	open(IN, "<$LOG") or return 0;
	foreach $line (<IN>)
	{
		chomp $line;
		if($line =~ /\s*(\d{8})\s/)
		{	
			if(!exists($registered{$1}))
			{
				doStats($1);		
				$registered{$1} = 1;
			}
			else
			{
				warning("Duplicate student number found in log file!");
			}
		}
	}
	close IN;
	printStats();
	return 1;
}

sub checkEligibility($)
{
	@details = @{$users{$_[0]}};
	$failure = "";
	
	if(!(exists($users{$_[0]})))
	{
		$failure .= "(Not member) "
	}
	else
	{
		if($details[8] <= 0)
		{
			$failure .= "(Not paid up) ";
		}

		unless((lc($details[1]) eq "member" or lc($details[1]) eq "staff" or lc($details[1]) eq "committe"))
		{
			$failure .= "(Wrong usertype)";
		}
	}

	if($COLORS) {
		print ("Vote:       " . ($failure eq "" ? "[32mYES[0m\n" : "[31mNO[0m $failure\n"));
	}
	else {
		print ("Vote:       " . ($failure eq "" ? "YES\n" : "NO $failure\n"));
	}
}

sub error($)
{
	die($_[0]);
}

sub warning($)
{
	if($COLORS)
	{
		print "WARNING: [31m$_[0][0m\n";
	}
	else
	{
		print "WARNING: $_[0]\n";
	}
}
