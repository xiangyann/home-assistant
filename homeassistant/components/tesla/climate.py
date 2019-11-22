"""Support for Tesla HVAC system."""
import logging

from homeassistant.components.climate import ClimateDevice
from homeassistant.components.climate.const import (
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    SUPPORT_TARGET_TEMPERATURE,
)
from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS, TEMP_FAHRENHEIT

from . import DOMAIN as TESLA_DOMAIN, TeslaDevice

_LOGGER = logging.getLogger(__name__)

SUPPORT_HVAC = [HVAC_MODE_HEAT, HVAC_MODE_OFF]


async def async_setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Tesla climate platform."""
    devices = [
        TeslaThermostat(device, hass.data[TESLA_DOMAIN]["controller"])
        for device in hass.data[TESLA_DOMAIN]["devices"]["climate"]
    ]
    add_entities(devices, True)


class TeslaThermostat(TeslaDevice, ClimateDevice):
    """Representation of a Tesla climate."""

    def __init__(self, tesla_device, controller):
        """Initialize the Tesla device."""
        super().__init__(tesla_device, controller)
        self._target_temperature = None
        self._temperature = None

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_TARGET_TEMPERATURE

    @property
    def hvac_mode(self):
        """Return hvac operation ie. heat, cool mode.

        Need to be one of HVAC_MODE_*.
        """
        if self.tesla_device.is_hvac_enabled():
            return HVAC_MODE_HEAT
        return HVAC_MODE_OFF

    @property
    def hvac_modes(self):
        """Return the list of available hvac operation modes.

        Need to be a subset of HVAC_MODES.
        """
        return SUPPORT_HVAC

    async def async_update(self):
        """Call by the Tesla device callback to update state."""
        _LOGGER.debug("Updating: %s", self._name)
        await super().async_update()
        self._target_temperature = self.tesla_device.get_goal_temp()
        self._temperature = self.tesla_device.get_current_temp()

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        tesla_temp_units = self.tesla_device.measurement

        if tesla_temp_units == "F":
            return TEMP_FAHRENHEIT
        return TEMP_CELSIUS

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._temperature

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temperature

    async def async_set_temperature(self, **kwargs):
        """Set new target temperatures."""
        _LOGGER.debug("Setting temperature for: %s", self._name)
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature:
            await self.tesla_device.set_temperature(temperature)

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        _LOGGER.debug("Setting mode for: %s", self._name)
        if hvac_mode == HVAC_MODE_OFF:
            await self.tesla_device.set_status(False)
        elif hvac_mode == HVAC_MODE_HEAT:
            await self.tesla_device.set_status(True)
