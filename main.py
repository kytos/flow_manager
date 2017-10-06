"""NApp responsible for installing or removing flows on the switches."""

import json

from flask import request

from kytos.core import KytosEvent, KytosNApp, log, rest

from pyof.foundation.network_types import HWAddress

from pyof.v0x01.common.action import (ActionOutput as ActionOutput10,
                                      ActionType as ActionType10,
                                      ActionVlanVid)
from pyof.v0x01.controller2switch.flow_mod import (FlowMod as FlowMod10,
                                                   FlowModCommand)

from pyof.v0x04.common.action import (ActionOutput as ActionOutput13,
                                      ActionSetField, ActionType as
                                      ActionType13)
from pyof.v0x04.common.flow_instructions import (InstructionApplyAction,
                                                 InstructionType as IType)
from pyof.v0x04.common.flow_match import OxmOfbMatchField, OxmTLV, VlanId
from pyof.v0x04.controller2switch.flow_mod import FlowMod as FlowMod13

from napps.kytos.of_flow_manager import settings


class Main(KytosNApp):
    """Main class of of_stats NApp."""

    def setup(self):
        """Replace the 'init' method for the KytosApp subclass.

        The setup method is automatically called by the run method.
        Users shouldn't call this method directly.
        """
        self.parser = FlowParser()
        log.debug("flow-manager starting")

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
            flows = []
            for flow in switch.flows:
                if switch.connection.protocol.version == 0x04:
                    flow_dict = self.parser.flow13_as_dict(flow)
                else:
                    flow_dict = self.parser.flow10_as_dict(flow)
                flows.append(flow_dict)
            switch_flows[switch_dpid] = flows
        return json.dumps(switch_flows)

    @rest('add-flows', methods=['POST'])
    @rest('add-flows/<dpid>', methods=['POST'])
    def insert_flows(self, dpid=None):
        """Install new flows in the switch identified by dpid.

        If no dpid has been specified, install flows in all switches.
        """
        if dpid:
            target = [dpid]
        else:
            target = self.controller.switches

        json_content = request.get_json()
        for switch_dpid in target:
            switch = self.controller.get_switch_by_dpid(switch_dpid)
            for flow in json_content:
                if switch.connection.protocol.version == 0x04:
                    flow_mod = self.parser.flowmod13_from_dict(flow)
                else:
                    flow_mod = self.parser.flowmod10_from_dict(flow)

                flow_mod.command = FlowModCommand.OFPFC_ADD

                event = KytosEvent(name=('kytos/of_flow_manager.messages.out.'
                                   'ofpt_flow_mod'),
                                   content={'destination': switch.connection,
                                            'message': flow_mod})

                self.controller.buffers.msg_out.put(event)

        return json.dumps({"response": "FlowMod Messages Sent"}), 201

    @rest('del-flows', methods=['POST'])
    @rest('del-flows/<dpid>', methods=['POST'])
    def delete_flows(self, dpid=None):
        """Delete existing flows in the switch identified by dpid.

        If no dpid has been specified, delete flows from all switches.
        """
        if dpid:
            target = [dpid]
        else:
            target = self.controller.switches

        json_content = request.get_json()
        for switch_dpid in target:
            switch = self.controller.get_switch_by_dpid(switch_dpid)
            for flow in json_content:
                if switch.connection.protocol.version == 0x04:
                    flow_mod = self.parser.flowmod13_from_dict(flow)
                else:
                    flow_mod = self.parser.flowmod10_from_dict(flow)

                flow_mod.command = FlowModCommand.OFPFC_DELETE

                event = KytosEvent(name=('kytos/of_flow_manager.messages.out.'
                                   'ofpt_flow_mod'),
                                   content={'destination': switch.connection,
                                            'message': flow_mod})

                self.controller.buffers.msg_out.put(event)

        return json.dumps({"response": "FlowMod Messages Sent"}), 202


