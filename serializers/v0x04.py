"""Flow serializer for OF 1.3."""
from itertools import chain

from pyof.foundation.network_types import HWAddress
from pyof.v0x04.common.action import ActionOutput, ActionSetField, ActionType
from pyof.v0x04.common.flow_instructions import InstructionType as IType
from pyof.v0x04.common.flow_instructions import InstructionApplyAction
from pyof.v0x04.common.flow_match import OxmOfbMatchField, OxmTLV, VlanId
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
            'dl_vlan_pcp': OxmOfbMatchField.OFPXMT_OFB_VLAN_PCP}
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
                actions = self._actions_from_dict(data)
                instruction.actions.extend(list(actions))

        return flow_mod

    def _match_from_dict(self, dictionary):
        known_fields = ((field, data) for field, data in dictionary.items()
                        if field in self._match_names)
        for field_name, data in known_fields:
            tlv = OxmTLV()
            tlv.oxm_field = self._match_names[field_name]
            # set oxm_value
            if field_name == 'dl_vlan_pcp':
                tlv.oxm_value = data.to_bytes(1, 'big')
            elif field_name == 'dl_vlan':
                vid = data | VlanId.OFPVID_PRESENT
                tlv.oxm_value = vid.to_bytes(2, 'big')
            elif field_name in ('dl_src', 'dl_dst'):
                tlv.oxm_value = HWAddress(data).pack()
            elif field_name == 'in_port':
                tlv.oxm_value = data.to_bytes(4, 'big')
            else:
                tlv.oxm_value = data.to_bytes(2, 'big')
            yield tlv

    @classmethod
    def _actions_from_dict(cls, dictionary):
        for action_type, data in dictionary.items():
            action = cls._action_from_dict(action_type, data)
            if action:
                yield action

    @classmethod
    def _action_from_dict(cls, action_type, data):
        if action_type == 'set_vlan':
            tlv = cls._create_vlan_tlv(vlan_id=data)
            return ActionSetField(field=tlv)
        elif action_type == 'output':
            return ActionOutput(port=data)

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
        flow_dict['actions'] = self._actions_to_dict(flow_stats)
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
            else:
                data = int.from_bytes(field.oxm_value, 'big')
            match_dict[match_field] = data
        return match_dict

    def _actions_to_dict(self, flow_stats):
        actions_dict = {}
        for action in self._filter_actions(flow_stats):
            action_dict = self._action_to_dict(action)
            actions_dict.update(action_dict)
        return actions_dict

    @staticmethod
    def _action_to_dict(action):
        if action.action_type == ActionType.OFPAT_SET_FIELD:
            if action.field.oxm_field == OxmOfbMatchField.OFPXMT_OFB_VLAN_VID:
                data = int.from_bytes(action.field.oxm_value, 'big') & 4095
            return {'set_vlan': data}
        elif action.action_type == ActionType.OFPAT_OUTPUT:
            return {'output': action.port.value}
        return {}

    @staticmethod
    def _filter_actions(flow_stats):
        """Filter instructions and return a list of their actions."""
        instructions = (inst for inst in flow_stats.instructions
                        if inst.instruction_type == IType.OFPIT_APPLY_ACTIONS)
        action_lists = (instruction.actions for instruction in instructions)
        # Make a list from a list of lists
        return chain.from_iterable(action_lists)
