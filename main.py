"""kytos/flow_manager NApp installs, lists and deletes switch flows."""
from collections import OrderedDict
from copy import deepcopy

from flask import jsonify, request
from pyof.foundation.base import UBIntBase
from pyof.v0x01.asynchronous.error_msg import BadActionCode
from pyof.v0x01.common.phy_port import PortConfig
from werkzeug.exceptions import BadRequest, NotFound, UnsupportedMediaType

from kytos.core import KytosEvent, KytosNApp, log, rest
from kytos.core.helpers import listen_to
from napps.kytos.flow_manager.match import match_flow
from napps.kytos.flow_manager.storehouse import StoreHouse
from napps.kytos.of_core.flow import FlowFactory

from .exceptions import InvalidCommandError
from .settings import ENABLE_CONSISTENCY_CHECK
from .settings import (CONSISTENCY_COOKIE_IGNORED_RANGE,
                       CONSISTENCY_TABLE_ID_IGNORED_RANGE, FLOWS_DICT_MAX_SIZE)


def cast_fields(flow_dict):
    """Make casting the match fields from UBInt() to native int ."""
    match = flow_dict['match']
    for field, value in match.items():
        if isinstance(value, UBIntBase):
            match[field] = int(value)
    flow_dict['match'] = match
    return flow_dict


def _validate_range(values):
    """Check that the range of flows ignored by the consistency is valid."""
    if len(values) != 2:
        msg = f'The tuple must have 2 items, not {len(values)}'
        raise ValueError(msg)
    first, second = values
    if second < first:
        msg = f'The first value is bigger than the second: {values}'
        raise ValueError(msg)
    if not isinstance(first, int) or not isinstance(second, int):
        msg = f'Expected a tuple of integers, received {values}'
        raise TypeError(msg)


def _valid_consistency_ignored(consistency_ignored_list):
    """Check the format of the list of ignored consistency flows.

    Check that the list of ignored flows in the consistency check
    is well formatted. Returns True, if the list is well
    formatted, otherwise return False.
    """
    msg = ('The list of ignored flows in the consistency check'
           'is not well formatted, it will be ignored: %s')
    for consistency_ignored in consistency_ignored_list:
        if isinstance(consistency_ignored, tuple):
            try:
                _validate_range(consistency_ignored)
            except (TypeError, ValueError) as error:
                log.warn(msg, error)
                return False
        elif not isinstance(consistency_ignored, (int, tuple)):
            error_msg = ('The elements must be of class int or tuple'
                         f' but they are: {type(consistency_ignored)}')
            log.warn(msg, error_msg)
            return False
    return True


