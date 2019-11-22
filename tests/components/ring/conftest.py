"""Configuration for Ring tests."""
import requests_mock
import pytest
from tests.common import load_fixture
from asynctest import patch


@pytest.fixture(name="ring_mock")
def ring_save_mock():
    """Fixture to mock a ring."""
    with patch("ring_doorbell._exists_cache", return_value=False):
        with patch("ring_doorbell._save_cache", return_value=True) as save_mock:
            yield save_mock


@pytest.fixture(name="requests_mock")
def requests_mock_fixture(ring_mock):
    """Fixture to provide a requests mocker."""
    with requests_mock.mock() as mock:
        # Note all devices have an id of 987652, but a different device_id.
        # the device_id is used as our unique_id, but the id is what is sent
        # to the APIs, which is why every mock uses that id.

        # Mocks the response for authenticating
        mock.post(
            "https://oauth.ring.com/oauth/token", text=load_fixture("ring_oauth.json")
        )
        # Mocks the response for getting the login session
        mock.post(
            "https://api.ring.com/clients_api/session",
            text=load_fixture("ring_session.json"),
        )
        # Mocks the response for getting all the devices
        mock.get(
            "https://api.ring.com/clients_api/ring_devices",
            text=load_fixture("ring_devices.json"),
        )
        # Mocks the response for getting the history of a device
        mock.get(
            "https://api.ring.com/clients_api/doorbots/987652/history",
            text=load_fixture("ring_doorbots.json"),
        )
        # Mocks the response for getting the health of a device
        mock.get(
            "https://api.ring.com/clients_api/doorbots/987652/health",
            text=load_fixture("ring_doorboot_health_attrs.json"),
        )
        # Mocks the response for getting a chimes health
        mock.get(
            "https://api.ring.com/clients_api/chimes/999999/health",
            text=load_fixture("ring_chime_health_attrs.json"),
        )

        yield mock
