"""NApp responsible for installing or removing flows on the switches."""

import json

from flask import request

from kytos.core import KytosEvent, KytosNApp, log, rest

from napps.kytos.of_flow_manager import settings


class Main(KytosNApp):
    """Main class of of_stats NApp."""

    def setup(self):
        """Replace the 'init' method for the KytosApp subclass.

        The setup method is automatically called by the run method.
        Users shouldn't call this method directly.
        """
        self.flow_manager = FlowManager(self.controller)

    def execute(self):
        """Method to be runned once on app 'start' or in a loop.

        The execute method is called by the run method of KytosNApp class.
        Users shouldn't call this method directly.
        """
        pass

    def shutdown(self):
        """Shutdown routine of the NApp."""
        log.debug("flow-manager stopping")

    @rest('flows')
    @rest('flows/<dpid>')
    def retrieve_flows(self, dpid=None):
        """Retrieve all flows from a switch identified by dpid.

        If no dpid has been specified, returns the flows from all switches.
        """
        switch_flows = {}

        if dpid:
            target = [dpid]
        else:
            target = self.controller.switches

        for switch_dpid in target:
            switch = self.controller.get_switch_by_dpid(switch_dpid)
            flows = {}
            for flow in switch.flows:
                flow = (flow.as_dict()['flow'])
                flow_id = flow.pop('self.id', 0)
                flows[flow_id] = flow
            switch_flows[switch_dpid] = flows
        return json.dumps(switch_flows)

    @rest('flows', methods=['POST'])
    @rest('flows/<dpid>', methods=['POST'])
    def insert_flows(self, dpid=None):
        """Install new flows in the switch identified by dpid.

        If no dpid has been specified, install flows in all switches.
        """
        json_content = request.get_json()
        for json_flow in json_content:
            received_flow = Flow.from_dict(json_flow)
            if dpid:
                self.flow_manager.install_new_flow(received_flow, dpid)
            else:
                for switch_dpid in self.controller.switches:
                    self.flow_manager.install_new_flow(received_flow,
                                                       switch_dpid)

        return json.dumps({"response": "FlowMod Messages Sent"}), 201

    @rest('flows', methods=['DELETE'])
    @rest('flows/<dpid>', methods=['DELETE'])
    @rest('flows/<dpid>/<flow_id>', methods=['DELETE'])
    def delete_flows(self, flow_id=None, dpid=None):
        """Delete a flow from a switch identified by flow_id and dpid.

        If no flow_id has been specified, removes all flows from the switch.
        If no dpid or flow_id  has been specified, removes all flows from all
        switches.
        """
        if flow_id:
            self.flow_manager.delete_flow(flow_id, dpid)
        elif dpid:
            self.flow_manager.clear_flows(dpid)
        else:
            for switch_dpid in self.controller.switches:
                self.flow_manager.clear_flows(switch_dpid)

        return json.dumps({"response": "FlowMod Messages Sent"}), 202


class FlowParser(object):
    """Class responsible for manipulating flows at the switches."""

    def flowmod10_from_dict():
        """Return an OF1.0 FlowMod message created from input dictionary."""
        pass

    def flow10_as_dict():
        """Return a dictionary created from input 1.0 switch's flows."""
        pass

    def flowmod13_from_dict():
        """Return an OF1.3 FlowMod message created from input dictionary."""
        pass

    def flow13_as_dict():
        """Return a dictionary created from input 1.3 switch's flows."""
        pass
