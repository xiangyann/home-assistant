"""Geolocation support for GeoNet NZ Quakes Feeds."""
import logging
from typing import Optional

from homeassistant.components.geo_location import GeolocationEvent
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    CONF_UNIT_SYSTEM_IMPERIAL,
    LENGTH_KILOMETERS,
    LENGTH_MILES,
    ATTR_TIME,
)
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.util.unit_system import IMPERIAL_SYSTEM

from .const import DOMAIN, FEED, SIGNAL_DELETE_ENTITY, SIGNAL_UPDATE_ENTITY

_LOGGER = logging.getLogger(__name__)

ATTR_DEPTH = "depth"
ATTR_EXTERNAL_ID = "external_id"
ATTR_LOCALITY = "locality"
ATTR_MAGNITUDE = "magnitude"
ATTR_MMI = "mmi"
ATTR_PUBLICATION_DATE = "publication_date"
ATTR_QUALITY = "quality"

SOURCE = "geonetnz_quakes"


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the GeoNet NZ Quakes Feed platform."""
    manager = hass.data[DOMAIN][FEED][entry.entry_id]

    @callback
    def async_add_geolocation(feed_manager, external_id, unit_system):
        """Add gelocation entity from feed."""
        new_entity = GeonetnzQuakesEvent(feed_manager, external_id, unit_system)
        _LOGGER.debug("Adding geolocation %s", new_entity)
        async_add_entities([new_entity], True)

    manager.listeners.append(
        async_dispatcher_connect(
            hass, manager.async_event_new_entity(), async_add_geolocation
        )
    )
    hass.async_create_task(manager.async_update())
    _LOGGER.debug("Geolocation setup done")


class GeonetnzQuakesEvent(GeolocationEvent):
    """This represents an external event with GeoNet NZ Quakes feed data."""

    def __init__(self, feed_manager, external_id, unit_system):
        """Initialize entity with data from feed entry."""
        self._feed_manager = feed_manager
        self._external_id = external_id
        self._unit_system = unit_system
        self._title = None
        self._distance = None
        self._latitude = None
        self._longitude = None
        self._attribution = None
        self._depth = None
        self._locality = None
        self._magnitude = None
        self._mmi = None
        self._quality = None
        self._time = None
        self._remove_signal_delete = None
        self._remove_signal_update = None

    async def async_added_to_hass(self):
        """Call when entity is added to hass."""
        self._remove_signal_delete = async_dispatcher_connect(
            self.hass,
            SIGNAL_DELETE_ENTITY.format(self._external_id),
            self._delete_callback,
        )
        self._remove_signal_update = async_dispatcher_connect(
            self.hass,
            SIGNAL_UPDATE_ENTITY.format(self._external_id),
            self._update_callback,
        )

    async def async_will_remove_from_hass(self) -> None:
        """Call when entity will be removed from hass."""
        self._remove_signal_delete()
        self._remove_signal_update()

    @callback
    def _delete_callback(self):
        """Remove this entity."""
        self.hass.async_create_task(self.async_remove())

    @callback
    def _update_callback(self):
        """Call update method."""
        self.async_schedule_update_ha_state(True)

    @property
    def should_poll(self):
        """No polling needed for GeoNet NZ Quakes feed location events."""
        return False

    async def async_update(self):
        """Update this entity from the data held in the feed manager."""
        _LOGGER.debug("Updating %s", self._external_id)
        feed_entry = self._feed_manager.get_entry(self._external_id)
        if feed_entry:
            self._update_from_feed(feed_entry)

    def _update_from_feed(self, feed_entry):
        """Update the internal state from the provided feed entry."""
        self._title = feed_entry.title
        # Convert distance if not metric system.
        if self._unit_system == CONF_UNIT_SYSTEM_IMPERIAL:
            self._distance = IMPERIAL_SYSTEM.length(
                feed_entry.distance_to_home, LENGTH_KILOMETERS
            )
        else:
            self._distance = feed_entry.distance_to_home
        self._latitude = feed_entry.coordinates[0]
        self._longitude = feed_entry.coordinates[1]
        self._attribution = feed_entry.attribution
        self._depth = feed_entry.depth
        self._locality = feed_entry.locality
        self._magnitude = feed_entry.magnitude
        self._mmi = feed_entry.mmi
        self._quality = feed_entry.quality
        self._time = feed_entry.time

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return "mdi:pulse"

    @property
    def source(self) -> str:
        """Return source value of this external event."""
        return SOURCE

    @property
    def name(self) -> Optional[str]:
        """Return the name of the entity."""
        return self._title

    @property
    def distance(self) -> Optional[float]:
        """Return distance value of this external event."""
        return self._distance

    @property
    def latitude(self) -> Optional[float]:
        """Return latitude value of this external event."""
        return self._latitude

    @property
    def longitude(self) -> Optional[float]:
        """Return longitude value of this external event."""
        return self._longitude

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        if self._unit_system == CONF_UNIT_SYSTEM_IMPERIAL:
            return LENGTH_MILES
        return LENGTH_KILOMETERS

    @property
    def device_state_attributes(self):
        """Return the device state attributes."""
        attributes = {}
        for key, value in (
            (ATTR_EXTERNAL_ID, self._external_id),
            (ATTR_ATTRIBUTION, self._attribution),
            (ATTR_DEPTH, self._depth),
            (ATTR_LOCALITY, self._locality),
            (ATTR_MAGNITUDE, self._magnitude),
            (ATTR_MMI, self._mmi),
            (ATTR_QUALITY, self._quality),
            (ATTR_TIME, self._time),
        ):
            if value or isinstance(value, bool):
                attributes[key] = value
        return attributes
