#!/usr/bin/env python

"""Defines Custom topology to create islands with switch chains
   use it with mininet as:
   mn --topo=islands --custom islands.py
"""

from mininet.topo import Topo, Node

class Islands(Topo):
    """Defines Custom topology to create islands with switch chains
        S1------S3      S5----S7 ...
        |       |       |     |
        h2      h4      h6    h8
        parameters: number of islands, number of switches in an island, number of hosts per switch
        (default to 2,2,1)
    """
    def __init__(self, islands=2, switches_per_island=2, hosts_per_sw=1, enable_all=True):
        super(Islands, self).__init__()
        nextid = 1
        for i in range(islands):
            thissw = None
            prevsw = None
            for i in range(switches_per_island):
                thissw = nextid
                nextid += 1
                self.add_node(thissw, Node(is_switch=True))
                if prevsw:
                    self.add_edge(prevsw, thissw)
                for i in range(hosts_per_sw):
                    hostid = nextid
                    nextid += 1
                    self.add_node(hostid, Node(is_switch=False))
                    self.add_edge(hostid, thissw)
                prevsw = thissw
        if enable_all:
            self.enable_all()

topos = { "islands": Islands, } 
