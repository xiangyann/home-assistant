"""Denon HEOS Media Player."""
import asyncio
from functools import reduce, wraps
import logging
from operator import ior
from typing import Sequence

from homeassistant.components.media_player import MediaPlayerDevice
from homeassistant.components.media_player.const import (
    DOMAIN, MEDIA_TYPE_MUSIC, MEDIA_TYPE_URL, SUPPORT_CLEAR_PLAYLIST,
    SUPPORT_NEXT_TRACK, SUPPORT_PAUSE, SUPPORT_PLAY, SUPPORT_PLAY_MEDIA,
    SUPPORT_PREVIOUS_TRACK, SUPPORT_SELECT_SOURCE, SUPPORT_SHUFFLE_SET,
    SUPPORT_STOP, SUPPORT_VOLUME_MUTE, SUPPORT_VOLUME_SET, SUPPORT_VOLUME_STEP)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_IDLE, STATE_PAUSED, STATE_PLAYING
from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.util.dt import utcnow

from .const import (
    DATA_SOURCE_MANAGER, DOMAIN as HEOS_DOMAIN, SIGNAL_HEOS_SOURCES_UPDATED)

BASE_SUPPORTED_FEATURES = SUPPORT_VOLUME_MUTE | SUPPORT_VOLUME_SET | \
                          SUPPORT_VOLUME_STEP | SUPPORT_CLEAR_PLAYLIST | \
                          SUPPORT_SHUFFLE_SET | SUPPORT_SELECT_SOURCE | \
                          SUPPORT_PLAY_MEDIA

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
        hass, config, async_add_entities, discovery_info=None):
    """Platform uses config entry setup."""
    pass


async def async_setup_entry(hass: HomeAssistantType, entry: ConfigEntry,
                            async_add_entities):
    """Add media players for a config entry."""
    players = hass.data[HEOS_DOMAIN][DOMAIN]
    devices = [HeosMediaPlayer(player) for player in players.values()]
    async_add_entities(devices, True)


