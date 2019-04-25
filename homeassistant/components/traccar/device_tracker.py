"""Support for Traccar device tracking."""
from datetime import datetime, timedelta
import logging

import voluptuous as vol

from homeassistant.components.device_tracker import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_HOST, CONF_PORT, CONF_SSL, CONF_VERIFY_SSL,
    CONF_PASSWORD, CONF_USERNAME, ATTR_BATTERY_LEVEL,
    CONF_SCAN_INTERVAL, CONF_MONITORED_CONDITIONS,
    CONF_EVENT)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import slugify


_LOGGER = logging.getLogger(__name__)

ATTR_ADDRESS = 'address'
ATTR_CATEGORY = 'category'
ATTR_GEOFENCE = 'geofence'
ATTR_MOTION = 'motion'
ATTR_SPEED = 'speed'
ATTR_TRACKER = 'tracker'
ATTR_TRACCAR_ID = 'traccar_id'
ATTR_STATUS = 'status'

EVENT_DEVICE_MOVING = 'device_moving'
EVENT_COMMAND_RESULT = 'command_result'
EVENT_DEVICE_FUEL_DROP = 'device_fuel_drop'
EVENT_GEOFENCE_ENTER = 'geofence_enter'
EVENT_DEVICE_OFFLINE = 'device_offline'
EVENT_DRIVER_CHANGED = 'driver_changed'
EVENT_GEOFENCE_EXIT = 'geofence_exit'
EVENT_DEVICE_OVERSPEED = 'device_overspeed'
EVENT_DEVICE_ONLINE = 'device_online'
EVENT_DEVICE_STOPPED = 'device_stopped'
EVENT_MAINTENANCE = 'maintenance'
EVENT_ALARM = 'alarm'
EVENT_TEXT_MESSAGE = 'text_message'
EVENT_DEVICE_UNKNOWN = 'device_unknown'
EVENT_IGNITION_OFF = 'ignition_off'
EVENT_IGNITION_ON = 'ignition_on'
EVENT_ALL_EVENTS = 'all_events'

DEFAULT_SCAN_INTERVAL = timedelta(seconds=30)
SCAN_INTERVAL = DEFAULT_SCAN_INTERVAL

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_PORT, default=8082): cv.port,
    vol.Optional(CONF_SSL, default=False): cv.boolean,
    vol.Optional(CONF_VERIFY_SSL, default=True): cv.boolean,
    vol.Optional(CONF_MONITORED_CONDITIONS,
                 default=[]): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_EVENT,
                 default=[]): vol.All(cv.ensure_list,
                                      [vol.Any(EVENT_DEVICE_MOVING,
                                               EVENT_COMMAND_RESULT,
                                               EVENT_DEVICE_FUEL_DROP,
                                               EVENT_GEOFENCE_ENTER,
                                               EVENT_DEVICE_OFFLINE,
                                               EVENT_DRIVER_CHANGED,
                                               EVENT_GEOFENCE_EXIT,
                                               EVENT_DEVICE_OVERSPEED,
                                               EVENT_DEVICE_ONLINE,
                                               EVENT_DEVICE_STOPPED,
                                               EVENT_MAINTENANCE,
                                               EVENT_ALARM,
                                               EVENT_TEXT_MESSAGE,
                                               EVENT_DEVICE_UNKNOWN,
                                               EVENT_IGNITION_OFF,
                                               EVENT_IGNITION_ON,
                                               EVENT_ALL_EVENTS)]),
})


async def async_setup_scanner(hass, config, async_see, discovery_info=None):
    """Validate the configuration and return a Traccar scanner."""
    from pytraccar.api import API

    session = async_get_clientsession(hass, config[CONF_VERIFY_SSL])

    api = API(hass.loop, session, config[CONF_USERNAME], config[CONF_PASSWORD],
              config[CONF_HOST], config[CONF_PORT], config[CONF_SSL])

    scanner = TraccarScanner(
        api, hass, async_see,
        config.get(CONF_SCAN_INTERVAL, SCAN_INTERVAL),
        config[CONF_MONITORED_CONDITIONS], config[CONF_EVENT])

    return await scanner.async_init()


