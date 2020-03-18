"""Common test objects."""
import copy
import json
from unittest.mock import ANY

from homeassistant.components import mqtt
from homeassistant.components.mqtt.discovery import async_start
from homeassistant.const import ATTR_ASSUMED_STATE, STATE_UNAVAILABLE

from tests.common import (
    MockConfigEntry,
    async_fire_mqtt_message,
    async_mock_mqtt_component,
    async_setup_component,
    mock_registry,
)

DEFAULT_CONFIG_DEVICE_INFO_ID = {
    "identifiers": ["helloworld"],
    "manufacturer": "Whatever",
    "name": "Beer",
    "model": "Glass",
    "sw_version": "0.1-beta",
}

DEFAULT_CONFIG_DEVICE_INFO_MAC = {
    "connections": [["mac", "02:5b:26:a8:dc:12"]],
    "manufacturer": "Whatever",
    "name": "Beer",
    "model": "Glass",
    "sw_version": "0.1-beta",
}


async def help_test_availability_without_topic(hass, mqtt_mock, domain, config):
    """Test availability without defined availability topic."""
    assert "availability_topic" not in config[domain]
    assert await async_setup_component(hass, domain, config)

    state = hass.states.get(f"{domain}.test")
    assert state.state != STATE_UNAVAILABLE


async def help_test_default_availability_payload(
    hass,
    mqtt_mock,
    domain,
    config,
    no_assumed_state=False,
    state_topic=None,
    state_message=None,
):
    """Test availability by default payload with defined topic.

    This is a test helper for the MqttAvailability mixin.
    """
    # Add availability settings to config
    config = copy.deepcopy(config)
    config[domain]["availability_topic"] = "availability-topic"
    assert await async_setup_component(hass, domain, config,)

    state = hass.states.get(f"{domain}.test")
    assert state.state == STATE_UNAVAILABLE

    async_fire_mqtt_message(hass, "availability-topic", "online")

    state = hass.states.get(f"{domain}.test")
    assert state.state != STATE_UNAVAILABLE
    if no_assumed_state:
        assert not state.attributes.get(ATTR_ASSUMED_STATE)

    async_fire_mqtt_message(hass, "availability-topic", "offline")

    state = hass.states.get(f"{domain}.test")
    assert state.state == STATE_UNAVAILABLE

    if state_topic:
        async_fire_mqtt_message(hass, state_topic, state_message)

        state = hass.states.get(f"{domain}.test")
        assert state.state == STATE_UNAVAILABLE

        async_fire_mqtt_message(hass, "availability-topic", "online")

        state = hass.states.get(f"{domain}.test")
        assert state.state != STATE_UNAVAILABLE


async def help_test_custom_availability_payload(
    hass,
    mqtt_mock,
    domain,
    config,
    no_assumed_state=False,
    state_topic=None,
    state_message=None,
):
    """Test availability by custom payload with defined topic.

    This is a test helper for the MqttAvailability mixin.
    """
    # Add availability settings to config
    config = copy.deepcopy(config)
    config[domain]["availability_topic"] = "availability-topic"
    config[domain]["payload_available"] = "good"
    config[domain]["payload_not_available"] = "nogood"
    assert await async_setup_component(hass, domain, config,)

    state = hass.states.get(f"{domain}.test")
    assert state.state == STATE_UNAVAILABLE

    async_fire_mqtt_message(hass, "availability-topic", "good")

    state = hass.states.get(f"{domain}.test")
    assert state.state != STATE_UNAVAILABLE
    if no_assumed_state:
        assert not state.attributes.get(ATTR_ASSUMED_STATE)

    async_fire_mqtt_message(hass, "availability-topic", "nogood")

    state = hass.states.get(f"{domain}.test")
    assert state.state == STATE_UNAVAILABLE

    if state_topic:
        async_fire_mqtt_message(hass, state_topic, state_message)

        state = hass.states.get(f"{domain}.test")
        assert state.state == STATE_UNAVAILABLE

        async_fire_mqtt_message(hass, "availability-topic", "good")

        state = hass.states.get(f"{domain}.test")
        assert state.state != STATE_UNAVAILABLE