class FlowParser(object):
    """Class responsible for manipulating flows at the switches."""

    flow_attributes = ['table_id', 'priority', 'idle_timeout', 'hard_timeout',
                       'cookie']
    match_attributes = {'in_port': OxmOfbMatchField.OFPXMT_OFB_IN_PORT,
                        'dl_src': OxmOfbMatchField.OFPXMT_OFB_ETH_SRC,
                        'dl_dst': OxmOfbMatchField.OFPXMT_OFB_ETH_DST,
                        'dl_type': OxmOfbMatchField.OFPXMT_OFB_ETH_TYPE,
                        'dl_vlan': OxmOfbMatchField.OFPXMT_OFB_VLAN_VID,
                        'dl_vlan_pcp': OxmOfbMatchField.OFPXMT_OFB_VLAN_PCP}
    match_13to10 = {b: a for a, b in match_attributes.items()}

    def flowmod10_from_dict(self, dictionary):
        """Return an OF1.0 FlowMod message created from input dictionary."""

        flow_mod = FlowMod10()

        for field, data in dictionary.items():
            if field in self.flow_attributes:
                setattr(flow_mod, field, data)
            elif field == 'match':
                for match_field, match_data in data.items():
                    if match_field in self.match_attributes:
                        setattr(flow_mod.match, match_field, match_data)
            elif field == 'actions':
                for action_type, action_data in data.items():
                    if action_type == 'set_vlan':
                        action = ActionVlanVid(vlan_id=action_data)
                        flow_mod.actions.append(action)
                    elif action_type == 'output':
                        action = ActionOutput10(port=action_data)
                        flow_mod.actions.append(action)

        return flow_mod

    def flow10_as_dict(self, flowstats):
        """Return a dictionary created from input 1.0 switch's flows."""

        flow_dict = {}
        for field, data in vars(flowstats).items():
            if field in self.flow_attributes:
                flow_dict[field] = data.value

        flow_dict['match'] = {}
        for field, data in vars(flowstats.match).items():
            if field in self.match_attributes:
                flow_dict['match'][field] = data.value

        flow_dict['actions'] = {}
        for action in flowstats.actions:
            if action.action_type == ActionType10.OFPAT_SET_VLAN_VID:
                flow_dict['actions']['set_vlan'] = action.vlan_id.value
            elif action.action_type == ActionType10.OFPAT_OUTPUT:
                flow_dict['actions']['output'] = action.port.value

        return flow_dict

    def flowmod13_from_dict(self, dictionary):
        """Return an OF1.3 FlowMod message created from input dictionary."""

        flow_mod = FlowMod13()
        instruction = InstructionApplyAction()
        flow_mod.instructions.append(instruction)

        for field, data in dictionary.items():
            if field in self.flow_attributes:
                setattr(flow_mod, field, data)
            elif field == 'match':
                for match_field, match_data in data.items():
                    if match_field in self.match_attributes:
                        tlv = OxmTLV()
                        tlv.oxm_field = self.match_attributes[match_field]
                        if match_field == 'dl_vlan_pcp':
                            tlv.oxm_value = match_data.to_bytes(1, 'big')
                        elif match_field == 'dl_vlan':
                            vid = match_data | VlanId.OFPVID_PRESENT
                            tlv.oxm_value = vid.to_bytes(2, 'big')
                        elif match_field in ('dl_src', 'dl_dst'):
                            addr = HWAddress(match_data)
                            tlv.oxm_value = addr.pack()
                        elif match_field == 'in_port':
                            tlv.oxm_value = match_data.to_bytes(4, 'big')
                        else:
                            tlv.oxm_value = match_data.to_bytes(2, 'big')

                        flow_mod.match.oxm_match_fields.append(tlv)

            elif field == 'actions':
                for action_type, action_data in data.items():
                    if action_type == 'set_vlan':
                        tlv = OxmTLV()
                        tlv.oxm_field = OxmOfbMatchField.OFPXMT_OFB_VLAN_VID
                        vid = action_data | VlanId.OFPVID_PRESENT
                        tlv.oxm_value = vid.to_bytes(2, 'big')
                        action = ActionSetField(field=tlv)
                        instruction.actions.append(action)
                    elif action_type == 'output':
                        action = ActionOutput13(port=action_data)
                        instruction.actions.append(action)

        return flow_mod

    def flow13_as_dict(self, flowstats):
        """Return a dictionary created from input 1.3 switch's flows."""

        flow_dict = {}
        for field, data in vars(flowstats).items():
            if field in self.flow_attributes:
                flow_dict[field] = data.value

        flow_dict['match'] = {}
        for field in flowstats.match.oxm_match_fields:
            if field.oxm_field in self.match_13to10:
                match_field = self.match_13to10.get(field.oxm_field)
                if match_field == 'dl_vlan':
                    data = int.from_bytes(field.oxm_value, 'big') & 4095
                elif match_field in ('dl_src', 'dl_dst'):
                    addr = HWAddress()
                    addr.unpack(field.oxm_value)
                    data = str(addr)
                else:
                    data = int.from_bytes(field.oxm_value, 'big')
                flow_dict['match'][match_field] = data

        flow_dict['actions'] = {}
        for instruction in flowstats.instructions:
            if instruction.instruction_type == IType.OFPIT_APPLY_ACTIONS:
                for action in instruction.actions:
                    if action.action_type == ActionType13.OFPAT_SET_FIELD:
                        if action.field.oxm_field == OxmOfbMatchField.OFPXMT_OFB_VLAN_VID:
                            data = int.from_bytes(action.field.oxm_value,
                                                  'big') & 4095
                        flow_dict['actions']['set_vlan'] = data
                    elif action.action_type == ActionType13.OFPAT_OUTPUT:
                        flow_dict['actions']['output'] = action.port.value

        return flow_dict
