"""Flow serializer for OF 1.0."""
from pyof.v0x01.common.action import ActionOutput, ActionType, ActionVlanVid
from pyof.v0x01.controller2switch.flow_mod import FlowMod

from napps.kytos.flow_manager.serializers.base import FlowSerializer


class FlowSerializer10(FlowSerializer):
    """Flow serializer for OpenFlow 1.0."""

    def __init__(self):
        """Initialize OF 1.0 specific variables."""
        super().__init__()
        self.match_attributes = set((
            'in_port',
            'dl_src',
            'dl_dst',
            'dl_type',
            'dl_vlan',
            'dl_vlan_pcp',
            'nw_src',
            'nw_dst',
            'nw_proto'))

    def from_dict(self, dictionary):
        """Return an OF 1.0 FlowMod message from serialized dictionary."""
        flow_mod = FlowMod()
        for field, data in dictionary.items():
            if field in self.flow_attributes:
                setattr(flow_mod, field, data)
            elif field == 'match':
                self._update_match(flow_mod.match, data)
            elif field == 'actions':
                actions = self._actions_from_list(data)
                flow_mod.actions.extend(actions)
        return flow_mod

    def _update_match(self, match, dictionary):
        """Update match attributes found in dictionary."""
        for field, data in dictionary.items():
            if field in self.match_attributes:
                setattr(match, field, data)

    @staticmethod
    def _actions_from_list(action_list):
        """Return actions found in the action list."""
        actions = []
        for action in action_list:
            if action['type'] == 'set_vlan':
                new_action = ActionVlanVid(vlan_id=action['value'])
            elif action['type'] == 'output':
                new_action = ActionOutput(port=action['value'])
            else:
                continue
            actions.append(new_action)
        return actions

    def to_dict(self, flow_stats):
        """Return a dictionary created from OF 1.0 FlowStats."""
        flow_dict = {field: data.value
                     for field, data in vars(flow_stats).items()
                     if field in self.flow_attributes}

        match_dict = {}
        for field, data in vars(flow_stats.match).items():
            if field in self.match_attributes:
                match_dict[field] = data.value

        actions_list = []
        for action in flow_stats.actions:
            if action.action_type == ActionType.OFPAT_SET_VLAN_VID:
                actions_list.append({'type': 'set_vlan', 'value':
                                     action.vlan_id.value})
            elif action.action_type == ActionType.OFPAT_OUTPUT:
                actions_list.append({'type': 'output', 'value':
                                     action.port.value})

        flow_dict.update({'match': match_dict, 'actions': actions_list})
        return flow_dict
