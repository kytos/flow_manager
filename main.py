"""kytos/flow_manager NApp installs, lists and deletes switch flows."""
import json

from flask import request
from kytos.core import KytosEvent, KytosNApp, log, rest

from napps.kytos.flow_manager.serializers.base import FlowSerializer
from napps.kytos.flow_manager.serializers.v0x01 import FlowSerializer10
from napps.kytos.flow_manager.serializers.v0x04 import FlowSerializer13


class Main(KytosNApp):
    """Main class to be used by Kytos controller."""

    def setup(self):
        """Replace the 'init' method for the KytosApp subclass.

        The setup method is automatically called by the run method.
        Users shouldn't call this method directly.
        """
        log.debug("flow-manager starting")
        self._serializer10 = FlowSerializer10()
        self._serializer13 = FlowSerializer13()

    def execute(self):
        """Run once on NApp 'start' or in a loop.

        The execute method is called by the run method of KytosNApp class.
        Users shouldn't call this method directly.
        """
        pass

    def shutdown(self):
        """Shutdown routine of the NApp."""
        log.debug("flow-manager stopping")

    @rest('flows')
    @rest('flows/<dpid>')
    def list(self, dpid=None):
        """Retrieve all flows from a switch identified by dpid.

        If no dpid is specified, return all flows from all switches.
        """
        dpids = [dpid] if dpid else self.controller.switches
        switches = [self.controller.get_switch_by_dpid(dpid) for dpid in dpids]

        switch_flows = {}

        for switch in switches:
            serializer = self._get_serializer(switch)
            flows_dict = [serializer.to_dict(flow) for flow in switch.flows]
            switch_flows[switch.dpid] = flows_dict
        return json.dumps(switch_flows)

    @rest('flows', methods=['POST'])
    @rest('flows/<dpid>', methods=['POST'])
    def add(self, dpid=None):
        """Install new flows in the switch identified by dpid.

        If no dpid is specified, install flows in all switches.
        """
        self._send_events(FlowSerializer.OFPFC_ADD, dpid)
        return json.dumps({"response": "FlowMod Messages Sent"}), 201

    @rest('delete', methods=['POST'])
    @rest('delete/<dpid>', methods=['POST'])
    def delete(self, dpid=None):
        """Delete existing flows in the switch identified by dpid.

        If no dpid is specified, delete flows from all switches.
        """
        self._send_events(FlowSerializer.OFPFC_DELETE, dpid)
        return json.dumps({"response": "FlowMod Messages Sent"}), 202

    def _send_events(self, command, dpid=None):
        """Create FlowMods from HTTP request and send to switches."""
        event_name = 'kytos/flow_manager.messages.out.ofpt_flow_mod'
        if dpid:
            switches = [self.controller.get_switch_by_dpid(dpid)]
        else:
            switches = self.controller.switches

        for switch in switches:
            connection = switch.connection
            serializer = self._get_serializer(switch)
            for flow_dict in request.get_json():
                event = KytosEvent(event_name, {'destination': connection})
                self._send_event(flow_dict, serializer, command, event)

    def _send_event(self, flow_dict, serializer, command, event):
        """Create and send one FlowMod to one switch."""
        # Create FlowMod message
        flow_mod = serializer.from_dict(flow_dict)
        flow_mod.command = command
        # Complete and send KytosEvent
        event.content['message'] = flow_mod
        self.controller.buffers.msg_out.put(event)

    def _get_serializer(self, switch):
        """Return the serializer with for the switch OF protocol version."""
        version = switch.connection.protocol.version
        return self._serializer10 if version == 0x01 else self._serializer13
