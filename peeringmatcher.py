#!/usr/bin/env python
#
# Peering matcher 0.4
#
#   Written by Job Snijders <job@instituut.net>
#
# With significant contributions from:
#
#       Jerome Vanhoutte <jerome@dev252.org>
#	David Freedman <lcreg-github@convergence.cx>
#
# To the extent possible under law, Job Snijders has waived all copyright
# and related or neighboring rights to this piece of code.
# This work is published from: The Netherlands.
#
# Install Guide:
#
# shell$ pip install 'prettytable>0.6.1' # version 0.6.1 or later
#
# Do not hesitate to send me patches/bugfixes/love ;-)

base_url    = 'https://beta.peeringdb.com/api'
default_asn = 8283

import exceptions, json, optparse, sys, socket, urllib2
from time import strftime, gmtime
from prettytable import *

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

    example: ./peeringmatcher.py 8283 16509

    Peeringmatcher.py will do a lookup against PeeringDB.net.
    In case a single ASN is given as an argument, the program will match
    against the default_asn variable, set in the header of the script.

    This is Public Domain code, with contributions from:

        Job Snijders <job@instituut.net>
        Jerome Vanhoutte <jerome@dev252.org>
	David Freedman <lcreg-github@convergence.cx>
"""
    sys.exit(1)

def _lazy_get(path):
    """ Lazily get content from the API, parse the JSON and return a dictionary
    """
    try:
        return json.loads(urllib2.urlopen(base_url + '/' + path).read())
    except:
        return {}


def main(asn_list):

    # If no ASN is defined on the commandline, the default_asn is used
    if (default_asn not in asn_list) and (len(asn_list) == 1):
        asn_list.append(default_asn)

    # Get JSON from PDB2 and work with it
    asns = {}
    ixps = {}
    table_header = ['IXP']
    for asn in map(str, asn_list):
        asns[asn] = _lazy_get('asn/%s' % asn)
        if asns[asn]['data'][0].get('ixlink_set'):
            for ixp in asns[asn]['data'][0]['ixlink_set']:
                ix_lan = ixp['ix_lan']
                if type(ixps.get(ix_lan, None)) is not dict:
                    ixps[ix_lan]        = {}
                if type(ixps[ix_lan].get(asn, None)) is not list:
                    ixps[ix_lan][asn]   = []
                ixps[ixp['ix_lan']][asn].append(ixp)
        table_header.append("AS%s - %s" % (int(asn), asns[asn]['data'][0]['name']))

    common_table = PrettyTable(table_header)

    # Now look for matches, and render them
    for ix_lan in ixps:
        if len(ixps[ix_lan]) == len(asn_list):
            row      = []
            ix_name  = 'UNKNOWN'
            # Dont bother caching this since we only use it once
            try:
                ix_name = _lazy_get('ix/%s' % _lazy_get('ixlan/%s' % ix_lan)['data'][0]['ix'])['data'][0]['name']
            except:
                pass
            row.append(ix_name)
            for asn in ixps[ix_lan]:
                asnaddrs = []
                for ixp in ixps[ix_lan][asn]:
                    ipaddr4  = ixp['ipaddr4']
                    ipaddr6  = ixp['ipaddr6']
                    if ipaddr4 is not None and _is_ipv4(ipaddr4):
                        asnaddrs.append(ipaddr4)
                    if ipaddr6 is not None and _is_ipv6(ipaddr6):
                        asnaddrs.append(ipaddr6)
                row.append('\n'.join(asnaddrs))
            common_table.add_row(row)

    common_table.hrules = ALL
    print "Common IXPs according to PeeringDB.net - time of generation: %s" % (time)
    print common_table
    print ""

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
