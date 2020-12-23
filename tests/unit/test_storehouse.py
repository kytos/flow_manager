"""Module to test the storehouse client."""
from unittest import TestCase
from unittest.mock import MagicMock, PropertyMock, patch

from kytos.lib.helpers import get_controller_mock


# pylint: disable=too-many-public-methods
class TestStoreHouse(TestCase):
    """Test the Main class."""

    def setUp(self):
        """Execute steps before each tests.

        Set the server_name_url_url from kytos/flow_manager
        """
        self.server_name_url = 'http://localhost:8181/api/kytos/flow_manager'

        patch('kytos.core.helpers.run_on_thread', lambda x: x).start()
        # pylint: disable=import-outside-toplevel
        from napps.kytos.flow_manager.storehouse import StoreHouse
        self.addCleanup(patch.stopall)

        self.napp = StoreHouse(get_controller_mock())

    @patch('napps.kytos.flow_manager.storehouse.StoreHouse.get_stored_box')
    def test_get_data(self, mock_get_stored_box):
        """Test get_data."""
        mock_box = MagicMock()
        box_data = MagicMock()
        mock_get_stored_box.return_value = True
        type(box_data).data = PropertyMock(side_effect=[{}, "box"])
        type(mock_box).data = PropertyMock(return_value=box_data)
        self.napp.box = mock_box
        response = self.napp.get_data()
        self.assertEqual(response.data, {})

        response = self.napp.get_data()
        self.assertEqual(response.data, "box")

    @patch('napps.kytos.flow_manager.storehouse.KytosEvent')
    @patch('kytos.core.buffers.KytosEventBuffer.put')
    def test_create_box(self, *args):
        """Test create_box."""
        (mock_buffers_put, mock_event) = args
        self.napp.create_box()
        mock_event.assert_called()
        mock_buffers_put.assert_called()

    # pylint: disable = protected-access
    @patch('napps.kytos.flow_manager.storehouse.StoreHouse.get_stored_box')
    @patch('napps.kytos.flow_manager.storehouse.StoreHouse.create_box')
    def test_get_or_create_a_box_from_list_of_boxes(self, *args):
        """Test create_box."""
        (mock_create_box, mock_get_stored_box) = args
        mock_event = MagicMock()
        mock_data = MagicMock()
        mock_error = MagicMock()
        self.napp._get_or_create_a_box_from_list_of_boxes(mock_event,
                                                          mock_data,
                                                          mock_error)
        mock_get_stored_box.assert_called()
        self.napp._get_or_create_a_box_from_list_of_boxes(mock_event,
                                                          None,
                                                          mock_error)
        mock_create_box.assert_called()

    @patch('napps.kytos.flow_manager.storehouse.KytosEvent')
    @patch('kytos.core.buffers.KytosEventBuffer.put')
    def test_get_stored_box(self, *args):
        """Test get_stored_box."""
        (mock_buffers_put, mock_event) = args
        mock_box = MagicMock()
        self.napp.get_stored_box(mock_box)
        mock_event.assert_called()
        mock_buffers_put.assert_called()

    @patch('napps.kytos.flow_manager.storehouse.KytosEvent')
    @patch('kytos.core.buffers.KytosEventBuffer.put')
    def test_save_flow(self, *args):
        """Test save_status."""
        (mock_buffers_put, mock_event) = args
        mock_status = MagicMock()
        self.napp.save_flow(mock_status)
        mock_event.assert_called()
        mock_buffers_put.assert_called()
