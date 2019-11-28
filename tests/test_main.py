"""Module to test the main napp file."""
from unittest import TestCase
from unittest.mock import Mock

from kytos.core import Controller
from kytos.core.config import KytosConfig

from napps.kytos.flow_manager.main import Main


class TestMain(TestCase):
    """Test the Main class."""

    def setUp(self):
        """Execute steps before each tests.
        """
        self.napp = Main(self.get_controller_mock())

    @staticmethod
    def get_controller_mock():
        """Return a controller mock."""
        options = KytosConfig().options['daemon']
        controller = Controller(options)
        controller.log = Mock()
        return controller

    def test_add_flow_mod_sent_ok(self):
        self.napp._flow_mods_sent_max_size = 3
        flow = Mock()
        xid = '12345'
        initial_len = len(self.napp._flow_mods_sent)
        self.napp._add_flow_mod_sent(xid, flow)

        assert len(self.napp._flow_mods_sent) == initial_len + 1
        assert self.napp._flow_mods_sent.get(xid, None) == flow

    def test_add_flow_mod_sent_overlimit(self):
        self.napp._flow_mods_sent_max_size = 5
        xid = '23456'
        while len(self.napp._flow_mods_sent) < 5:
            xid += '1'
            flow = Mock()
            self.napp._add_flow_mod_sent(xid, flow)

        xid = '90876'
        flow = Mock()
        initial_len = len(self.napp._flow_mods_sent)
        self.napp._add_flow_mod_sent(xid, flow)

        assert len(self.napp._flow_mods_sent) == initial_len
        assert self.napp._flow_mods_sent.get(xid, None) == flow
