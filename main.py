"""kytos/flow_manager NApp installs, lists and deletes switch flows."""
from flask import jsonify, request
from kytos.core import KytosEvent, KytosNApp, log, rest

from napps.kytos.of_core.v0x01.flow import Flow as Flow10
from napps.kytos.of_core.v0x04.flow import Flow as Flow13


class Main(KytosNApp):
    """Main class to be used by Kytos controller."""

    def setup(self):
        """Replace the 'init' method for the KytosApp subclass.

        The setup method is automatically called by the run method.
        Users shouldn't call this method directly.
        """
        log.debug("flow-manager starting")

    def execute(self):
        """Run once on NApp 'start' or in a loop.

        The execute method is called by the run method of KytosNApp class.
        Users shouldn't call this method directly.
        """
        pass

    def shutdown(self):
        """Shutdown routine of the NApp."""
        log.debug("flow-manager stopping")

    @rest('v2/flows')
    @rest('v2/flows/<dpid>')
    def list(self, dpid=None):
        """Retrieve all flows from a switch identified by dpid.

        If no dpid is specified, return all flows from all switches.
        """
        if dpid is None:
            switches = self.controller.switches.values()
        else:
            switches = [self.controller.get_switch_by_dpid(dpid)]

        switch_flows = {}

        for switch in switches:
            flows_dict = [flow.as_dict() for flow in switch.flows]
            switch_flows[switch.dpid] = {'flows': flows_dict}

        return jsonify(switch_flows)

    @rest('v2/flows', methods=['POST'])
    @rest('v2/flows/<dpid>', methods=['POST'])
    def add(self, dpid=None):
        """Install new flows in the switch identified by dpid.

        If no dpid is specified, install flows in all switches.
        """
        return self._send_flow_mods_from_request(dpid, "add")

    @rest('v2/delete', methods=['POST'])
    @rest('v2/delete/<dpid>', methods=['POST'])
    def delete(self, dpid=None):
        """Delete existing flows in the switch identified by dpid.

        If no dpid is specified, delete flows from all switches.
        """
        return self._send_flow_mods_from_request(dpid, "delete")

    def _get_all_switches_enabled(self):
        """Get a list of all switches enabled."""
        switches = self.controller.switches.values()
        return [switch for switch in switches if switch.enabled]

    def _send_flow_mods_from_request(self, dpid, command):
        """Install FlowsMods from request."""
        flows_dict = request.get_json()

        if flows_dict is None:
            return jsonify({"response": 'flows dict is none.'}), 404

        if dpid:
            switch = self.controller.get_switch_by_dpid(dpid)
            if not switch:
                return jsonify({"response": 'dpid not found.'}), 404
            elif switch.enabled is False:
                return jsonify({"response": 'switch is disabled.'}), 404
            else:
                self._install_flows(command, flows_dict, [switch])
        else:
            self._install_flows(command, flows_dict,
                                self._get_all_switches_enabled())

        return jsonify({"response": "FlowMod Messages Sent"})


    def _install_flows(self, command, flows_dict, switches=[]):
        """Execute all procedures to install flows in the switches.

        Args:
            command: Flow command to be installed
            flows_dict: Dictionary with flows to be installed in the switches.
            switches: A list of switches
        """
        for switch in switches:
            serializer = self._get_flow_serializer(switch)
            flows = flows_dict.get('flows', [])
            for flow_dict in flows:
                flow = serializer.from_dict(flow_dict, switch)
                if command == "delete":
                    flow_mod = flow.as_of_delete_flow_mod()
                elif command == "add":
                    flow_mod = flow.as_of_add_flow_mod()
                self._send_flow_mod(flow.switch, flow_mod)

            self._send_napp_event(switch, flow, command)

    def _send_flow_mod(self, switch, flow_mod):
        event_name = 'kytos/flow_manager.messages.out.ofpt_flow_mod'

        content = {'destination': switch.connection,
                   'message': flow_mod}

        event = KytosEvent(name=event_name, content=content)
        self.controller.buffers.msg_out.put(event)

    def _send_napp_event(self, switch, flow, command):
        """Send an Event to other apps informing about a FlowMod."""
        if command == 'add':
            name = 'kytos/flow_manager.flow.added'
        elif command == 'delete':
            name = 'kytos/flow_manager.flow.removed'
        content = {'datapath': switch,
                   'flow': flow}
        event_app = KytosEvent(name, content)
        self.controller.buffers.app.put(event_app)

    @staticmethod
    def _get_flow_serializer(switch):
        """Return the serializer with for the switch OF protocol version."""
        version = switch.connection.protocol.version
        return Flow10 if version == 0x01 else Flow13
