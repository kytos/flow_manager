"""Test Flow serializer for OF 1.0 methods."""
from unittest import TestCase
from unittest.mock import MagicMock, patch

from napps.kytos.flow_manager.serializers.v0x04 import FlowSerializer13


# pylint: disable=protected-access, unused-argument, no-member
class TestFlowSerializer13(TestCase):
    """Test the FlowSerializer13 class."""

    def setUp(self):
        """Execute steps before each tests."""
        self.napp = FlowSerializer13()

    @patch('napps.kytos.flow_manager.serializers.v0x04.ActionOutput')
    @patch('napps.kytos.flow_manager.serializers.v0x04.OxmTLV')
    @patch('napps.kytos.flow_manager.serializers.v0x04.InstructionApplyAction')
    @patch('napps.kytos.flow_manager.serializers.v0x04.FlowMod')
    def test_from_dict(self, *args):
        """Test from_dict method."""
        (mock_flow_mod, mock_instruction, _, _) = args
        flow_mod = MagicMock()
        flow_mod.instructions = []
        flow_mod.match.oxm_match_fields = []
        instruction = MagicMock()
        instruction.actions = []

        mock_flow_mod.return_value = flow_mod
        mock_instruction.return_value = instruction

        self.napp.flow_attributes = {'flow_attr'}
        self.napp._match_names = {'match_attr': 123}
        dictionary = {'flow_attr': 'any_data',
                      'match': {'match_attr': 123},
                      'actions': [{'action_type': 'output',
                                   'port': 'controller'}]}
        return_flow_mod = self.napp.from_dict(dictionary)

        self.assertEqual(return_flow_mod.flow_attr, 'any_data')
        self.assertEqual(len(return_flow_mod.match.oxm_match_fields), 1)
        self.assertEqual(len(return_flow_mod.instructions), 1)
        self.assertEqual(len(return_flow_mod.instructions[0].actions), 1)

    @patch('napps.kytos.flow_manager.serializers.v0x04.IPAddress')
    @patch('napps.kytos.flow_manager.serializers.v0x04.HWAddress')
    @patch('napps.kytos.flow_manager.serializers.v0x04.OxmTLV')
    def test_match_from_dict(self, *args):
        """Test _match_from_dict method."""
        (_, mock_hw_address, mock_ip_address) = args
        hw_address = MagicMock()
        hw_address.pack.return_value = 'hw_address'
        mock_hw_address.return_value = hw_address
        ip_address = MagicMock()
        ip_address.pack.return_value = 'ip_address'
        mock_ip_address.return_value = ip_address

        dictionary = {'dl_vlan_pcp': 0, 'nw_proto': 1, 'dl_vlan': 2,
                      'dl_src': 3, 'dl_dst': 4, 'nw_src': 5, 'nw_dst': 6,
                      'in_port': 7, 'dl_type': 8}

        tlv_generator = self.napp._match_from_dict(dictionary)

        self.assertEqual(next(tlv_generator).oxm_value, b'\x00')
        self.assertEqual(next(tlv_generator).oxm_value, b'\x01')
        self.assertEqual(next(tlv_generator).oxm_value, b'\x10\x02')
        self.assertEqual(next(tlv_generator).oxm_value, 'hw_address')
        self.assertEqual(next(tlv_generator).oxm_value, 'hw_address')
        self.assertEqual(next(tlv_generator).oxm_value, 'ip_address')
        self.assertEqual(next(tlv_generator).oxm_value, 'ip_address')
        self.assertEqual(next(tlv_generator).oxm_value, b'\x00\x00\x00\x07')
        self.assertEqual(next(tlv_generator).oxm_value, b'\x00\x08')

    @patch('napps.kytos.flow_manager.serializers.v0x04.ActionOutput')
    def test_actions_from_list(self, mock_action_output):
        """Test _actions_from_list method."""
        actions = [{'action_type': 'output', 'port': 'controller'}]
        generator = self.napp._actions_from_list(actions)
        return_action = next(generator)

        self.assertEqual(return_action, mock_action_output.return_value)

    @patch('napps.kytos.flow_manager.serializers.v0x04.ActionPopVLAN',
           return_value='action_pop_vlan')
    @patch('napps.kytos.flow_manager.serializers.v0x04.ActionPush',
           return_value='action_push')
    @patch('napps.kytos.flow_manager.serializers.v0x04.ActionOutput',
           return_value='action_output')
    @patch('napps.kytos.flow_manager.serializers.v0x04.ActionSetField',
           return_value='action_set_field')
    @patch('napps.kytos.flow_manager.serializers.v0x04.OxmTLV')
    def test_action_from_dict(self, *args):
        """Test _action_from_dict method."""
        (mock_oxm_tlv, mock_action_set_field, mock_action_output,
         mock_action_push, _) = args
        oxm_tlv = MagicMock()
        mock_oxm_tlv.return_value = oxm_tlv

        action_1 = {'action_type': 'set_vlan', 'vlan_id': 123}
        return_1 = self.napp._action_from_dict(action_1)
        mock_action_set_field.assert_called_with(field=oxm_tlv)
        self.assertEqual(return_1, 'action_set_field')

        action_2 = {'action_type': 'output', 'port': 'controller'}
        return_2 = self.napp._action_from_dict(action_2)
        mock_action_output.assert_called_with(port=0xfffffffd)
        self.assertEqual(return_2, 'action_output')

        action_3 = {'action_type': 'output', 'port': 'any'}
        return_3 = self.napp._action_from_dict(action_3)
        mock_action_output.assert_called_with(port='any')
        self.assertEqual(return_3, 'action_output')

        action_4 = {'action_type': 'push_vlan', 'tag_type': 's'}
        return_4 = self.napp._action_from_dict(action_4)
        mock_action_push.assert_called_with(action_type=17, ethertype=0x88a8)
        self.assertEqual(return_4, 'action_push')

        action_5 = {'action_type': 'push_vlan', 'tag_type': 'c'}
        return_5 = self.napp._action_from_dict(action_5)
        mock_action_push.assert_called_with(action_type=17, ethertype=0x8100)
        self.assertEqual(return_5, 'action_push')

        action_6 = {'action_type': 'pop_vlan'}
        return_6 = self.napp._action_from_dict(action_6)
        self.assertEqual(return_6, 'action_pop_vlan')

    @patch('napps.kytos.flow_manager.serializers.v0x04.OxmTLV')
    def test_create_vlan_tlv(self, mock_oxm_tlv):
        """Test _create_vlan_tlv method."""
        tlv = self.napp._create_vlan_tlv(1)

        self.assertEqual(tlv.oxm_field, 6)
        self.assertEqual(tlv.oxm_value, b'\x10\x01')

    @patch('napps.kytos.flow_manager.serializers.v0x04.FlowSerializer13.'
           '_actions_to_list', return_value='actions_to_list')
    @patch('napps.kytos.flow_manager.serializers.v0x04.FlowSerializer13.'
           '_match_to_dict', return_value='match_to_dict')
    def test_to_dict(self, *args):
        """Test to_dict method."""
        (_, _) = args
        flow_stats = MagicMock()
        flow_stats.flow_attr = MagicMock()
        self.napp.flow_attributes = {'flow_attr'}

        flow_dict = self.napp.to_dict(flow_stats)

        expected = {'flow_attr': flow_stats.flow_attr.value,
                    'match': 'match_to_dict',
                    'actions': 'actions_to_list'}
        self.assertEqual(flow_dict, expected)

    @patch('napps.kytos.flow_manager.serializers.v0x04.HWAddress')
    @patch('napps.kytos.flow_manager.serializers.v0x04.IPAddress')
    def test_match_to_dict(self, *args):
        """Test _match_to_dict method."""
        (mock_ip_address, mock_hw_address) = args
        ip_address = MagicMock()
        hw_address = MagicMock()
        mock_ip_address.return_value = ip_address
        mock_hw_address.return_value = hw_address

        flow_stats = MagicMock()
        flow_stats.match.oxm_match_fields = []
        for oxm_field in [0, 6, 4, 3, 11, 12]:
            field = MagicMock()
            field.oxm_field = oxm_field
            flow_stats.match.oxm_match_fields.append(field)

        match_dict = self.napp._match_to_dict(flow_stats)
        expected = {'in_port': 0, 'dl_vlan': 0, 'dl_src': str(hw_address),
                    'dl_dst': str(hw_address), 'nw_src': str(ip_address),
                    'nw_dst': str(ip_address)}

        self.assertEqual(match_dict, expected)

    @patch('napps.kytos.flow_manager.serializers.v0x04.FlowSerializer13.'
           '_filter_actions')
    def test_actions_to_list(self, mock_filter_actions):
        """Test _actions_to_list method."""
        flow_stats = MagicMock()
        action = MagicMock()
        action.action_type = 0
        action.port = 0xfffffffd
        mock_filter_actions.return_value = [action]

        actions_list = self.napp._actions_to_list(flow_stats)

        expected = [{'action_type': 'output', 'port': 'controller'}]
        self.assertEqual(actions_list, expected)

    def test_action_to_dict(self):
        """Test _action_to_dict method."""
        action_1 = MagicMock()
        action_1.action_type = 25
        action_1.field.oxm_field = 6
        action_1.field.oxm_value = b'\x01'
        return_1 = self.napp._action_to_dict(action_1)
        expected = {'action_type': 'set_vlan', 'vlan_id': 1}
        self.assertEqual(return_1, expected)

        action_2 = MagicMock()
        action_2.action_type = 0
        action_2.port = 0xfffffffd
        return_2 = self.napp._action_to_dict(action_2)
        expected = {'action_type': 'output', 'port': 'controller'}
        self.assertEqual(return_2, expected)

        action_3 = MagicMock()
        action_3.action_type = 0
        action_3.port.value = 'any'
        return_3 = self.napp._action_to_dict(action_3)
        expected = {'action_type': 'output', 'port': 'any'}
        self.assertEqual(return_3, expected)

        action_4 = MagicMock()
        action_4.action_type = 17
        action_4.ethertype = 0x88a8
        return_4 = self.napp._action_to_dict(action_4)
        expected = {'action_type': 'push_vlan', 'tag_type': 's'}
        self.assertEqual(return_4, expected)

        action_5 = MagicMock()
        action_5.action_type = 17
        action_5.ethertype = 'any'
        return_5 = self.napp._action_to_dict(action_5)
        expected = {'action_type': 'push_vlan', 'tag_type': 'c'}
        self.assertEqual(return_5, expected)

        action_6 = MagicMock()
        action_6.action_type = 18
        return_6 = self.napp._action_to_dict(action_6)
        expected = {'action_type': 'pop_vlan'}
        self.assertEqual(return_6, expected)

        action_7 = MagicMock()
        action_7.action_type = 'any'
        return_7 = self.napp._action_to_dict(action_7)
        self.assertEqual(return_7, {})

    def test_filter_actions(self):
        """Test _filter_actions method."""
        action = MagicMock()
        action.action_type = 0
        action.port = 0xfffffffd
        instruction = MagicMock()
        instruction.instruction_type = 4
        instruction.actions = [action]
        flow_stats = MagicMock()
        flow_stats.instructions = [instruction]

        action_list = self.napp._filter_actions(flow_stats)

        self.assertEqual(list(action_list), instruction.actions)
