"""
Provide a mock light platform.

Call init before using it in your tests to ensure clean test data.
"""
from homeassistant.const import STATE_ON, STATE_OFF
from tests.common import MockToggleEntity


ENTITIES = []


def init(empty=False):
    """Initialize the platform with entities."""
    global ENTITIES

    ENTITIES = (
        []
        if empty
        else [
            MockToggleEntity("Ceiling", STATE_ON),
            MockToggleEntity("Ceiling", STATE_OFF),
            MockToggleEntity(None, STATE_OFF),
        ]
    )


async def async_setup_platform(
    hass, config, async_add_entities_callback, discovery_info=None
):
    """Return mock entities."""
    async_add_entities_callback(ENTITIES)
