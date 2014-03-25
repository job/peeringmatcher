#!/usr/bin/env python
# 
# Peering matcher 0.3 
#
#   Written by Job Snijders <job.snijders@atrato.com>
#
# With significant contributions from:
#
#       Jerome Vanhoutte <jerome@dev252.org>
#
# To the extent possible under law, Job Snijders has waived all copyright
# and related or neighboring rights to this piece of code. 
# This work is published from: The Netherlands.
#
# Install Guide:
#
# shell$ pip install mysql-python
# shell$ pip install 'prettytable>0.6.1' # version 0.6.1 or later
#
# Do not hesitate to send me patches/bugfixes/love ;-)

default_asn = 5580

import MySQLdb
import pprint
import re
import socket
import sys
from prettytable import *
from time import *

time = strftime("%Y-%m-%d %H:%M:%S", gmtime())


def _is_ipv4(ip):
    """ Return true if given arg is a valid IPv4 address
    """
    try:
        socket.inet_aton(ip)
    except socket.error:
        return False
    except exceptions.UnicodeEncodeError:
        return False
    return True


def _is_ipv6(ip):
    """ Return true if given arg is a valid IPv6 address
    """
    try:
        socket.inet_pton(socket.AF_INET6, ip)
    except socket.error, UnicodeEncodeError:
        return False
    except exceptions.UnicodeEncodeError:
        return False
    return True


