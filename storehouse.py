"""Module to handle the storehouse."""
import time

from kytos.core import log
from kytos.core.events import KytosEvent
from napps.kytos.flow_manager import settings

DEFAULT_BOX_RESTORE_TIMER = 0.1
BOX_RESTORE_ATTEMPTS = 10


class StoreHouse:
    """Class to handle storehouse."""

    @classmethod
    def __new__(cls, *args, **kwargs):
        # pylint: disable=unused-argument
        """Make this class a Singleton."""
        instance = cls.__dict__.get("__instance__")
        if instance is not None:
            return instance
        cls.__instance__ = instance = object.__new__(cls)
        return instance

    def __init__(self, controller):
        """Create a storehouse client instance."""
        self.controller = controller
        self.namespace = 'kytos.flow.persistence'
        self.box_restore_timer = getattr(settings, 'BOX_RESTORE_TIMER',
                                         DEFAULT_BOX_RESTORE_TIMER)

        if 'box' not in self.__dict__:
            self.box = None
        self.list_stored_boxes()

    def get_data(self):
        """Return the persistence box data."""
        # Wait retrieve or create box in storehouse
        i = 0
        while not self.box and i < BOX_RESTORE_ATTEMPTS:
            time.sleep(self.box_restore_timer)
            i += 1
        if not self.box:
            error = 'Error retrieving persistence box from storehouse.'
            log.error(error)
            raise FileNotFoundError(error)
        return self.box.data

    def create_box(self):
        """Create a persistence box to store administrative changes."""
        content = {'namespace': self.namespace,
                   'callback': self._create_box_callback,
                   'data': {}}
        event = KytosEvent(name='kytos.storehouse.create', content=content)
        self.controller.buffers.app.put(event)

    def _create_box_callback(self, _event, data, error):
        """Execute the callback to handle create_box."""
        if error:
            log.error(f'Can\'t create persistence'
                      f'box with namespace {self.namespace}')

        self.box = data

    def list_stored_boxes(self):
        """List all persistence box stored in storehouse."""
        name = 'kytos.storehouse.list'
        content = {'namespace': self.namespace,
                   'callback': self._get_or_create_a_box_from_list_of_boxes}

        event = KytosEvent(name=name, content=content)
        self.controller.buffers.app.put(event)

    def _get_or_create_a_box_from_list_of_boxes(self, _event, data, _error):
        """Create a persistence box or retrieve the stored box."""
        if data:
            self.get_stored_box(data[0])
        else:
            self.create_box()

    def get_stored_box(self, box_id):
        """Get persistence box from storehouse."""
        content = {'namespace': self.namespace,
                   'callback': self._get_box_callback,
                   'box_id': box_id,
                   'data': {}}
        name = 'kytos.storehouse.retrieve'
        event = KytosEvent(name=name, content=content)
        self.controller.buffers.app.put(event)

    def _get_box_callback(self, _event, data, error):
        """Handle get_box method saving the box or logging with the error."""
        if error:
            log.error('Persistence box not found.')

        self.box = data

    def save_flow(self, flows):
        """Save flows in storehouse."""
        self.box.data[flows['id']] = flows
        content = {'namespace': self.namespace,
                   'box_id': self.box.box_id,
                   'data': self.box.data,
                   'callback': self._save_flow_callback}

        event = KytosEvent(name='kytos.storehouse.update', content=content)
        self.controller.buffers.app.put(event)

    def _save_flow_callback(self, _event, data, error):
        """Display stored flow."""
        if error:
            log.error(f'Can\'t update persistence box {data.box_id}.')

        log.info(f'Flow saved in {self.namespace}.{data.box_id}')
