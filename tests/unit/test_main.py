"""Test Main methods."""
from unittest import TestCase
from unittest.mock import MagicMock, patch

from kytos.lib.helpers import (get_controller_mock, get_kytos_event_mock,
                               get_switch_mock, get_test_client)


# pylint: disable=protected-access
class TestMain(TestCase):
    """Tests for the Main class."""

    API_URL = 'http://localhost:8181/api/kytos/flow_manager'

    def setUp(self):
        patch('kytos.core.helpers.run_on_thread', lambda x: x).start()
        # pylint: disable=import-outside-toplevel
        from napps.kytos.flow_manager.main import Main

        self.addCleanup(patch.stopall)

        controller = get_controller_mock()
        self.switch_01 = get_switch_mock("00:00:00:00:00:00:00:01", 0x04)
        self.switch_01.is_enabled.return_value = True
        self.switch_01.flows = []

        self.switch_02 = get_switch_mock("00:00:00:00:00:00:00:02", 0x04)
        self.switch_02.is_enabled.return_value = False
        self.switch_02.flows = []

        controller.switches = {"00:00:00:00:00:00:00:01": self.switch_01,
                               "00:00:00:00:00:00:00:02": self.switch_02}

        self.napp = Main(controller)

    def test_rest_list_without_dpid(self):
        """Test list rest method withoud dpid."""
        flow_1 = MagicMock()
        flow_1.as_dict.return_value = {'flow_1': 'data'}
        flow_2 = MagicMock()
        flow_2.as_dict.return_value = {'flow_2': 'data'}
        self.switch_01.flows.append(flow_1)
        self.switch_02.flows.append(flow_2)

        api = get_test_client(self.napp.controller, self.napp)
        url = f'{self.API_URL}/v2/flows'

        response = api.get(url)
        expected = {'00:00:00:00:00:00:00:01': {'flows': [{'flow_1': 'data'}]},
                    '00:00:00:00:00:00:00:02': {'flows': [{'flow_2': 'data'}]}}

        self.assertEqual(response.json, expected)
        self.assertEqual(response.status_code, 200)

    def test_rest_list_with_dpid(self):
        """Test list rest method with dpid."""
        flow_1 = MagicMock()
        flow_1.as_dict.return_value = {'flow_1': 'data'}
        self.switch_01.flows.append(flow_1)

        api = get_test_client(self.napp.controller, self.napp)
        url = f'{self.API_URL}/v2/flows/00:00:00:00:00:00:00:01'

        response = api.get(url)
        expected = {'00:00:00:00:00:00:00:01': {'flows': [{'flow_1': 'data'}]}}

        self.assertEqual(response.json, expected)
        self.assertEqual(response.status_code, 200)

    @patch('napps.kytos.flow_manager.main.Main._install_flows')
    def test_rest_add_and_delete_without_dpid(self, mock_install_flows):
        """Test add and delete rest method without dpid."""
        api = get_test_client(self.napp.controller, self.napp)

        for method in ['flows', 'delete']:
            url = f'{self.API_URL}/v2/{method}'

            response_1 = api.post(url, json={'data': '123'})
            response_2 = api.post(url)

            self.assertEqual(response_1.status_code, 200)
            self.assertEqual(response_2.status_code, 404)

        self.assertEqual(mock_install_flows.call_count, 2)

    @patch('napps.kytos.flow_manager.main.Main._install_flows')
    def test_rest_add_and_delete_with_dpid(self, mock_install_flows):
        """Test add and delete rest method with dpid."""
        api = get_test_client(self.napp.controller, self.napp)

        for method in ['flows', 'delete']:
            url_1 = f'{self.API_URL}/v2/{method}/00:00:00:00:00:00:00:01'
            url_2 = f'{self.API_URL}/v2/{method}/00:00:00:00:00:00:00:02'
            url_3 = f'{self.API_URL}/v2/{method}/00:00:00:00:00:00:00:03'

            response_1 = api.post(url_1)
            response_2 = api.post(url_1, json={'data': '123'})
            response_3 = api.post(url_2, json={'data': '123'})
            response_4 = api.post(url_3, json={'data': '123'})

            self.assertEqual(response_1.status_code, 404)
            self.assertEqual(response_2.status_code, 200)
            self.assertEqual(response_3.status_code, 404)
            self.assertEqual(response_4.status_code, 404)

        self.assertEqual(mock_install_flows.call_count, 2)

    def test_get_all_switches_enabled(self):
        """Test _get_all_switches_enabled method."""
        switches = self.napp._get_all_switches_enabled()

        self.assertEqual(switches, [self.switch_01])

    @patch('napps.kytos.flow_manager.main.Main._store_changed_flows')
    @patch('napps.kytos.flow_manager.main.Main._send_napp_event')
    @patch('napps.kytos.flow_manager.main.Main._add_flow_mod_sent')
    @patch('napps.kytos.flow_manager.main.Main._send_flow_mod')
    @patch('napps.kytos.flow_manager.main.FlowFactory.get_class')
    def test_install_flows(self, *args):
        """Test _install_flows method."""
        (mock_flow_factory, mock_send_flow_mod, mock_add_flow_mod_sent,
         mock_send_napp_event, _) = args
        serializer = MagicMock()
        flow = MagicMock()
        flow_mod = MagicMock()

        flow.as_of_add_flow_mod.return_value = flow_mod
        serializer.from_dict.return_value = flow
        mock_flow_factory.return_value = serializer

        flows_dict = {'flows': [MagicMock()]}
        switches = [self.switch_01]
        self.napp._install_flows('add', flows_dict, switches)

        mock_send_flow_mod.assert_called_with(flow.switch, flow_mod)
        mock_add_flow_mod_sent.assert_called_with(flow_mod.header.xid,
                                                  flow, 'add')
        mock_send_napp_event.assert_called_with(self.switch_01, flow, 'add')

    def test_add_flow_mod_sent(self):
        """Test _add_flow_mod_sent method."""
        xid = 0
        flow = MagicMock()

        self.napp._add_flow_mod_sent(xid, flow, 'add')

        self.assertEqual(self.napp._flow_mods_sent[xid], (flow, 'add'))

    @patch('kytos.core.buffers.KytosEventBuffer.put')
    def test_send_flow_mod(self, mock_buffers_put):
        """Test _send_flow_mod method."""
        switch = get_switch_mock("00:00:00:00:00:00:00:01", 0x04)
        flow_mod = MagicMock()

        self.napp._send_flow_mod(switch, flow_mod)

        mock_buffers_put.assert_called()

    @patch('kytos.core.buffers.KytosEventBuffer.put')
    def test_send_napp_event(self, mock_buffers_put):
        """Test _send_napp_event method."""
        switch = get_switch_mock("00:00:00:00:00:00:00:01", 0x04)
        flow = MagicMock()

        for command in ['add', 'delete', 'error']:
            self.napp._send_napp_event(switch, flow, command)

        self.assertEqual(mock_buffers_put.call_count, 3)

    @patch('napps.kytos.flow_manager.main.Main._send_napp_event')
    def test_handle_errors(self, mock_send_napp_event):
        """Test handle_errors method."""
        flow = MagicMock()
        self.napp._flow_mods_sent[0] = (flow, 'add')

        message = MagicMock()
        message.header.xid.value = 0
        message.error_type = 2
        message.code = 5
        event = get_kytos_event_mock(name='.*.of_core.*.ofpt_error',
                                     content={'message': message})
        self.napp.handle_errors(event)

        mock_send_napp_event.assert_called_with(flow.switch, flow, 'error',
                                                error_command='add',
                                                error_code=5, error_type=2)

    @patch("napps.kytos.flow_manager.main.StoreHouse.get_data")
    def test_load_flows(self, mock_storehouse):
        """Test load flows."""
        self.napp._load_flows()
        mock_storehouse.assert_called()

    @patch("napps.kytos.flow_manager.main.Main._install_flows")
    def test_resend_stored_flows(self, mock_install_flows):
        """Test resend stored flows."""
        dpid = "00:00:00:00:00:00:00:01"
        switch = get_switch_mock(dpid, 0x04)
        mock_event = MagicMock()
        flow = {"command": "add", "flow": MagicMock()}

        flows = {"flow_list": [flow]}
        mock_event.content = {"switch": switch}
        self.napp.controller.switches = {dpid: switch}
        self.napp.stored_flows = {dpid: flows}
        self.napp.resend_stored_flows(mock_event)
        mock_install_flows.assert_called()

    @patch("napps.kytos.of_core.flow.FlowFactory.get_class")
    @patch("napps.kytos.flow_manager.main.StoreHouse.save_flow")
    def test_store_changed_flows(self, mock_save_flow, _):
        """Test store changed flows."""
        dpid = "00:00:00:00:00:00:00:01"
        switch = get_switch_mock(dpid, 0x04)
        switch.id = dpid
        flow = {
            "priority": 17,
            "cookie": 84114964,
            "command": "add",
            "match": {"dl_dst": "00:15:af:d5:38:98"},
        }
        match_fields = {
            "priority": 17,
            "cookie": 84114964,
            "command": "add",
            "dl_dst": "00:15:af:d5:38:98",
        }
        flows = {"flow": flow}

        command = "add"
        flow_list = {
            "flow_list": [
                {"match_fields": match_fields, "command": "delete",
                 "flow": flow}
            ]
        }
        self.napp.stored_flows = {dpid: flow_list}
        self.napp._store_changed_flows(command, flows, switch)
        mock_save_flow.assert_called()

        self.napp.stored_flows = {}
        self.napp._store_changed_flows(command, flows, switch)
        mock_save_flow.assert_called()
