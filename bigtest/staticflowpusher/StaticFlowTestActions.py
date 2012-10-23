#!/usr/bin/env python
#
# owner: mandeep
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

# Setup Env
env = bigtest.controller.TwoNodeTest()
log = bigtest.log.info

controller = env.node1()
node1type = controller.imageType()
net = controller.mininet(mininet.topolib.TreeTopo(depth=1))
cli = controller.cli()
rest = controller.restGet

dpid = '00:00:00:00:00:00:00:03'
# Input, Floodlight REST API output
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

log("Verify that there are no flows")
if node1type == "linux":
    restout = rest('core/switch/%s/flow/json' % dpid)
bigtest.Assert(restout[dpid] == [])

# creates a static flow that is sued by the Floodlight REST API
def create_static_flow_post_data(dpid, action):
    return '{"switch": "%s", "name":"flow-mod-1", "cookie":"0", "priority":"32768", "ingress-port":"1","active":"true", "actions":"%s"}' % (dpid, action)

log("Assert that a specific action/list of actions can be set on the switch")
def assert_action_push(idx, sw, action_inp, action_outp):
    log("Test for flow-entry with action = '%s' -> '%s'", action_inp, action_outp)
    sFlow = create_static_flow_post_data(sw, action_inp)
    if node1type == "linux":
        # push flow via static flow pusher api
        controller.urlPost('/wm/staticflowentrypusher/json', sFlow)
        
    # verify in config and active flows
    if node1type == "linux":
        flows = controller.restGet('core/switch/%s/flow/json' % sw)
        print flows
        print str(action_outp)
        bigtest.Assert(str(flows[sw][0]['actions'][0]) == str(action_outp))

for i in range(len(actions)):
    if node1type == "linux":
        assert_action_push(i, dpid, actions[i][0],  actions[i][1])
net.stop()
env.endTest()