async def help_test_setting_attribute_via_mqtt_json_message(
    hass, mqtt_mock, domain, config
):
    """Test the setting of attribute via MQTT with JSON payload.

    This is a test helper for the MqttAttributes mixin.
    """
    # Add JSON attributes settings to config
    config = copy.deepcopy(config)
    config[domain]["json_attributes_topic"] = "attr-topic"
    assert await async_setup_component(hass, domain, config,)

    async_fire_mqtt_message(hass, "attr-topic", '{ "val": "100" }')
    state = hass.states.get(f"{domain}.test")

    assert state.attributes.get("val") == "100"


async def help_test_setting_attribute_with_template(hass, mqtt_mock, domain, config):
    """Test the setting of attribute via MQTT with JSON payload.

    This is a test helper for the MqttAttributes mixin.
    """
    # Add JSON attributes settings to config
    config = copy.deepcopy(config)
    config[domain]["json_attributes_topic"] = "attr-topic"
    config[domain]["json_attributes_template"] = "{{ value_json['Timer1'] | tojson }}"
    assert await async_setup_component(hass, domain, config,)

    async_fire_mqtt_message(
        hass, "attr-topic", json.dumps({"Timer1": {"Arm": 0, "Time": "22:18"}})
    )
    state = hass.states.get(f"{domain}.test")

    assert state.attributes.get("Arm") == 0
    assert state.attributes.get("Time") == "22:18"


async def help_test_update_with_json_attrs_not_dict(
    hass, mqtt_mock, caplog, domain, config
):
    """Test attributes get extracted from a JSON result.

    This is a test helper for the MqttAttributes mixin.
    """
    # Add JSON attributes settings to config
    config = copy.deepcopy(config)
    config[domain]["json_attributes_topic"] = "attr-topic"
    assert await async_setup_component(hass, domain, config,)

    async_fire_mqtt_message(hass, "attr-topic", '[ "list", "of", "things"]')
    state = hass.states.get(f"{domain}.test")

    assert state.attributes.get("val") is None
    assert "JSON result was not a dictionary" in caplog.text


async def help_test_update_with_json_attrs_bad_JSON(
    hass, mqtt_mock, caplog, domain, config
):
    """Test JSON validation of attributes.

    This is a test helper for the MqttAttributes mixin.
    """
    # Add JSON attributes settings to config
    config = copy.deepcopy(config)
    config[domain]["json_attributes_topic"] = "attr-topic"
    assert await async_setup_component(hass, domain, config,)

    async_fire_mqtt_message(hass, "attr-topic", "This is not JSON")

    state = hass.states.get(f"{domain}.test")
    assert state.attributes.get("val") is None
    assert "Erroneous JSON: This is not JSON" in caplog.text


async def help_test_discovery_update_attr(hass, mqtt_mock, caplog, domain, config):
    """Test update of discovered MQTTAttributes.

    This is a test helper for the MqttAttributes mixin.
    """
    # Add JSON attributes settings to config
    config1 = copy.deepcopy(config)
    config1[domain]["json_attributes_topic"] = "attr-topic1"
    config2 = copy.deepcopy(config)
    config2[domain]["json_attributes_topic"] = "attr-topic2"
    data1 = json.dumps(config1[domain])
    data2 = json.dumps(config2[domain])

    entry = MockConfigEntry(domain=mqtt.DOMAIN)
    await async_start(hass, "homeassistant", {}, entry)
    async_fire_mqtt_message(hass, f"homeassistant/{domain}/bla/config", data1)
    await hass.async_block_till_done()
    async_fire_mqtt_message(hass, "attr-topic1", '{ "val": "100" }')
    state = hass.states.get(f"{domain}.test")
    assert state.attributes.get("val") == "100"

    # Change json_attributes_topic
    async_fire_mqtt_message(hass, f"homeassistant/{domain}/bla/config", data2)
    await hass.async_block_till_done()

    # Verify we are no longer subscribing to the old topic
    async_fire_mqtt_message(hass, "attr-topic1", '{ "val": "50" }')
    state = hass.states.get(f"{domain}.test")
    assert state.attributes.get("val") == "100"

    # Verify we are subscribing to the new topic
    async_fire_mqtt_message(hass, "attr-topic2", '{ "val": "75" }')
    state = hass.states.get(f"{domain}.test")
    assert state.attributes.get("val") == "75"


async def help_test_unique_id(hass, domain, config):
    """Test unique id option only creates one entity per unique_id."""
    await async_mock_mqtt_component(hass)
    assert await async_setup_component(hass, domain, config,)
    async_fire_mqtt_message(hass, "test-topic", "payload")
    assert len(hass.states.async_entity_ids(domain)) == 1


