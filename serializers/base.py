"""Abstract class for serializing flows."""
from abc import ABC, abstractmethod

from pyof.v0x01.controller2switch.flow_mod import \
    FlowModCommand as CommonFlowModCommand


class FlowSerializer(ABC):
    """Common code for OF 1.0 and 1.3 flow serialization.

    For a FlowMod dictionary, create a FlowMod message and, for a FlowStats,
    create a dictionary.
    """

    # These values are the same in both versions 1.0 and 1.3
    OFPFC_ADD = CommonFlowModCommand.OFPFC_ADD
    OFPFC_DELETE = CommonFlowModCommand.OFPFC_DELETE

    def __init__(self):
        """Initialize common attributes of 1.0 and 1.3 versions."""
        self.flow_attributes = set(('table_id', 'priority', 'idle_timeout',
                                   'hard_timeout', 'cookie'))

    @abstractmethod
    def from_dict(self, dictionary):
        """Return a FlowMod instance created from a serialized dictionary."""
        pass

    @abstractmethod
    def to_dict(self, flow_stats):
        """Return a serialized dictionary for a FlowStats message."""
        pass
