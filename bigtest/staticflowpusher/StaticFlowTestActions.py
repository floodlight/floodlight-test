#!/usr/bin/env python
#
# @owner: Mandeep Dhami, Big Switch Networks
# @author Jason Parraga, Marist College (Jason.Parraga1@marist.edu)
#
# This test verifies that the controller can specify all openflow 1.0 actions
# for a flow-entry and that they are properly installed on the switch.
# It does not do any traffic testing to verify the switch's implementation.
#
# In particular, it does the following:
# 1. Sets up a linear topology with 2 hosts and 1 switch (default mininet topology)
# 2. Verifies that switch exists and has no flow-entrys
# 3. For each action type create a flow-entry and verify that it exists on the switch
# 4. Create a flow-entry with no action (drop) and verify that it exists on the switch
# 5. Create a single flow-entry with ALL actions and verify that it exists on the switch
# 6. Delete all flow-entries and verify that eventually no flow-entries exist on the switch
#

import bigtest.controller
import mininet.topolib
import bigtest
import urllib

# setup env
env = bigtest.controller.TwoNodeTest()
log = bigtest.log.info

controller = env.node1()
node1type = controller.imageType()
# setup topology
net = controller.mininet(mininet.topolib.TreeTopo(depth=1))
cli = controller.cli()
rest = controller.restGet

# dpid of the controller
dpid = '00:00:00:00:00:00:00:03'

# action input, Floodlight REST API output
actions = [
    ['output=0', "{u'length': 8, u'type': u'OUTPUT', u'port': 0, u'lengthU': 8, u'maxLength': 32767}" ],
    ['output=controller', "{u'length': 8, u'type': u'OUTPUT', u'port': -3, u'lengthU': 8, u'maxLength': 32767}" ],
    ['enqueue=0:3', "{u'queueId': 3, u'length': 16, u'type': u'OPAQUE_ENQUEUE', u'port': 0, u'lengthU': 16}"],
    ['set-vlan-id=200', "{u'length': 8, u'virtualLanIdentifier': 200, u'type': u'SET_VLAN_ID', u'lengthU': 8}" ],
    ['set-vlan-priority=5', "{u'length': 8, u'type': u'SET_VLAN_PCP', u'lengthU': 8, u'virtualLanPriorityCodePoint': 5}" ],
    ['strip-vlan', "{u'length': 8, u'type': u'STRIP_VLAN', u'lengthU': 8}" ],
    ['set-src-mac=00:11:22:33:44:55', "{u'dataLayerAddress': u'00:11:22:33:44:55', u'length': 16, u'type': u'SET_DL_SRC', u'lengthU': 16}" ],
    ['set-dst-mac=ff:ee:dd:cc:bb:aa', "{u'dataLayerAddress': u'ff:ee:dd:cc:bb:aa', u'length': 16, u'type': u'SET_DL_DST', u'lengthU': 16}" ],
    ['set-src-ip=1.2.3.4', "{u'type': u'SET_NW_SRC', u'length': 8, u'networkAddress': 16909060, u'lengthU': 8}" ],
    ['set-dst-ip=254.253.255.0', "{u'type': u'SET_NW_DST', u'length': 8, u'networkAddress': -16908544, u'lengthU': 8}" ],
    ['set-tos-bits=0x07', "{u'networkTypeOfService': 7, u'type': u'SET_NW_TOS', u'length': 8, u'lengthU': 8}" ],
    ['set-src-port=100', "{u'length': 8, u'type': u'SET_TP_SRC', u'lengthU': 8, u'transportPort': 100}" ],
    ['set-dst-port=0x100', "{u'length': 8, u'type': u'SET_TP_DST', u'lengthU': 8, u'transportPort': 256}" ],
]

log("Verify that the switch exists and is active")
controller.waitForSwitches([dpid])

# pushes a string representation of a flow the the static flow pusher Rest API
def push_flow(sFlow):
        controller.urlPost('/wm/staticflowentrypusher/json', sFlow)
        
# creates a static flow string with a single action to be pushed to the static flow pusher REST API
def create_single_action_static_flow_post_data(action):
    return '{"switch": "%s", "name":"flow-mod-1", "cookie":"0", "priority":"32768", "ingress-port":"1","active":"true", "actions":"%s"}' % (dpid, action)

# creates a static flow string with all actions to be pushed to the static flow pusher REST API
def create_all_action_static_flow_post_data():
    actionList = []
    for i in range(0,len(actions)):
        if(i > 0):
            actionList.append(',')
        actionList.append(actions[i][0])
    allActions = ''.join([`action`.strip("'") for action in actionList]) #list comprehension that generates a string containing all the actions
    return '{"switch": "%s", "name":"flow-mod-1", "cookie":"0", "priority":"32768", "ingress-port":"1","active":"true", "actions":"%s"}' % (dpid, allActions)

# pushes a static flow with each action one by one and verifies that they are pushed
def assert_action_push():
    for i in range(len(actions)):
        if node1type == "linux":
            action_inp, action_outp = actions[i][0],  actions[i][1]
            log("Test for flow-entry with action = '%s' -> '%s'", action_inp, action_outp)
            sFlow = create_single_action_static_flow_post_data(action_inp)
            push_flow(sFlow)
                
            # verify in config and active flows
            if node1type == "linux":
                flows = controller.restGet('core/switch/%s/flow/json' % dpid)
                bigtest.Assert(str(flows[dpid][0]['actions'][0]) == str(action_outp))

# pushes a static flow with no action and verifies that it has been pushed       
def assert_no_action_push():
    sFlow = '{"switch": "%s", "name":"flow-mod-1", "cookie":"0", "priority":"32768", "ingress-port":"1","active":"true", "actions":""}' % dpid
    push_flow(sFlow)
    
    # verify in config and active flows
    if node1type == "linux":
        flows = controller.restGet('core/switch/%s/flow/json' % dpid)
        print "printing flows" + str(flows[dpid][0]['actions'])
        bigtest.Assert(flows[dpid][0]['actions'] == [])

# pushes a single flow with all actions and verifies that it has been pushed        
def assert_all_action_push():
    log("Test for flow-entry with all actions")
    sFlow = create_all_action_static_flow_post_data()
    push_flow(sFlow)
        
    # verify flow with all actions is active
    if node1type == "linux":
        flows = controller.restGet('core/switch/%s/flow/json' % dpid)
        bigtest.Assert(len(flows[dpid][0]['actions']) == len(actions))    

# verifies that no static flows currently exist, (remove will clear flows if set to True)        
def assert_no_flows(remove):
    if node1type == "linux":
        # remove flows via static flow pusher api (done when finishing test)
        if remove:
            urllib.urlopen("http://%s:8080/wm/staticflowentrypusher/clear/all/json" % controller.ipAddress())
        restout = rest('core/switch/%s/flow/json' % dpid)
    bigtest.Assert(restout[dpid] == [])

# begin Testing...

log("Ensuring there are no static flows before testing.")
assert_no_flows(False)

log("Pushing a static flow with no action")
assert_no_action_push()

log("Pushing a series of static flows with different actions")
assert_action_push()

log("Pushing a static flow with all actions")     
assert_all_action_push()

log("Removing all static flows and verifying that they have been removed")
assert_no_flows(True)

net.stop()
env.endTest()