async def help_test_discovery_removal(hass, mqtt_mock, caplog, domain, data):
    """Test removal of discovered component.

    This is a test helper for the MqttDiscoveryUpdate mixin.
    """
    entry = MockConfigEntry(domain=mqtt.DOMAIN)
    await async_start(hass, "homeassistant", {}, entry)

    async_fire_mqtt_message(hass, f"homeassistant/{domain}/bla/config", data)
    await hass.async_block_till_done()

    state = hass.states.get(f"{domain}.test")
    assert state is not None
    assert state.name == "test"

    async_fire_mqtt_message(hass, f"homeassistant/{domain}/bla/config", "")
    await hass.async_block_till_done()

    state = hass.states.get(f"{domain}.test")
    assert state is None


async def help_test_discovery_update(hass, mqtt_mock, caplog, domain, data1, data2):
    """Test update of discovered component.

    This is a test helper for the MqttDiscoveryUpdate mixin.
    """
    entry = MockConfigEntry(domain=mqtt.DOMAIN)
    await async_start(hass, "homeassistant", {}, entry)

    async_fire_mqtt_message(hass, f"homeassistant/{domain}/bla/config", data1)
    await hass.async_block_till_done()

    state = hass.states.get(f"{domain}.beer")
    assert state is not None
    assert state.name == "Beer"

    async_fire_mqtt_message(hass, f"homeassistant/{domain}/bla/config", data2)
    await hass.async_block_till_done()

    state = hass.states.get(f"{domain}.beer")
    assert state is not None
    assert state.name == "Milk"

    state = hass.states.get(f"{domain}.milk")
    assert state is None


async def help_test_discovery_broken(hass, mqtt_mock, caplog, domain, data1, data2):
    """Test handling of bad discovery message."""
    entry = MockConfigEntry(domain=mqtt.DOMAIN)
    await async_start(hass, "homeassistant", {}, entry)

    async_fire_mqtt_message(hass, f"homeassistant/{domain}/bla/config", data1)
    await hass.async_block_till_done()

    state = hass.states.get(f"{domain}.beer")
    assert state is None

    async_fire_mqtt_message(hass, f"homeassistant/{domain}/bla/config", data2)
    await hass.async_block_till_done()

    state = hass.states.get(f"{domain}.milk")
    assert state is not None
    assert state.name == "Milk"
    state = hass.states.get(f"{domain}.beer")
    assert state is None


async def help_test_entity_device_info_with_identifier(hass, mqtt_mock, domain, config):
    """Test device registry integration.

    This is a test helper for the MqttDiscoveryUpdate mixin.
    """
    # Add device settings to config
    config = copy.deepcopy(config[domain])
    config["device"] = copy.deepcopy(DEFAULT_CONFIG_DEVICE_INFO_ID)
    config["unique_id"] = "veryunique"

    entry = MockConfigEntry(domain=mqtt.DOMAIN)
    entry.add_to_hass(hass)
    await async_start(hass, "homeassistant", {}, entry)
    registry = await hass.helpers.device_registry.async_get_registry()

    data = json.dumps(config)
    async_fire_mqtt_message(hass, f"homeassistant/{domain}/bla/config", data)
    await hass.async_block_till_done()

    device = registry.async_get_device({("mqtt", "helloworld")}, set())
    assert device is not None
    assert device.identifiers == {("mqtt", "helloworld")}
    assert device.manufacturer == "Whatever"
    assert device.name == "Beer"
    assert device.model == "Glass"
    assert device.sw_version == "0.1-beta"


async def help_test_entity_device_info_with_connection(hass, mqtt_mock, domain, config):
    """Test device registry integration.

    This is a test helper for the MqttDiscoveryUpdate mixin.
    """
    # Add device settings to config
    config = copy.deepcopy(config[domain])
    config["device"] = copy.deepcopy(DEFAULT_CONFIG_DEVICE_INFO_MAC)
    config["unique_id"] = "veryunique"

    entry = MockConfigEntry(domain=mqtt.DOMAIN)
    entry.add_to_hass(hass)
    await async_start(hass, "homeassistant", {}, entry)
    registry = await hass.helpers.device_registry.async_get_registry()

    data = json.dumps(config)
    async_fire_mqtt_message(hass, f"homeassistant/{domain}/bla/config", data)
    await hass.async_block_till_done()

    device = registry.async_get_device(set(), {("mac", "02:5b:26:a8:dc:12")})
    assert device is not None
    assert device.connections == {("mac", "02:5b:26:a8:dc:12")}
    assert device.manufacturer == "Whatever"
    assert device.name == "Beer"
    assert device.model == "Glass"
    assert device.sw_version == "0.1-beta"


