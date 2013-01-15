#!/usr/bin/env python2.7
# 
# Peering matcher 0.2 
#
#   Written by Job Snijders <job.snijders@atrato.com>
#
# With significant contributions from:
#       Vanhoutte Jerome <jerome@dev252.org>
#
# To the extent possible under law, Job Snijders has waived all copyright
# and related or neighboring rights to this piece of code. 
# This work is published from: The Netherlands.
#
# Install Guide:
#
# shell$ pip install mysql-python
# shell$ pip install 'prettytable>0.6.1' # version 0.6.1 or later
# shell$ pip install ipaddr
#
# Do not hesitate to send me patches/bugfixes/love ;-)

default_asn = 5580

import sys
import re
import ipaddr 
import pprint
import MySQLdb
from ipaddr import *
from prettytable import *
from time import *

time = strftime("%Y-%m-%d %H:%M:%S", gmtime())

# Using the ipaddr library make it easy
# Used to validate an ip as the db is provision with crappy data
def is_valid_ipv4_address(address):
    try:
        ipaddr.IPv4Address(address)
        return True
    except ValueError:
        return False

def is_valid_ipv6_address(address):
    try:
        ipaddr.IPv6Address(address)
        return True
    except ValueError: # not a valid address
        return False

def usage():
    print """Peering Matcher 0.2
usage: peeringmatcher.py ASN1 [ ASN2 ] [ ASN3 ] [ etc.. ]

    example: ./peeringmatcher.py 5580 16509

    Peeringmatcher.py will do a lookup against PeeringDB.net.
    In case a single ASN is given as an argument, the program will match
    against the default_asn variable, set in the header of the script.

    This is Public Domain code, with contributions from:

        Job Snijders <job.snijders@atrato.com> 
        Jerome Vanhoutte <jerome@dev252.org>
"""
    sys.exit(2)

def main():
    asn_list = sys.argv[1:]
    peerings = {}
    asn_names = {}
    counter = {}
    common_ixps = []
    table_header = ['IXP']

    if len(asn_list) < 1:
        usage()

    # If no ASN is defined on the commandline, the default_asn is used
    if (default_asn not in asn_list) and (len(asn_list) == 1):
        asn_list.append(default_asn)

    # Go trought all the argument passed via the command line and look if these are integer
    for asn in asn_list:
        try:
            asn = int(asn)
        except:
            print 'Error: Please enter a valid ASN: %s' % (asn)
            usage()
    
    #convert string to integer to be used after as key 
    asn_list = map(int, asn_list)

    # setup connection to peeringdb.net
    db = MySQLdb.connect ("peeringdb.net","peeringdb","peeringdb","Peering")

    for asn in asn_list:
        cursor = db.cursor()
        peerings[asn] = {}

        # Fetch the ASN list 
        sql_asn_name = "select DISTINCT participant.name from peerParticipantsPublics peer \
        LEFT JOIN peerParticipants participant ON participant.id = peer.participant_id \
        WHERE peer.local_asn='%s'" % (asn)

        cursor.execute(sql_asn_name)
        try:
            name = cursor.fetchone()[0]
        except:
            print "AS%s does not have a PeeringDB entry :-(" % (asn)
            sys.exit(2)
        
        asn_names[asn] = name

        # Fetch the peering information for each AS
        sql_peering = "select peer.local_ipaddr, public.name from peerParticipantsPublics peer \
        LEFT JOIN mgmtPublics public ON peer.public_id=public.id \
        WHERE peer.local_asn=%s ORDER by public.name;" % (asn)

        cursor.execute(sql_peering)
        results = cursor.fetchall()
    
        for row in results:
            if row[0] is None:
                continue
            ixp_name = row[1]
            local_ipaddr = row[0].strip()
            local_ipaddr = local_ipaddr.replace('/64','')   
            local_ipaddr = local_ipaddr.replace('/120','')
            local_ipaddr = local_ipaddr.replace('/48','')
            local_ipaddr = local_ipaddr.replace('/22','')
            local_ipaddr = local_ipaddr.replace('/23','')
            local_ipaddr = local_ipaddr.replace('/24','')
            #filter the shit from the database
            if (is_valid_ipv4_address(local_ipaddr)) or (is_valid_ipv6_address(local_ipaddr)):
                peerings[asn].setdefault(ixp_name, []).append(local_ipaddr)
    
    db.close()
    
    for ixdict in peerings.values():
        for ixname in ixdict.keys():
            counter[ixname] = counter.get(ixname, 0) + 1
    
    for ixp in counter:
        if counter[ixp] == len(asn_names):
            common_ixps.append(ixp)

    if len(common_ixps) == 0:
        print "No common IXPs found in PeeringDB.net database :-("
        sys.exit(2)

    # now magic ascii art
    for asn in asn_names:
        name = "AS%s - %s" % (int(asn), asn_names[asn])
        table_header.append(name) 
    common_table = PrettyTable(table_header)
        
    for ixp in common_ixps:
        row = [ixp]
        for asn in asn_names:
            row.append('\n'.join(peerings[asn][ixp]))
        common_table.add_row(row)

    common_table.hrules = ALL
    print "Common IXPs according to PeeringDB.net - time of generation: %s" % (time)
    print common_table

if __name__ == '__main__':
    main()
