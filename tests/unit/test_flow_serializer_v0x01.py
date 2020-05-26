"""Test Flow serializer for OF 1.0 methods."""
from unittest import TestCase
from unittest.mock import MagicMock, patch

from napps.kytos.flow_manager.serializers.v0x01 import FlowSerializer10


# pylint: disable=protected-access, no-member
class TestFlowSerializer10(TestCase):
    """Test the FlowSerializer10 class."""

    def setUp(self):
        """Execute steps before each tests."""
        self.napp = FlowSerializer10()

    @patch('napps.kytos.flow_manager.serializers.v0x01.ActionOutput')
    @patch('napps.kytos.flow_manager.serializers.v0x01.FlowMod')
    def test_from_dict(self, *args):
        """Test from_dict method."""
        (mock_flow_mod, _) = args
        flow_mod = MagicMock()
        flow_mod.actions = []
        mock_flow_mod.return_value = flow_mod

        self.napp.flow_attributes = {'flow_attr'}
        self.napp.match_attributes = {'match_attr'}
        dictionary = {'flow_attr': 'any_data',
                      'match': {'match_attr': 123},
                      'actions': [{'action_type': 'output',
                                   'port': 'controller'}]}
        return_flow_mod = self.napp.from_dict(dictionary)

        self.assertEqual(return_flow_mod.flow_attr, 'any_data')
        self.assertEqual(return_flow_mod.match.match_attr, 123)
        self.assertEqual(len(return_flow_mod.actions), 1)

    def test_update_match(self):
        """Test _update_match method."""
        match = MagicMock()
        dictionary = {'attr': 'data'}
        self.napp.match_attributes = {'attr'}

        self.napp._update_match(match, dictionary)

        self.assertEqual(match.attr, 'data')

    @patch('napps.kytos.flow_manager.serializers.v0x01.ActionOutput')
    @patch('napps.kytos.flow_manager.serializers.v0x01.ActionVlanVid')
    def test_actions_from_list(self, *args):
        """Test _actions_from_list method."""
        (mock_action_vlan_vid, mock_action_output) = args
        mock_action_vlan_vid.return_value = 'action_vlan_vid'
        mock_action_output.side_effect = ['action_output_controller',
                                          'action_output_any']
        actions = [{'action_type': 'set_vlan', 'vlan_id': 'id'},
                   {'action_type': 'output', 'port': 'controller'},
                   {'action_type': 'output', 'port': 'any'},
                   {'action_type': 'any'}]

        return_actions = self.napp._actions_from_list(actions)

        expected_actions = ['action_vlan_vid', 'action_output_controller',
                            'action_output_any']
        self.assertEqual(return_actions, expected_actions)

    def test_to_dict(self):
        """Test to_dict method."""
        action_1 = MagicMock()
        action_1.action_type = 1
        action_1.vlan_id.value = 'id'

        action_2 = MagicMock()
        action_2.action_type = 0
        action_2.port = 0xfffd

        action_3 = MagicMock()
        action_3.action_type = 0
        action_3.port.value = 'port'

        flow_stats = MagicMock()
        flow_stats.actions = [action_1, action_2, action_3]
        flow_stats.flow_attr = MagicMock()
        flow_stats.match.match_attr = MagicMock()
        self.napp.flow_attributes = {'flow_attr'}
        self.napp.match_attributes = {'match_attr'}

        flow_dict = self.napp.to_dict(flow_stats)

        expected = {'flow_attr': flow_stats.flow_attr.value,
                    'match': {'match_attr': flow_stats.match.match_attr.value},
                    'actions': [{'action_type': 'set_vlan', 'vlan_id': 'id'},
                                {'action_type': 'output',
                                 'port': 'controller'},
                                {'action_type': 'output', 'port': 'port'}]}

        self.assertEqual(flow_dict, expected)
