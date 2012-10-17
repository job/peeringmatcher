Peeringmatcher
==============

        alice:peering job$ ./peeringmatcher.py
        Peering Matcher 0.1
        usage: peeringmatcher.py ASN1 [ ASN2 ] [ ASN3 ] [ etc.. ]
            example: ./peeringmatcher.py 5580 16509
            In case a single ASN is given as an argument, the program will match
            against the default_asn in the code.
            Written by Job Snijders <job.snijders@atrato-ip.com>
            Many thanks to http://peeringdb.net
        alice:peering job$

Check what IXPs AS5580 and AS8954 have in common:
-------------------------------------------------

        Alice:peering job$ ./peeringmatcher.py 5580 8954
        +--------+-------------------------+-----------------------------+
        |  IXP   |  AS8954 - InTouch N.V.  | AS5580 - Atrato IP Networks |
        +--------+-------------------------+-----------------------------+
        | AMS-IX |      195.69.144.93      |        195.69.144.229       |
        |        | 2001:7f8:1::a500:8954:1 |        195.69.145.229       |
        |        |                         |   2001:7f8:1::a500:5580:1   |
        |        |                         |   2001:7f8:1::a500:5580:2   |
        +--------+-------------------------+-----------------------------+
        Alice:peering job$ 
