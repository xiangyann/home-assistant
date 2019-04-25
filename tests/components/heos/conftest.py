"""Configuration for HEOS tests."""
from typing import Dict, Sequence

from asynctest.mock import Mock, patch as patch
from pyheos import Dispatcher, HeosPlayer, HeosSource, InputSource, const
import pytest

from homeassistant.components.heos import DOMAIN
from homeassistant.const import CONF_HOST

from tests.common import MockConfigEntry


@pytest.fixture(name="config_entry")
def config_entry_fixture():
    """Create a mock HEOS config entry."""
    return MockConfigEntry(domain=DOMAIN, data={CONF_HOST: '127.0.0.1'},
                           title='Controller (127.0.0.1)')


@pytest.fixture(name="controller")
def controller_fixture(players, favorites, input_sources, dispatcher):
    """Create a mock Heos controller fixture."""
    with patch("pyheos.Heos", autospec=True) as mock:
        mock_heos = mock.return_value
        mock_heos.dispatcher = dispatcher
        mock_heos.get_players.return_value = players
        mock_heos.players = players
        mock_heos.get_favorites.return_value = favorites
        mock_heos.get_input_sources.return_value = input_sources
        mock_heos.is_signed_in = True
        mock_heos.signed_in_username = "user@user.com"
        yield mock_heos


@pytest.fixture(name="config")
def config_fixture():
    """Create hass config fixture."""
    return {
        DOMAIN: {CONF_HOST: '127.0.0.1'}
    }


@pytest.fixture(name="players")
def player_fixture(dispatcher):
    """Create a mock HeosPlayer."""
    player = Mock(HeosPlayer)
    player.heos.dispatcher = dispatcher
    player.player_id = 1
    player.name = "Test Player"
    player.model = "Test Model"
    player.version = "1.0.0"
    player.is_muted = False
    player.available = True
    player.state = const.PLAY_STATE_STOP
    player.ip_address = "127.0.0.1"
    player.network = "wired"
    player.shuffle = False
    player.repeat = const.REPEAT_OFF
    player.volume = 25
    player.now_playing_media.supported_controls = const.CONTROLS_ALL
    player.now_playing_media.album_id = 1
    player.now_playing_media.queue_id = 1
    player.now_playing_media.source_id = 1
    player.now_playing_media.station = "Station Name"
    player.now_playing_media.type = "Station"
    player.now_playing_media.album = "Album"
    player.now_playing_media.artist = "Artist"
    player.now_playing_media.media_id = "1"
    player.now_playing_media.duration = None
    player.now_playing_media.current_position = None
    player.now_playing_media.image_url = "http://"
    player.now_playing_media.song = "Song"
    return {player.player_id: player}


@pytest.fixture(name="favorites")
def favorites_fixture() -> Dict[int, HeosSource]:
    """Create favorites fixture."""
    station = Mock(HeosSource)
    station.type = const.TYPE_STATION
    station.name = "Today's Hits Radio"
    station.media_id = '123456789'
    radio = Mock(HeosSource)
    radio.type = const.TYPE_STATION
    radio.name = "Classical MPR (Classical Music)"
    radio.media_id = 's1234'
    return {
        1: station,
        2: radio
    }


@pytest.fixture(name="input_sources")
def input_sources_fixture() -> Sequence[InputSource]:
    """Create a set of input sources for testing."""
    source = Mock(InputSource)
    source.player_id = 1
    source.input_name = const.INPUT_AUX_IN_1
    source.name = "HEOS Drive - Line In 1"
    return [source]


@pytest.fixture(name="dispatcher")
def dispatcher_fixture() -> Dispatcher:
    """Create a dispatcher for testing."""
    return Dispatcher()


@pytest.fixture(name="discovery_data")
def discovery_data_fixture() -> dict:
    """Return mock discovery data for testing."""
    return {
        'host': '127.0.0.1',
        'manufacturer': 'Denon',
        'model_name': 'HEOS Drive',
        'model_number': 'DWSA-10 4.0',
        'name': 'Office',
        'port': 60006,
        'serial': None,
        'ssdp_description':
            'http://127.0.0.1:60006/upnp/desc/aios_device/aios_device.xml',
        'udn': 'uuid:e61de70c-2250-1c22-0080-0005cdf512be',
        'upnp_device_type': 'urn:schemas-denon-com:device:AiosDevice:1'
    }