def log_command_error(command: str):
    """Return decorator that logs command failure."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            from pyheos import CommandError
            try:
                await func(*args, **kwargs)
            except (CommandError, asyncio.TimeoutError, ConnectionError) as ex:
                _LOGGER.error("Unable to %s: %s", command, ex)
        return wrapper
    return decorator


class HeosMediaPlayer(MediaPlayerDevice):
    """The HEOS player."""

    def __init__(self, player):
        """Initialize."""
        from pyheos import const
        self._media_position_updated_at = None
        self._player = player
        self._signals = []
        self._supported_features = BASE_SUPPORTED_FEATURES
        self._source_manager = None
        self._play_state_to_state = {
            const.PLAY_STATE_PLAY: STATE_PLAYING,
            const.PLAY_STATE_STOP: STATE_IDLE,
            const.PLAY_STATE_PAUSE: STATE_PAUSED
        }
        self._control_to_support = {
            const.CONTROL_PLAY: SUPPORT_PLAY,
            const.CONTROL_PAUSE: SUPPORT_PAUSE,
            const.CONTROL_STOP: SUPPORT_STOP,
            const.CONTROL_PLAY_PREVIOUS: SUPPORT_PREVIOUS_TRACK,
            const.CONTROL_PLAY_NEXT: SUPPORT_NEXT_TRACK
        }

    async def _controller_event(self, event):
        """Handle controller event."""
        from pyheos import const
        if event == const.EVENT_PLAYERS_CHANGED:
            await self.async_update_ha_state(True)

    async def _heos_event(self, event):
        """Handle connection event."""
        from pyheos import CommandError, const
        if event == const.EVENT_CONNECTED:
            try:
                await self._player.refresh()
            except (CommandError, asyncio.TimeoutError, ConnectionError) as ex:
                _LOGGER.error("Unable to refresh player %s: %s",
                              self._player, ex)
        await self.async_update_ha_state(True)

    async def _player_update(self, player_id, event):
        """Handle player attribute updated."""
        from pyheos import const
        if self._player.player_id != player_id:
            return
        if event == const.EVENT_PLAYER_NOW_PLAYING_PROGRESS:
            self._media_position_updated_at = utcnow()
        await self.async_update_ha_state(True)

    async def _sources_updated(self):
        """Handle sources changed."""
        await self.async_update_ha_state(True)

    async def async_added_to_hass(self):
        """Device added to hass."""
        from pyheos import const
        self._source_manager = self.hass.data[HEOS_DOMAIN][DATA_SOURCE_MANAGER]
        # Update state when attributes of the player change
        self._signals.append(self._player.heos.dispatcher.connect(
            const.SIGNAL_PLAYER_EVENT, self._player_update))
        # Update state when available players change
        self._signals.append(self._player.heos.dispatcher.connect(
            const.SIGNAL_CONTROLLER_EVENT, self._controller_event))
        # Update state upon connect/disconnects
        self._signals.append(self._player.heos.dispatcher.connect(
            const.SIGNAL_HEOS_EVENT, self._heos_event))
        # Update state when sources change
        self._signals.append(
            self.hass.helpers.dispatcher.async_dispatcher_connect(
                SIGNAL_HEOS_SOURCES_UPDATED, self._sources_updated))

    @log_command_error("clear playlist")
    async def async_clear_playlist(self):
        """Clear players playlist."""
        await self._player.clear_queue()

    @log_command_error("pause")
    async def async_media_pause(self):
        """Send pause command."""
        await self._player.pause()

    @log_command_error("play")
    async def async_media_play(self):
        """Send play command."""
        await self._player.play()

    @log_command_error("move to previous track")
    async def async_media_previous_track(self):
        """Send previous track command."""
        await self._player.play_previous()

    @log_command_error("move to next track")
    async def async_media_next_track(self):
        """Send next track command."""
        await self._player.play_next()

    @log_command_error("stop")
    async def async_media_stop(self):
        """Send stop command."""
        await self._player.stop()

    @log_command_error("set mute")
    async def async_mute_volume(self, mute):
        """Mute the volume."""
        await self._player.set_mute(mute)

    @log_command_error("play media")
    async def async_play_media(self, media_type, media_id, **kwargs):
        """Play a piece of media."""
        if media_type == MEDIA_TYPE_URL:
            await self._player.play_url(media_id)
        else:
            _LOGGER.error("Unable to play media: Unsupported media type '%s'",
                          media_type)

    @log_command_error("select source")
    async def async_select_source(self, source):
        """Select input source."""
        await self._source_manager.play_source(source, self._player)

    @log_command_error("set shuffle")
    async def async_set_shuffle(self, shuffle):
        """Enable/disable shuffle mode."""
        await self._player.set_play_mode(self._player.repeat, shuffle)

    @log_command_error("set volume level")
    async def async_set_volume_level(self, volume):
        """Set volume level, range 0..1."""
        await self._player.set_volume(int(volume * 100))

    async def async_update(self):
        """Update supported features of the player."""
        controls = self._player.now_playing_media.supported_controls
        current_support = [self._control_to_support[control]
                           for control in controls]
        self._supported_features = reduce(ior, current_support,
                                          BASE_SUPPORTED_FEATURES)

    async def async_will_remove_from_hass(self):
        """Disconnect the device when removed."""
        for signal_remove in self._signals:
            signal_remove()
        self._signals.clear()

    @property
    def available(self) -> bool:
        """Return True if the device is available."""
        return self._player.available

    @property
    def device_info(self) -> dict:
        """Get attributes about the device."""
        return {
            'identifiers': {
                (DOMAIN, self._player.player_id)
            },
            'name': self._player.name,
            'model': self._player.model,
            'manufacturer': 'HEOS',
            'sw_version': self._player.version
        }

    @property
    def device_state_attributes(self) -> dict:
        """Get additional attribute about the state."""
        return {
            'media_album_id': self._player.now_playing_media.album_id,
            'media_queue_id': self._player.now_playing_media.queue_id,
            'media_source_id': self._player.now_playing_media.source_id,
            'media_station': self._player.now_playing_media.station,
            'media_type': self._player.now_playing_media.type
        }

    @property
    def is_volume_muted(self) -> bool:
        """Boolean if volume is currently muted."""
        return self._player.is_muted

    @property
    def media_album_name(self) -> str:
        """Album name of current playing media, music track only."""
        return self._player.now_playing_media.album

    @property
    def media_artist(self) -> str:
        """Artist of current playing media, music track only."""
        return self._player.now_playing_media.artist

    @property
    def media_content_id(self) -> str:
        """Content ID of current playing media."""
        return self._player.now_playing_media.media_id

    @property
    def media_content_type(self) -> str:
        """Content type of current playing media."""
        return MEDIA_TYPE_MUSIC

    @property
    def media_duration(self):
        """Duration of current playing media in seconds."""
        duration = self._player.now_playing_media.duration
        if isinstance(duration, int):
            return duration / 1000
        return None

    @property
    def media_position(self):
        """Position of current playing media in seconds."""
        # Some media doesn't have duration but reports position, return None
        if not self._player.now_playing_media.duration:
            return None
        return self._player.now_playing_media.current_position / 1000

    @property
    def media_position_updated_at(self):
        """When was the position of the current playing media valid."""
        # Some media doesn't have duration but reports position, return None
        if not self._player.now_playing_media.duration:
            return None
        return self._media_position_updated_at

    @property
    def media_image_url(self) -> str:
        """Image url of current playing media."""
        # May be an empty string, if so, return None
        image_url = self._player.now_playing_media.image_url
        return image_url if image_url else None

    @property
    def media_title(self) -> str:
        """Title of current playing media."""
        return self._player.now_playing_media.song

    @property
    def name(self) -> str:
        """Return the name of the device."""
        return self._player.name

    @property
    def should_poll(self) -> bool:
        """No polling needed for this device."""
        return False

    @property
    def shuffle(self) -> bool:
        """Boolean if shuffle is enabled."""
        return self._player.shuffle

    @property
    def source(self) -> str:
        """Name of the current input source."""
        return self._source_manager.get_current_source(
            self._player.now_playing_media)

    @property
    def source_list(self) -> Sequence[str]:
        """List of available input sources."""
        return self._source_manager.source_list

    @property
    def state(self) -> str:
        """State of the player."""
        return self._play_state_to_state[self._player.state]

    @property
    def supported_features(self) -> int:
        """Flag media player features that are supported."""
        return self._supported_features

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return str(self._player.player_id)

    @property
    def volume_level(self) -> float:
        """Volume level of the media player (0..1)."""
        return self._player.volume / 100
