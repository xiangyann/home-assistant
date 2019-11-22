"""Support for Tesla door locks."""
import logging

from homeassistant.components.lock import LockDevice
from homeassistant.const import STATE_LOCKED, STATE_UNLOCKED

from . import DOMAIN as TESLA_DOMAIN, TeslaDevice

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Tesla lock platform."""
    devices = [
        TeslaLock(device, hass.data[TESLA_DOMAIN]["controller"])
        for device in hass.data[TESLA_DOMAIN]["devices"]["lock"]
    ]
    add_entities(devices, True)


class TeslaLock(TeslaDevice, LockDevice):
    """Representation of a Tesla door lock."""

    def __init__(self, tesla_device, controller):
        """Initialise of the lock."""
        self._state = None
        super().__init__(tesla_device, controller)

    async def async_lock(self, **kwargs):
        """Send the lock command."""
        _LOGGER.debug("Locking doors for: %s", self._name)
        await self.tesla_device.lock()

    async def async_unlock(self, **kwargs):
        """Send the unlock command."""
        _LOGGER.debug("Unlocking doors for: %s", self._name)
        await self.tesla_device.unlock()

    @property
    def is_locked(self):
        """Get whether the lock is in locked state."""
        return self._state == STATE_LOCKED

    async def async_update(self):
        """Update state of the lock."""
        _LOGGER.debug("Updating state for: %s", self._name)
        await super().async_update()
        self._state = STATE_LOCKED if self.tesla_device.is_locked() else STATE_UNLOCKED
