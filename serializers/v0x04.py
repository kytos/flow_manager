"""Flow serializer for OF 1.3."""
from itertools import chain

from pyof.foundation.basic_types import HWAddress, IPAddress
from pyof.foundation.network_types import EtherType
from pyof.v0x04.common.action import (ActionOutput, ActionPopVLAN, ActionPush,
                                      ActionSetField, ActionType)
from pyof.v0x04.common.flow_instructions import InstructionApplyAction
from pyof.v0x04.common.flow_instructions import InstructionType as IType
from pyof.v0x04.common.flow_match import OxmOfbMatchField, OxmTLV, VlanId
from pyof.v0x04.common.port import PortNo
from pyof.v0x04.controller2switch.flow_mod import FlowMod

from napps.kytos.flow_manager.serializers.base import FlowSerializer


class FlowSerializer13(FlowSerializer):
    """Flow serializer for OpenFlow 1.3."""

    def __init__(self):
        """Initialize OF 1.3 specific variables."""
        super().__init__()
        self._match_names = {
            'in_port': OxmOfbMatchField.OFPXMT_OFB_IN_PORT,
            'dl_src': OxmOfbMatchField.OFPXMT_OFB_ETH_SRC,
            'dl_dst': OxmOfbMatchField.OFPXMT_OFB_ETH_DST,
            'dl_type': OxmOfbMatchField.OFPXMT_OFB_ETH_TYPE,
            'dl_vlan': OxmOfbMatchField.OFPXMT_OFB_VLAN_VID,
            'dl_vlan_pcp': OxmOfbMatchField.OFPXMT_OFB_VLAN_PCP,
            'nw_src': OxmOfbMatchField.OFPXMT_OFB_IPV4_SRC,
            'nw_dst': OxmOfbMatchField.OFPXMT_OFB_IPV4_DST,
            'nw_proto': OxmOfbMatchField.OFPXMT_OFB_IP_PROTO}
        # Invert match_values index
        self._match_values = {b: a for a, b in self._match_names.items()}

    def from_dict(self, dictionary):
        """Return an OF 1.0 FlowMod message from serialized dictionary."""
        flow_mod = FlowMod()
        instruction = InstructionApplyAction()
        flow_mod.instructions.append(instruction)

        for field, data in dictionary.items():
            if field in self.flow_attributes:
                setattr(flow_mod, field, data)
            elif field == 'match':
                tlvs = self._match_from_dict(data)
                flow_mod.match.oxm_match_fields.append(list(tlvs))
            elif field == 'actions':
                actions = self._actions_from_list(data)
                instruction.actions.extend(list(actions))

        return flow_mod

    def _match_from_dict(self, dictionary):
        known_fields = ((field, data) for field, data in dictionary.items()
                        if field in self._match_names)
        for field_name, data in known_fields:
            tlv = OxmTLV()
            tlv.oxm_field = self._match_names[field_name]
            # set oxm_value
            if field_name in ('dl_vlan_pcp', 'nw_proto'):
                tlv.oxm_value = data.to_bytes(1, 'big')
            elif field_name == 'dl_vlan':
                vid = data | VlanId.OFPVID_PRESENT
                tlv.oxm_value = vid.to_bytes(2, 'big')
            elif field_name in ('dl_src', 'dl_dst'):
                tlv.oxm_value = HWAddress(data).pack()
            elif field_name in ('nw_src', 'nw_dst'):
                tlv.oxm_value = IPAddress(data).pack()
            elif field_name == 'in_port':
                tlv.oxm_value = data.to_bytes(4, 'big')
            else:
                tlv.oxm_value = data.to_bytes(2, 'big')
            yield tlv

    @classmethod
    def _actions_from_list(cls, action_list):
        for action in action_list:
            new_action = cls._action_from_dict(action)
            if new_action:
                yield new_action

    @classmethod
    def _action_from_dict(cls, action):
        if action['action_type'] == 'set_vlan':
            tlv = cls._create_vlan_tlv(vlan_id=action['vlan_id'])
            return ActionSetField(field=tlv)
        elif action['action_type'] == 'output':
            if action['port'] == 'controller':
                return ActionOutput(port=PortNo.OFPP_CONTROLLER)
            return ActionOutput(port=action['port'])
        elif action['action_type'] == 'push_vlan':
            if action['tag_type'] == 's':
                ethertype = EtherType.VLAN_QINQ
            else:
                ethertype = EtherType.VLAN
            return ActionPush(action_type=ActionType.OFPAT_PUSH_VLAN,
                              ethertype=ethertype)
        elif action['action_type'] == 'pop_vlan':
            return ActionPopVLAN()

    @staticmethod
    def _create_vlan_tlv(vlan_id):
        tlv = OxmTLV()
        tlv.oxm_field = OxmOfbMatchField.OFPXMT_OFB_VLAN_VID
        oxm_value = vlan_id | VlanId.OFPVID_PRESENT
        tlv.oxm_value = oxm_value.to_bytes(2, 'big')
        return tlv

    def to_dict(self, flow_stats):
        """Return a dictionary created from input 1.3 switch's flows."""
        flow_dict = {field: data.value
                     for field, data in vars(flow_stats).items()
                     if field in self.flow_attributes}
        flow_dict['match'] = self._match_to_dict(flow_stats)
        flow_dict['actions'] = self._actions_to_list(flow_stats)
        return flow_dict

    def _match_to_dict(self, flow_stats):
        match_dict = {}
        fields = (field for field in flow_stats.match.oxm_match_fields
                  if field.oxm_field in self._match_values)
        for field in fields:
            match_field = self._match_values[field.oxm_field]
            if match_field == 'dl_vlan':
                data = int.from_bytes(field.oxm_value, 'big') & 4095
            elif match_field in ('dl_src', 'dl_dst'):
                addr = HWAddress()
                addr.unpack(field.oxm_value)
                data = str(addr)
            elif match_field in ('nw_src', 'nw_dst'):
                addr = IPAddress()
                addr.unpack(field.oxm_value)
                data = str(addr)
            else:
                data = int.from_bytes(field.oxm_value, 'big')
            match_dict[match_field] = data
        return match_dict

    def _actions_to_list(self, flow_stats):
        actions_list = []
        for action in self._filter_actions(flow_stats):
            action_dict = self._action_to_dict(action)
            actions_list.append(action_dict)
        return actions_list

    @staticmethod
    def _action_to_dict(action):
        if action.action_type == ActionType.OFPAT_SET_FIELD:
            if action.field.oxm_field == OxmOfbMatchField.OFPXMT_OFB_VLAN_VID:
                data = int.from_bytes(action.field.oxm_value, 'big') & 4095
                return {'action_type': 'set_vlan', 'vlan_id': data}
        elif action.action_type == ActionType.OFPAT_OUTPUT:
            if action.port == PortNo.OFPP_CONTROLLER:
                return {'action_type': 'output', 'port': 'controller'}
            return {'action_type': 'output', 'port': action.port.value}
        elif action.action_type == ActionType.OFPAT_PUSH_VLAN:
            if action.ethertype == EtherType.VLAN_QINQ:
                return {'action_type': 'push_vlan', 'tag_type': 's'}
            return {'action_type': 'push_vlan', 'tag_type': 'c'}
        elif action.action_type == ActionType.OFPAT_POP_VLAN:
            return {'action_type': 'pop_vlan'}
        return {}

    @staticmethod
    def _filter_actions(flow_stats):
        """Filter instructions and return a list of their actions."""
        instructions = (inst for inst in flow_stats.instructions
                        if inst.instruction_type == IType.OFPIT_APPLY_ACTIONS)
        action_lists = (instruction.actions for instruction in instructions)
        # Make a list from a list of lists
        return chain.from_iterable(action_lists)
