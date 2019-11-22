"""Support for Huawei LTE sensors."""

import logging
import re
from typing import Optional

import attr

from homeassistant.const import CONF_URL, STATE_UNKNOWN
from homeassistant.components.sensor import (
    DEVICE_CLASS_SIGNAL_STRENGTH,
    DOMAIN as SENSOR_DOMAIN,
)
from homeassistant.helpers import entity_registry

from . import HuaweiLteBaseEntity
from .const import (
    DOMAIN,
    KEY_DEVICE_INFORMATION,
    KEY_DEVICE_SIGNAL,
    KEY_MONITORING_TRAFFIC_STATISTICS,
    UNIT_BYTES,
    UNIT_SECONDS,
)


_LOGGER = logging.getLogger(__name__)


SENSOR_META = {
    KEY_DEVICE_INFORMATION: dict(
        include=re.compile(r"^WanIP.*Address$", re.IGNORECASE)
    ),
    (KEY_DEVICE_INFORMATION, "WanIPAddress"): dict(
        name="WAN IP address", icon="mdi:ip", enabled_default=True
    ),
    (KEY_DEVICE_INFORMATION, "WanIPv6Address"): dict(
        name="WAN IPv6 address", icon="mdi:ip"
    ),
    (KEY_DEVICE_SIGNAL, "band"): dict(name="Band"),
    (KEY_DEVICE_SIGNAL, "cell_id"): dict(name="Cell ID"),
    (KEY_DEVICE_SIGNAL, "lac"): dict(name="LAC", icon="mdi:map-marker"),
    (KEY_DEVICE_SIGNAL, "mode"): dict(
        name="Mode",
        formatter=lambda x: ({"0": "2G", "2": "3G", "7": "4G"}.get(x, "Unknown"), None),
    ),
    (KEY_DEVICE_SIGNAL, "pci"): dict(name="PCI"),
    (KEY_DEVICE_SIGNAL, "rsrq"): dict(
        name="RSRQ",
        device_class=DEVICE_CLASS_SIGNAL_STRENGTH,
        # http://www.lte-anbieter.info/technik/rsrq.php
        icon=lambda x: (x is None or x < -11)
        and "mdi:signal-cellular-outline"
        or x < -8
        and "mdi:signal-cellular-1"
        or x < -5
        and "mdi:signal-cellular-2"
        or "mdi:signal-cellular-3",
        enabled_default=True,
    ),
    (KEY_DEVICE_SIGNAL, "rsrp"): dict(
        name="RSRP",
        device_class=DEVICE_CLASS_SIGNAL_STRENGTH,
        # http://www.lte-anbieter.info/technik/rsrp.php
        icon=lambda x: (x is None or x < -110)
        and "mdi:signal-cellular-outline"
        or x < -95
        and "mdi:signal-cellular-1"
        or x < -80
        and "mdi:signal-cellular-2"
        or "mdi:signal-cellular-3",
        enabled_default=True,
    ),
    (KEY_DEVICE_SIGNAL, "rssi"): dict(
        name="RSSI",
        device_class=DEVICE_CLASS_SIGNAL_STRENGTH,
        # https://eyesaas.com/wi-fi-signal-strength/
        icon=lambda x: (x is None or x < -80)
        and "mdi:signal-cellular-outline"
        or x < -70
        and "mdi:signal-cellular-1"
        or x < -60
        and "mdi:signal-cellular-2"
        or "mdi:signal-cellular-3",
        enabled_default=True,
    ),
    (KEY_DEVICE_SIGNAL, "sinr"): dict(
        name="SINR",
        device_class=DEVICE_CLASS_SIGNAL_STRENGTH,
        # http://www.lte-anbieter.info/technik/sinr.php
        icon=lambda x: (x is None or x < 0)
        and "mdi:signal-cellular-outline"
        or x < 5
        and "mdi:signal-cellular-1"
        or x < 10
        and "mdi:signal-cellular-2"
        or "mdi:signal-cellular-3",
        enabled_default=True,
    ),
    (KEY_DEVICE_SIGNAL, "rscp"): dict(
        name="RSCP",
        device_class=DEVICE_CLASS_SIGNAL_STRENGTH,
        # https://wiki.teltonika.lt/view/RSCP
        icon=lambda x: (x is None or x < -95)
        and "mdi:signal-cellular-outline"
        or x < -85
        and "mdi:signal-cellular-1"
        or x < -75
        and "mdi:signal-cellular-2"
        or "mdi:signal-cellular-3",
    ),
    (KEY_DEVICE_SIGNAL, "ecio"): dict(
        name="EC/IO",
        device_class=DEVICE_CLASS_SIGNAL_STRENGTH,
        # https://wiki.teltonika.lt/view/EC/IO
        icon=lambda x: (x is None or x < -20)
        and "mdi:signal-cellular-outline"
        or x < -10
        and "mdi:signal-cellular-1"
        or x < -6
        and "mdi:signal-cellular-2"
        or "mdi:signal-cellular-3",
    ),
    KEY_MONITORING_TRAFFIC_STATISTICS: dict(
        exclude=re.compile(r"^showtraffic$", re.IGNORECASE)
    ),
    (KEY_MONITORING_TRAFFIC_STATISTICS, "CurrentConnectTime"): dict(
        name="Current connection duration", unit=UNIT_SECONDS, icon="mdi:timer"
    ),
    (KEY_MONITORING_TRAFFIC_STATISTICS, "CurrentDownload"): dict(
        name="Current connection download", unit=UNIT_BYTES, icon="mdi:download"
    ),
    (KEY_MONITORING_TRAFFIC_STATISTICS, "CurrentUpload"): dict(
        name="Current connection upload", unit=UNIT_BYTES, icon="mdi:upload"
    ),
    (KEY_MONITORING_TRAFFIC_STATISTICS, "TotalConnectTime"): dict(
        name="Total connected duration", unit=UNIT_SECONDS, icon="mdi:timer"
    ),
    (KEY_MONITORING_TRAFFIC_STATISTICS, "TotalDownload"): dict(
        name="Total download", unit=UNIT_BYTES, icon="mdi:download"
    ),
    (KEY_MONITORING_TRAFFIC_STATISTICS, "TotalUpload"): dict(
        name="Total upload", unit=UNIT_BYTES, icon="mdi:upload"
    ),
}


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up from config entry."""
    router = hass.data[DOMAIN].routers[config_entry.data[CONF_URL]]
    sensors = []
    for key in (
        KEY_DEVICE_INFORMATION,
        KEY_DEVICE_SIGNAL,
        KEY_MONITORING_TRAFFIC_STATISTICS,
    ):
        items = router.data.get(key)
        if not items:
            continue
        key_meta = SENSOR_META.get(key)
        if key_meta:
            include = key_meta.get("include")
            if include:
                items = filter(include.search, items)
            exclude = key_meta.get("exclude")
            if exclude:
                items = [x for x in items if not exclude.search(x)]
        for item in items:
            sensors.append(
                HuaweiLteSensor(router, key, item, SENSOR_META.get((key, item), {}))
            )

    # Pre-0.97 unique id migration. Old ones used the device serial number
    # (see comments in HuaweiLteData._setup_lte for more info), as well as
    # had a bug that joined the path str with periods, not the path components,
    # resulting e.g. *_device_signal.sinr to end up as
    # *_d.e.v.i.c.e._.s.i.g.n.a.l...s.i.n.r
    entreg = await entity_registry.async_get_registry(hass)
    for entid, ent in entreg.entities.items():
        if ent.platform != DOMAIN:
            continue
        for sensor in sensors:
            oldsuf = ".".join(f"{sensor.key}.{sensor.item}")
            if ent.unique_id.endswith(f"_{oldsuf}"):
                entreg.async_update_entity(entid, new_unique_id=sensor.unique_id)
                _LOGGER.debug(
                    "Updated entity %s unique id to %s", entid, sensor.unique_id
                )

    async_add_entities(sensors, True)


def format_default(value):
    """Format value."""
    unit = None
    if value is not None:
        # Clean up value and infer unit, e.g. -71dBm, 15 dB
        match = re.match(
            r"([>=<]*)(?P<value>.+?)\s*(?P<unit>[a-zA-Z]+)\s*$", str(value)
        )
        if match:
            try:
                value = float(match.group("value"))
                unit = match.group("unit")
            except ValueError:
                pass
    return value, unit


@attr.s
class HuaweiLteSensor(HuaweiLteBaseEntity):
    """Huawei LTE sensor entity."""

    key: str = attr.ib()
    item: str = attr.ib()
    meta: dict = attr.ib()

    _state = attr.ib(init=False, default=STATE_UNKNOWN)
    _unit: str = attr.ib(init=False)

    async def async_added_to_hass(self):
        """Subscribe to needed data on add."""
        await super().async_added_to_hass()
        self.router.subscriptions[self.key].add(f"{SENSOR_DOMAIN}/{self.item}")

    async def async_will_remove_from_hass(self):
        """Unsubscribe from needed data on remove."""
        await super().async_will_remove_from_hass()
        self.router.subscriptions[self.key].remove(f"{SENSOR_DOMAIN}/{self.item}")

    @property
    def _entity_name(self) -> str:
        return self.meta.get("name", self.item)

    @property
    def _device_unique_id(self) -> str:
        return f"{self.key}.{self.item}"

    @property
    def state(self):
        """Return sensor state."""
        return self._state

    @property
    def device_class(self) -> Optional[str]:
        """Return sensor device class."""
        return self.meta.get("device_class")

    @property
    def unit_of_measurement(self):
        """Return sensor's unit of measurement."""
        return self.meta.get("unit", self._unit)

    @property
    def icon(self):
        """Return icon for sensor."""
        icon = self.meta.get("icon")
        if callable(icon):
            return icon(self.state)
        return icon

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled when first added to the entity registry."""
        return bool(self.meta.get("enabled_default"))

    async def async_update(self):
        """Update state."""
        try:
            value = self.router.data[self.key][self.item]
        except KeyError:
            _LOGGER.debug("%s[%s] not in data", self.key, self.item)
            self._available = False
            return
        self._available = True

        formatter = self.meta.get("formatter")
        if not callable(formatter):
            formatter = format_default

        self._state, self._unit = formatter(value)


async def async_setup_platform(*args, **kwargs):
    """Old no longer used way to set up Huawei LTE sensors."""
    _LOGGER.warning(
        "Loading and configuring as a platform is no longer supported or "
        "required, convert to enabling/disabling available entities"
    )