async def help_test_entity_device_info_remove(hass, mqtt_mock, domain, config):
    """Test device registry remove."""
    # Add device settings to config
    config = copy.deepcopy(config[domain])
    config["device"] = copy.deepcopy(DEFAULT_CONFIG_DEVICE_INFO_ID)
    config["unique_id"] = "veryunique"

    entry = MockConfigEntry(domain=mqtt.DOMAIN)
    entry.add_to_hass(hass)
    await async_start(hass, "homeassistant", {}, entry)
    dev_registry = await hass.helpers.device_registry.async_get_registry()
    ent_registry = await hass.helpers.entity_registry.async_get_registry()

    data = json.dumps(config)
    async_fire_mqtt_message(hass, f"homeassistant/{domain}/bla/config", data)
    await hass.async_block_till_done()

    device = dev_registry.async_get_device({("mqtt", "helloworld")}, set())
    assert device is not None
    assert ent_registry.async_get_entity_id(domain, mqtt.DOMAIN, "veryunique")

    async_fire_mqtt_message(hass, f"homeassistant/{domain}/bla/config", "")
    await hass.async_block_till_done()

    device = dev_registry.async_get_device({("mqtt", "helloworld")}, set())
    assert device is None
    assert not ent_registry.async_get_entity_id(domain, mqtt.DOMAIN, "veryunique")


async def help_test_entity_device_info_update(hass, mqtt_mock, domain, config):
    """Test device registry update.

    This is a test helper for the MqttDiscoveryUpdate mixin.
    """
    # Add device settings to config
    config = copy.deepcopy(config[domain])
    config["device"] = copy.deepcopy(DEFAULT_CONFIG_DEVICE_INFO_ID)
    config["unique_id"] = "veryunique"

    entry = MockConfigEntry(domain=mqtt.DOMAIN)
    entry.add_to_hass(hass)
    await async_start(hass, "homeassistant", {}, entry)
    registry = await hass.helpers.device_registry.async_get_registry()

    data = json.dumps(config)
    async_fire_mqtt_message(hass, f"homeassistant/{domain}/bla/config", data)
    await hass.async_block_till_done()

    device = registry.async_get_device({("mqtt", "helloworld")}, set())
    assert device is not None
    assert device.name == "Beer"

    config["device"]["name"] = "Milk"
    data = json.dumps(config)
    async_fire_mqtt_message(hass, f"homeassistant/{domain}/bla/config", data)
    await hass.async_block_till_done()

    device = registry.async_get_device({("mqtt", "helloworld")}, set())
    assert device is not None
    assert device.name == "Milk"


async def help_test_entity_id_update(hass, mqtt_mock, domain, config, topics=None):
    """Test MQTT subscriptions are managed when entity_id is updated."""
    # Add unique_id to config
    config = copy.deepcopy(config)
    config[domain]["unique_id"] = "TOTALLY_UNIQUE"

    if topics is None:
        # Add default topics to config
        config[domain]["availability_topic"] = "avty-topic"
        config[domain]["state_topic"] = "test-topic"
        topics = ["avty-topic", "test-topic"]
    assert len(topics) > 0
    registry = mock_registry(hass, {})
    mock_mqtt = await async_mock_mqtt_component(hass)
    assert await async_setup_component(hass, domain, config,)

    state = hass.states.get(f"{domain}.test")
    assert state is not None
    assert mock_mqtt.async_subscribe.call_count == len(topics)
    for topic in topics:
        mock_mqtt.async_subscribe.assert_any_call(topic, ANY, ANY, ANY)
    mock_mqtt.async_subscribe.reset_mock()

    registry.async_update_entity(f"{domain}.test", new_entity_id=f"{domain}.milk")
    await hass.async_block_till_done()

    state = hass.states.get(f"{domain}.test")
    assert state is None

    state = hass.states.get(f"{domain}.milk")
    assert state is not None
    for topic in topics:
        mock_mqtt.async_subscribe.assert_any_call(topic, ANY, ANY, ANY)
