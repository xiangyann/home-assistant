"""Test zha fan."""
from unittest.mock import call, patch

import zigpy.zcl.clusters.general as general
import zigpy.zcl.clusters.hvac as hvac
import zigpy.zcl.foundation as zcl_f

from homeassistant.components import fan
from homeassistant.components.fan import ATTR_SPEED, DOMAIN, SERVICE_SET_SPEED
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
)

from .common import (
    async_enable_traffic,
    async_init_zigpy_device,
    async_test_device_join,
    find_entity_id,
    make_attribute,
    make_zcl_header,
)

from tests.common import mock_coro


async def test_fan(hass, config_entry, zha_gateway):
    """Test zha fan platform."""

    # create zigpy device
    zigpy_device = await async_init_zigpy_device(
        hass, [hvac.Fan.cluster_id, general.Basic.cluster_id], [], None, zha_gateway
    )

    # load up fan domain
    await hass.config_entries.async_forward_entry_setup(config_entry, DOMAIN)
    await hass.async_block_till_done()

    cluster = zigpy_device.endpoints.get(1).fan
    zha_device = zha_gateway.get_device(zigpy_device.ieee)
    entity_id = await find_entity_id(DOMAIN, zha_device, hass)
    assert entity_id is not None

    # test that the fan was created and that it is unavailable
    assert hass.states.get(entity_id).state == STATE_UNAVAILABLE

    # allow traffic to flow through the gateway and device
    await async_enable_traffic(hass, zha_gateway, [zha_device])

    # test that the state has changed from unavailable to off
    assert hass.states.get(entity_id).state == STATE_OFF

    # turn on at fan
    attr = make_attribute(0, 1)
    hdr = make_zcl_header(zcl_f.Command.Report_Attributes)
    cluster.handle_message(hdr, [[attr]])
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == STATE_ON

    # turn off at fan
    attr.value.value = 0
    cluster.handle_message(hdr, [[attr]])
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == STATE_OFF

    # turn on from HA
    with patch(
        "zigpy.zcl.Cluster.write_attributes",
        return_value=mock_coro([zcl_f.Status.SUCCESS, zcl_f.Status.SUCCESS]),
    ):
        # turn on via UI
        await async_turn_on(hass, entity_id)
        assert len(cluster.write_attributes.mock_calls) == 1
        assert cluster.write_attributes.call_args == call({"fan_mode": 2})

    # turn off from HA
    with patch(
        "zigpy.zcl.Cluster.write_attributes",
        return_value=mock_coro([zcl_f.Status.SUCCESS, zcl_f.Status.SUCCESS]),
    ):
        # turn off via UI
        await async_turn_off(hass, entity_id)
        assert len(cluster.write_attributes.mock_calls) == 1
        assert cluster.write_attributes.call_args == call({"fan_mode": 0})

    # change speed from HA
    with patch(
        "zigpy.zcl.Cluster.write_attributes",
        return_value=mock_coro([zcl_f.Status.SUCCESS, zcl_f.Status.SUCCESS]),
    ):
        # turn on via UI
        await async_set_speed(hass, entity_id, speed=fan.SPEED_HIGH)
        assert len(cluster.write_attributes.mock_calls) == 1
        assert cluster.write_attributes.call_args == call({"fan_mode": 3})

    # test adding new fan to the network and HA
    await async_test_device_join(hass, zha_gateway, hvac.Fan.cluster_id, entity_id)


async def async_turn_on(hass, entity_id, speed=None):
    """Turn fan on."""
    data = {
        key: value
        for key, value in [(ATTR_ENTITY_ID, entity_id), (ATTR_SPEED, speed)]
        if value is not None
    }

    await hass.services.async_call(DOMAIN, SERVICE_TURN_ON, data, blocking=True)


async def async_turn_off(hass, entity_id):
    """Turn fan off."""
    data = {ATTR_ENTITY_ID: entity_id} if entity_id else {}

    await hass.services.async_call(DOMAIN, SERVICE_TURN_OFF, data, blocking=True)


async def async_set_speed(hass, entity_id, speed=None):
    """Set speed for specified fan."""
    data = {
        key: value
        for key, value in [(ATTR_ENTITY_ID, entity_id), (ATTR_SPEED, speed)]
        if value is not None
    }

    await hass.services.async_call(DOMAIN, SERVICE_SET_SPEED, data, blocking=True)
