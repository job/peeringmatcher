#!/usr/bin/env python
# Peering matcher 0.1 written by Job Snijders <job.snijders@atrato-ip.com>
#
# To the extent possible under law, Job Snijders has waived all copyright
# and related or neighboring rights to this piece of code. 
# This work is published from: The Netherlands.
#
# Install Guide:
#
# pip install mysql-python
# pip install prettytable (version 0.6.1 or later)
# pip install ipaddr
#
# Do not hesitate to send me patches/bugfixes/love ;-)

default_asn = 5580

import sys
import re
import socket
from ipaddr import *
import MySQLdb
from prettytable import *
from time import gmtime , strftime

time = strftime("%Y-%m-%d %H:%M:%S", gmtime())

def is_valid_ipv4_address(address):
    try:
        addr= socket.inet_pton(socket.AF_INET, address)
    except AttributeError: # no inet_pton here, sorry
        try:
            addr= socket.inet_aton(address)
        except socket.error:
            return False
        return address.count('.') == 3
    except socket.error: # not a valid address
        return False
    return True

def is_valid_ipv6_address(address):
    try:
        addr= socket.inet_pton(socket.AF_INET6, address)
    except socket.error: # not a valid address
        return False
    return True

def usage():
    print """Peering Matcher 0.001a
usage: peeringmatcher.py ASN1 [ ASN2 ] [ ASN3 ] [ etc.. ]
\texample: ./peeringmatcher.py 5580 16509
\tIn case a single ASN is given as an argument, the program will match
\tagainst the default_asn in the code.
\tWritten by Job Snijders <job.snijders@atrato-ip.com>
\tMany thanks to http://peeringdb.net"""
    sys.exit(2)

def main():
    asn_list = sys.argv[1:]
    peerings = {}
    asn_names = {}
    if len(asn_list) < 1:
        usage()

    if (default_asn not in asn_list) and (len(asn_list) == 1):
        asn_list.append(default_asn)

    for asn in asn_list:
        try:
            asn = int(asn)
        except:
            print 'Error: Please enter a valid ASN: %s' % (asn)
            usage()
    
    asn_list = map(int, asn_list)

    db = MySQLdb.connect ("peeringdb.net","peeringdb","peeringdb","Peering")
    for asn in asn_list:
        cursor = db.cursor()
        peerings[asn] = {}
        sql_asn_name = "SELECT name FROM peerParticipants WHERE asn = '%s'" % (asn)
        cursor.execute(sql_asn_name)
        try:
            name = cursor.fetchone()[0]
        except:
            print "AS%s does not have a PeeringDB entry :-(" % (asn)
            sys.exit(2)
        asn_names[asn] = name
        
        sql_peering = "select peer.local_ipaddr, public.name from peerParticipantsPublics peer LEFT JOIN mgmtPublics public ON peer.public_id=public.id WHERE peer.local_asn=%s ORDER by public.name;" % (asn)
        cursor.execute(sql_peering)
        results = cursor.fetchall()
        for row in results:
            if row[0] is None:
                continue
            ixp_name = row[1]
            local_ipaddr = row[0].strip()
            local_ipaddr = lcoal_ipaddr.replace('/64','')	
            local_ipaddr = local_ipaddr.replace('/120','')
            local_ipaddr = local_ipaddr.replace('/48','')
            local_ipaddr = local_ipaddr.replace('/22','')
            local_ipaddr = local_ipaddr.replace('/23','')
            local_ipaddr = local_ipaddr.replace('/24','')
            if (is_valid_ipv4_address(local_ipaddr)) or (is_valid_ipv6_address(local_ipaddr)):
                peerings[asn].setdefault(ixp_name, []).append(local_ipaddr)
    db.close()
    
    counter = {}
    for ixdict in peerings.values():
        for ixname in ixdict.keys():
            counter[ixname] = counter.get(ixname, 0) + 1
    common_ixps = []
    for ixp in counter:
        if counter[ixp] == len(asn_names):
            common_ixps.append(ixp)

    if len(common_ixps) == 0:
        print "No common IXPs found in PeeringDB.net database :-("
        sys.exit(2)

    # now magic ascii art
    table_header = ['IXP']
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
