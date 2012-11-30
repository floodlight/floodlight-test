#!/usr/bin/env python
#Credit to Brandon Heller (brandonh@stanford.edu), his original example was build on for this.
#Author: Ryan Wallner (ryan.wallner1@marist.edu)
#Editor: Jason Parraga (Jason.Parraga1@marist.edu)

"""Defines Custom square toplogy like so

    h5 --- s1 --- s3 --- h6
            |      |
    h7 --- s2 --- s4 --- h8
    
   use it with mininet as:
   mn --topo=square --custom square.py
"""

from mininet.topo import Topo, Node

class Square(Topo):
    def __init__(self, enable_all=True):
        super(Square, self).__init__()
        
        # Set Node IDs for Switches
        leftSwitch = 1
        bottomLeftSwitch = 2
        rightSwitch = 3
        bottomRightSwitch = 4
        
        # Set Node IDs for hosts
        leftTopHost = 5
        rightTopHost = 6
        bottomLeftHost = 7
        bottomRightHost = 8
        
        switch = Node(is_switch=True)
        host = Node(is_switch=False)
        
        # Add Nodes
        self.add_node(leftSwitch, switch)
        self.add_node(rightSwitch, switch)
        self.add_node(bottomLeftSwitch, switch)
        self.add_node(bottomRightSwitch, switch)
        
        self.add_node(leftTopHost, host)
        self.add_node(rightTopHost, host)
        self.add_node(bottomLeftHost, host)
        self.add_node(bottomRightHost, host)
        
        # Add edges
        self.add_edge(leftTopHost, leftSwitch)
        self.add_edge(rightSwitch, rightTopHost)
        self.add_edge(bottomLeftHost, bottomLeftSwitch)
        self.add_edge(bottomRightSwitch, bottomRightHost)
        
        self.add_edge(leftSwitch, rightSwitch)
        self.add_edge(bottomLeftSwitch, bottomRightSwitch)
        self.add_edge(rightSwitch, bottomRightSwitch)
        self.add_edge(leftSwitch, bottomLeftSwitch)
        
        switches = [leftSwitch, rightSwitch, bottomLeftSwitch, bottomRightSwitch]
        
        # Add inter-switch link ports
        self.port(leftSwitch, rightSwitch)
        self.port(leftSwitch, bottomLeftSwitch)
        self.port(rightSwitch, leftSwitch)
        self.port(rightSwitch, bottomRightSwitch)
        self.port(bottomLeftSwitch, leftSwitch)
        self.port(bottomLeftSwitch, bottomRightSwitch)
        self.port(bottomRightSwitch, rightSwitch)
        self.port(bottomRightSwitch, bottomLeftSwitch)
                    
        self.enable_all()

topos = { "square": Square, } 