class TraccarScanner:
    """Define an object to retrieve Traccar data."""

    def __init__(self, api, hass, async_see, scan_interval,
                 custom_attributes,
                 event_types):
        """Initialize."""
        from stringcase import camelcase
        self._event_types = {camelcase(evt): evt for evt in event_types}
        self._custom_attributes = custom_attributes
        self._scan_interval = scan_interval
        self._async_see = async_see
        self._api = api
        self.connected = False
        self._hass = hass

    async def async_init(self):
        """Further initialize connection to Traccar."""
        await self._api.test_connection()
        if self._api.connected and not self._api.authenticated:
            _LOGGER.error("Authentication for Traccar failed")
            return False

        await self._async_update()
        async_track_time_interval(self._hass,
                                  self._async_update,
                                  self._scan_interval)
        return True

    async def _async_update(self, now=None):
        """Update info from Traccar."""
        if not self.connected:
            _LOGGER.debug('Testing connection to Traccar')
            await self._api.test_connection()
            self.connected = self._api.connected
            if self.connected:
                _LOGGER.info("Connection to Traccar restored")
            else:
                return
        _LOGGER.debug('Updating device data')
        await self._api.get_device_info(self._custom_attributes)
        self._hass.async_create_task(self.import_device_data())
        if self._event_types:
            self._hass.async_create_task(self.import_events())
        self.connected = self._api.connected

    async def import_device_data(self):
        """Import device data from Traccar."""
        for device_unique_id in self._api.device_info:
            device_info = self._api.device_info[device_unique_id]
            device = None
            attr = {}
            attr[ATTR_TRACKER] = 'traccar'
            if device_info.get('address') is not None:
                attr[ATTR_ADDRESS] = device_info['address']
            if device_info.get('geofence') is not None:
                attr[ATTR_GEOFENCE] = device_info['geofence']
            if device_info.get('category') is not None:
                attr[ATTR_CATEGORY] = device_info['category']
            if device_info.get('speed') is not None:
                attr[ATTR_SPEED] = device_info['speed']
            if device_info.get('battery') is not None:
                attr[ATTR_BATTERY_LEVEL] = device_info['battery']
            if device_info.get('motion') is not None:
                attr[ATTR_MOTION] = device_info['motion']
            if device_info.get('traccar_id') is not None:
                attr[ATTR_TRACCAR_ID] = device_info['traccar_id']
                for dev in self._api.devices:
                    if dev['id'] == device_info['traccar_id']:
                        device = dev
                        break
            if device is not None and device.get('status') is not None:
                attr[ATTR_STATUS] = device['status']
            for custom_attr in self._custom_attributes:
                if device_info.get(custom_attr) is not None:
                    attr[custom_attr] = device_info[custom_attr]
            await self._async_see(
                dev_id=slugify(device_info['device_id']),
                gps=(device_info.get('latitude'),
                     device_info.get('longitude')),
                gps_accuracy=(device_info.get('accuracy')),
                attributes=attr)

    async def import_events(self):
        """Import events from Traccar."""
        device_ids = [device['id'] for device in self._api.devices]
        end_interval = datetime.utcnow()
        start_interval = end_interval - self._scan_interval
        events = await self._api.get_events(
            device_ids=device_ids,
            from_time=start_interval,
            to_time=end_interval,
            event_types=self._event_types.keys())
        if events is not None:
            for event in events:
                device_name = next((
                    dev.get('name') for dev in self._api.devices()
                    if dev.get('id') == event['deviceId']), None)
                self._hass.bus.async_fire(
                    'traccar_' + self._event_types.get(event["type"]), {
                        'device_traccar_id': event['deviceId'],
                        'device_name': device_name,
                        'type': event['type'],
                        'serverTime': event['serverTime'],
                        'attributes': event['attributes']
                    })