def usage():
    print """Peering Matcher 0.3
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

class PeeringMatcher:
    def __init__(self):
        # setup connection to peeringdb.net
        self.db = MySQLdb.connect("peeringdb.net", "peeringdb", "peeringdb", "Peering")

    def get_asn_info(self, asn_list):
        """ Get ASN info and return as dict
        """
        cursor = self.db.cursor()
        asns = {}

        # Fetch the ASN list
        sql_asn_name = """
            SELECT DISTINCT peer.asn, peer.name
            FROM peerParticipants peer
            WHERE peer.asn IN (%(asns)s)
            """ % { 'asns': ', '.join(map(str, asn_list)) }

        cursor.execute(sql_asn_name)

        for row in cursor.fetchall():
            asn = row[0]
            as_name = row[1]
            asns[asn] = { 'name': as_name }

        if set(asn_list) != set(asns.keys()):
            raise KeyError("Following AS does not have a PeeringDB entry: %s" % (', '.join(map(str, set(asn_list) - set(asns.keys())))))

        return asns


    def get_common_pops(self, asn_list):
        """ Return a dict with common PoPs between networks
        """
        cursor = self.db.cursor()

        # Fetch common facilities
        sql_pops = """
            SELECT facility.name,
                ppp.local_asn,
                ppp.avail_sonet,
                ppp.avail_ethernet,
                ppp.avail_atm
            FROM mgmtFacilities facility
            JOIN peerParticipantsPrivates ppp ON facility.id = ppp.facility_id
            JOIN peerParticipants peer ON ppp.participant_id = peer.id
            WHERE peer.asn IN (%(asns)s)
                AND facility.id IN (
                SELECT ppp.facility_id
                FROM peerParticipantsPrivates ppp
                JOIN peerParticipants peer ON ppp.participant_id=peer.id
                WHERE peer.asn IN (%(asns)s)
                GROUP BY ppp.facility_id
                HAVING COUNT(1) > 1
                )
            ORDER BY facility.name, ppp.participant_id
            """ % { 'asns': ', '.join(map(str, asn_list)) }
        cursor.execute(sql_pops)

        pops = {}
        for row in cursor.fetchall():
            pop_name = row[0]
            asn = row[1]
            avail_sonet = row[2]
            avail_ethernet = row[3]
            avail_atm = row[4]

            if pop_name not in pops:
                pops[pop_name] = {}
            if asn not in pops[pop_name]:
                pops[pop_name][asn] = []

            if avail_sonet == '1':
                pops[pop_name][asn].append('SONET')
            if avail_ethernet == '1':
                pops[pop_name][asn].append('Ethernet')
            if avail_atm == '1':
                pops[pop_name][asn].append('ATM')

        return pops


    def get_common_ixs(self, asn_list):
        pass

def main(asn_list):
    peerings = {}
    facilities = {}
    asn_names = {}
    common_ixps = []
    common_pops = []

    # If no ASN is defined on the commandline, the default_asn is used
    if (default_asn not in asn_list) and (len(asn_list) == 1):
        asn_list.append(default_asn)

    # setup connection to peeringdb.net
    db = MySQLdb.connect("peeringdb.net", "peeringdb", "peeringdb", "Peering")
    cursor = db.cursor()

    pm = PeeringMatcher()
    asns = pm.get_asn_info(asn_list)

    for asn in asn_list:
        cursor = db.cursor()
        peerings[asn] = {}
        facilities[asn] = {}

        # Fetch the IX peering information for each AS
        sql_peering = """
            SELECT  peer.local_ipaddr,
                    public.name
            FROM peerParticipantsPublics peer
            LEFT JOIN mgmtPublics public ON peer.public_id=public.id
            WHERE peer.local_asn=%s ORDER BY public.name"""

        cursor.execute(sql_peering, [asn])
        results = cursor.fetchall()
    
        for row in results:
            if row[0] is None:
                continue
            ixp_name = row[1]
            local_ipaddr = row[0].strip()
            local_ipaddr = local_ipaddr.split('/')[0]
            # Peeringdb is unfortunately filled with crappy IP data. Filter the
            # shit from the database.
            if _is_ipv4(local_ipaddr) or _is_ipv6(local_ipaddr):
                peerings[asn].setdefault(ixp_name, []).append(local_ipaddr)

    db.close()

    counter = {}
    for ixdict in peerings.values():
        for ixname in ixdict:
            counter[ixname] = counter.get(ixname, 0) + 1

    for ixp in counter:
        if counter[ixp] == len(asns):
            common_ixps.append(ixp)

    counter = {}
    for popdict in facilities.values():
        for popname in popdict:
            counter[popname] = counter.get(popname, 0) + 1

    for pop in counter:
        if counter[pop] == len(asns):
            common_pops.append(pop)

    if len(common_ixps) == 0 and len(common_pops) == 0:
        print >> sys.stderr, "No common IXPs or facilities found in PeeringDB.net database :-("
        sys.exit(2)

    # now magic ascii art
    table_header = ['IXP']
    for asn in asns:
        name = "AS%s - %s" % (int(asn), asns[asn]['name'])
        table_header.append(name) 
    common_table = PrettyTable(table_header)

    for ixp in common_ixps:
        row = [ixp]
        for asn in asns:
            row.append('\n'.join(peerings[asn][ixp]))
        common_table.add_row(row)

    common_table.hrules = ALL
    print "Common IXPs according to PeeringDB.net - time of generation: %s" % (time)
    print common_table

    print ""

    pops = pm.get_common_pops(asn_list)

    table_header = ['Facility']
    # now magic ascii art
    for asn in asns:
        table_header.append("AS%s - %s" % (int(asn), asns[asn]['name']))
    common_table = PrettyTable(table_header)

    for pop_name in pops:
        row = [pop_name]
        for asn in asns:
            row.append('\n'.join(pops[pop_name][asn]))
        common_table.add_row(row)

    common_table.hrules = ALL
    print "Common facilities according to PeeringDB.net - time of generation: %s" % (time)
    print common_table



if __name__ == '__main__':
    import optparse
    parser = optparse.OptionParser()

    options, args = parser.parse_args()

    # we need at least one ASN
    if len(args) < 1:
        usage()

    # Go trought all the argument passed via the command line and look if these are integer
    for asn in args:
        try:
            asn = int(asn)
        except:
            print >> sys.stderr, 'Error: Please enter a valid ASN: %s' % (asn)
            usage()

    # convert string to integer to be used after as key
    asn_list = map(int, args)

    # print pretty table
    main(asn_list)