class Main(KytosNApp):
    """Main class to be used by Kytos controller."""

    def setup(self):
        """Replace the 'init' method for the KytosApp subclass.

        The setup method is automatically called by the run method.
        Users shouldn't call this method directly.
        """
        log.debug("flow-manager starting")
        self._flow_mods_sent = OrderedDict()
        self._flow_mods_sent_max_size = FLOWS_DICT_MAX_SIZE
        self.cookie_ignored_range = []
        self.tab_id_ignored_range = []
        if _valid_consistency_ignored(CONSISTENCY_COOKIE_IGNORED_RANGE):
            self.cookie_ignored_range = CONSISTENCY_COOKIE_IGNORED_RANGE
        if _valid_consistency_ignored(CONSISTENCY_TABLE_ID_IGNORED_RANGE):
            self.tab_id_ignored_range = CONSISTENCY_TABLE_ID_IGNORED_RANGE

        # Storehouse client to save and restore flow data:
        self.storehouse = StoreHouse(self.controller)

        # Format of stored flow data:
        # {'flow_persistence': {'dpid_str': {'flow_list': [
        #                                     {'command': '<add|delete>',
        #                                      'flow': {flow_dict}}]}}}
        self.stored_flows = {}
        self.resent_flows = set()

    def execute(self):
        """Run once on NApp 'start' or in a loop.

        The execute method is called by the run method of KytosNApp class.
        Users shouldn't call this method directly.
        """
        self._load_flows()

    def shutdown(self):
        """Shutdown routine of the NApp."""
        log.debug("flow-manager stopping")

    @listen_to('kytos/of_core.handshake.completed')
    def resend_stored_flows(self, event):
        """Resend stored Flows."""
        # if consistency check is enabled, it should take care of this
        if CONSISTENCY_INTERVAL >= 0:
            return
        switch = event.content['switch']
        dpid = str(switch.dpid)
        # This can be a problem because this code is running a thread
        if dpid in self.resent_flows:
            log.debug(f'Flow already resent to the switch {dpid}')
            return
        if dpid in self.stored_flows:
            flow_list = self.stored_flows[dpid]['flow_list']
            for flow in flow_list:
                command = flow['command']
                flows_dict = {"flows": [flow['flow']]}
                self._install_flows(command, flows_dict, [switch])
            self.resent_flows.add(dpid)
            log.info(f'Flows resent to Switch {dpid}')

    @staticmethod
    def is_ignored(field, ignored_range):
        """Check that the flow field is in the range of ignored flows.

        Returns True, if the field is in the range of ignored flows,
        otherwise it returns False.
        """
        for i in ignored_range:
            if isinstance(i, tuple):
                start_range, end_range = i
                if start_range <= field <= end_range:
                    return True
            if isinstance(i, int):
                if field == i:
                    return True
        return False

    def consistency_ignored_check(self, flow):
        """Check if the flow is in the list of flows ignored by consistency.

        Check by `cookie` range and `table_id` range.
        Return True if the flow is in the ignored range, otherwise return
        False.
        """
        # Check by cookie
        if self.is_ignored(flow.cookie, self.cookie_ignored_range):
            return True

        # Check by `table_id`
        if self.is_ignored(flow.table_id, self.tab_id_ignored_range):
            return True
        return False

    @listen_to('kytos/of_core.flow_stats.received')
    def on_flow_stats_check_consistency(self, event):
        """Check the consistency of a switch upon receiving flow stats."""
        if ENABLE_CONSISTENCY_CHECK is False:
            return
        switch = event.content['switch']
        if switch.is_enabled():
            self.check_storehouse_consistency(switch)
            if switch.dpid in self.stored_flows:
                self.check_switch_consistency(switch)

    def check_switch_consistency(self, switch):
        """Check consistency of installed flows for a specific switch."""
        dpid = switch.dpid

        # Flows stored in storehouse
        stored_flows = self.stored_flows[dpid]['flow_list']

        serializer = FlowFactory.get_class(switch)

        for stored_flow in stored_flows:
            command = stored_flow['command']
            stored_flow_obj = serializer.from_dict(stored_flow['flow'], switch)

            flow = {'flows': [stored_flow['flow']]}

            if stored_flow_obj not in switch.flows:
                if command == 'add':
                    log.info('A consistency problem was detected in '
                             f'switch {dpid}.')
                    self._install_flows(command, flow, [switch])
                    log.info(f'Flow forwarded to switch {dpid} to be '
                             'installed.')
            elif command == 'delete':
                log.info('A consistency problem was detected in '
                         f'switch {dpid}.')
                command = 'delete_strict'
                self._install_flows(command, flow, [switch])
                log.info(f'Flow forwarded to switch {dpid} to be deleted.')

    def check_storehouse_consistency(self, switch):
        """Check consistency of installed flows for a specific switch."""
        dpid = switch.dpid

        for installed_flow in switch.flows:

            # Check if the flow are in the ignored flow list
            if self.consistency_ignored_check(installed_flow):
                continue

            if dpid not in self.stored_flows:
                log.info('A consistency problem was detected in '
                         f'switch {dpid}.')
                flow = {'flows': [installed_flow.as_dict()]}
                command = 'delete_strict'
                self._install_flows(command, flow, [switch])
                log.info(f'Flow forwarded to switch {dpid} to be deleted.')
            else:
                serializer = FlowFactory.get_class(switch)
                stored_flows = self.stored_flows[dpid]['flow_list']
                stored_flows_list = [serializer.from_dict(stored_flow['flow'],
                                                          switch)
                                     for stored_flow in stored_flows]

                if installed_flow not in stored_flows_list:
                    log.info('A consistency problem was detected in '
                             f'switch {dpid}.')
                    flow = {'flows': [installed_flow.as_dict()]}
                    command = 'delete_strict'
                    self._install_flows(command, flow, [switch])
                    log.info(f'Flow forwarded to switch {dpid} to be deleted.')

    # pylint: disable=attribute-defined-outside-init
    def _load_flows(self):
        """Load stored flows."""
        try:
            data = self.storehouse.get_data()['flow_persistence']
            if 'id' in data:
                del data['id']
            self.stored_flows = data
        except (KeyError, FileNotFoundError) as error:
            log.debug(f'There are no flows to load: {error}')
        else:
            log.info('Flows loaded.')

    def _store_changed_flows(self, command, flow, switch):
        """Store changed flows.

        Args:
            command: Flow command to be installed
            flow: Flows to be stored
            switch: Switch target
        """
        stored_flows_box = deepcopy(self.stored_flows)
        # if the flow has a destination dpid it can be stored.
        if not switch:
            log.info('The Flow cannot be stored, the destination switch '
                     f'have not been specified: {switch}')
            return
        installed_flow = {}
        flow_list = []
        installed_flow['command'] = command
        installed_flow['flow'] = flow
        deleted_flows = []

        serializer = FlowFactory.get_class(switch)
        installed_flow_obj = serializer.from_dict(flow, switch)

        if switch.id not in stored_flows_box:
            # Switch not stored, add to box.
            flow_list.append(installed_flow)
            stored_flows_box[switch.id] = {'flow_list': flow_list}
        else:
            stored_flows = stored_flows_box[switch.id].get('flow_list', [])
            # Check if flow already stored
            for stored_flow in stored_flows:
                stored_flow_obj = serializer.from_dict(stored_flow['flow'],
                                                       switch)

                version = switch.connection.protocol.version

                if installed_flow['command'] == 'delete':
                    # No strict match
                    if match_flow(flow, version, stored_flow['flow']):
                        deleted_flows.append(stored_flow)

                elif installed_flow_obj == stored_flow_obj:
                    if stored_flow['command'] == installed_flow['command']:
                        log.debug('Data already stored.')
                        return
                    # Flow with inconsistency in "command" fields : Remove the
                    # old instruction. This happens when there is a stored
                    # instruction to install the flow, but the new instruction
                    # is to remove it. In this case, the old instruction is
                    # removed and the new one is stored.
                    stored_flow['command'] = installed_flow.get('command')
                    deleted_flows.append(stored_flow)
                    break

            # if installed_flow['command'] != 'delete':
            stored_flows.append(installed_flow)
            for i in deleted_flows:
                stored_flows.remove(i)
            stored_flows_box[switch.id]['flow_list'] = stored_flows

        stored_flows_box['id'] = 'flow_persistence'
        self.storehouse.save_flow(stored_flows_box)
        del stored_flows_box['id']
        self.stored_flows = deepcopy(stored_flows_box)

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

            if not any(switches):
                raise NotFound("Switch not found")

        switch_flows = {}

        for switch in switches:
            flows_dict = [cast_fields(flow.as_dict())
                          for flow in switch.flows]
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
    @rest('v2/flows', methods=['DELETE'])
    @rest('v2/flows/<dpid>', methods=['DELETE'])
    def delete(self, dpid=None):
        """Delete existing flows in the switch identified by dpid.

        If no dpid is specified, delete flows from all switches.
        """
        return self._send_flow_mods_from_request(dpid, "delete")

    def _get_all_switches_enabled(self):
        """Get a list of all switches enabled."""
        switches = self.controller.switches.values()
        return [switch for switch in switches if switch.is_enabled()]

    def _send_flow_mods_from_request(self, dpid, command, flows_dict=None):
        """Install FlowsMods from request."""
        if flows_dict is None:
            flows_dict = request.get_json() or {}
            content_type = request.content_type
            # Get flow to check if the request is well-formed
            flows = flows_dict.get('flows', [])

            if content_type is None:
                result = 'The request body is empty'
                raise BadRequest(result)

            if content_type != 'application/json':
                result = ('The content type must be application/json '
                          f'(received {content_type}).')
                raise UnsupportedMediaType(result)

            if not any(flows_dict) or not any(flows):
                result = 'The request body is not well-formed.'
                raise BadRequest(result)

        if dpid:
            switch = self.controller.get_switch_by_dpid(dpid)
            if not switch:
                return jsonify({"response": 'dpid not found.'}), 404
            elif switch.is_enabled() is False:
                if command == "delete":
                    self._install_flows(command, flows_dict, [switch])
                else:
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
            serializer = FlowFactory.get_class(switch)
            flows = flows_dict.get('flows', [])
            for flow_dict in flows:
                flow = serializer.from_dict(flow_dict, switch)
                if command == "delete":
                    flow_mod = flow.as_of_delete_flow_mod()
                elif command == "delete_strict":
                    flow_mod = flow.as_of_strict_delete_flow_mod()
                elif command == "add":
                    flow_mod = flow.as_of_add_flow_mod()
                else:
                    raise InvalidCommandError
                self._send_flow_mod(flow.switch, flow_mod)
                self._add_flow_mod_sent(flow_mod.header.xid, flow, command)

                self._send_napp_event(switch, flow, command)
                self._store_changed_flows(command, flow_dict, switch)

    def _add_flow_mod_sent(self, xid, flow, command):
        """Add the flow mod to the list of flow mods sent."""
        if len(self._flow_mods_sent) >= self._flow_mods_sent_max_size:
            self._flow_mods_sent.popitem(last=False)
        self._flow_mods_sent[xid] = (flow, command)

    def _send_flow_mod(self, switch, flow_mod):
        event_name = 'kytos/flow_manager.messages.out.ofpt_flow_mod'

        content = {'destination': switch.connection,
                   'message': flow_mod}

        event = KytosEvent(name=event_name, content=content)
        self.controller.buffers.msg_out.put(event)

    def _send_napp_event(self, switch, flow, command, **kwargs):
        """Send an Event to other apps informing about a FlowMod."""
        if command == 'add':
            name = 'kytos/flow_manager.flow.added'
        elif command in ('delete', 'delete_strict'):
            name = 'kytos/flow_manager.flow.removed'
        elif command == 'error':
            name = 'kytos/flow_manager.flow.error'
        else:
            raise InvalidCommandError
        content = {'datapath': switch,
                   'flow': flow}
        content.update(kwargs)
        event_app = KytosEvent(name, content)
        self.controller.buffers.app.put(event_app)

    @listen_to('.*.of_core.*.ofpt_error')
    def handle_errors(self, event):
        """Receive OpenFlow error and send a event.

        The event is sent only if the error is related to a request made
        by flow_manager.
        """
        message = event.content["message"]

        connection = event.source
        switch = connection.switch

        xid = message.header.xid.value
        error_type = message.error_type
        error_code = message.code
        error_data = message.data.pack()

        # Get the packet responsible for the error
        error_packet = connection.protocol.unpack(error_data)

        if message.code == BadActionCode.OFPBAC_BAD_OUT_PORT:
            actions = []
            if hasattr(error_packet, 'actions'):
                # Get actions from the flow mod (OF 1.0)
                actions = error_packet.actions
            else:
                # Get actions from the list of flow mod instructions (OF 1.3)
                for instruction in error_packet.instructions:
                    actions.extend(instruction.actions)

            for action in actions:
                iface = switch.get_interface_by_port_no(action.port)

                # Set interface to drop packets forwarded to it
                if iface:
                    iface.config = PortConfig.OFPPC_NO_FWD

        try:
            flow, error_command = self._flow_mods_sent[xid]
        except KeyError:
            pass
        else:
            self._send_napp_event(flow.switch, flow, 'error',
                                  error_command=error_command,
                                  error_type=error_type, error_code=error_code)
