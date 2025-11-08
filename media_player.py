"""Home Assistant Media Player Entity."""

import asyncio
import logging
from typing import Optional, Dict, Any
from pathlib import Path

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerState,
    MediaPlayerEntityFeature,
    MediaType,
)
from homeassistant.const import STATE_IDLE, STATE_PLAYING, STATE_PAUSED
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity

from .mpv_backend import MPVBackend
from .metadata_handler import MetadataHandler

_LOGGER = logging.getLogger(__name__)


class PipePlayPlayer(MediaPlayerEntity):
    """Home Assistant media player using MPV backend."""
    
    def __init__(self, hass: HomeAssistant, name: str = "PipePlay Player"):
        """Initialize the media player."""
        self._hass = hass
        self._name = name
        self._backend = MPVBackend()
        self._metadata_handler = MetadataHandler()
        self._attr_unique_id = "pipeplay_player"
        self._attr_device_class = "speaker"
        
        # Media info
        self._media_title = None
        self._media_artist = None
        self._media_album = None
        self._media_content_type = None
        self._media_duration = None
        self._media_position = None
        self._media_position_updated_at = None
        
        # Supported features
        self._attr_supported_features = (
            MediaPlayerEntityFeature.PLAY
            | MediaPlayerEntityFeature.PAUSE
            | MediaPlayerEntityFeature.STOP
            | MediaPlayerEntityFeature.VOLUME_SET
            | MediaPlayerEntityFeature.VOLUME_MUTE
            | MediaPlayerEntityFeature.SEEK
            | MediaPlayerEntityFeature.PLAY_MEDIA
        )
    
    async def async_added_to_hass(self):
        """Called when entity is added to Home Assistant."""
        await super().async_added_to_hass()
        await self._backend.initialize()
        self._backend.set_state_callback(self._on_backend_state_change)
        _LOGGER.info("PipePlay Player added to Home Assistant")
    
    async def async_will_remove_from_hass(self):
        """Called when entity is being removed from Home Assistant."""
        await self._backend.cleanup()
        _LOGGER.info("PipePlay Player removed from Home Assistant")
    
    async def _on_backend_state_change(self):
        """Handle backend state changes."""
        self.async_schedule_update_ha_state()
    
    @property
    def name(self) -> str:
        """Return the name of the media player."""
        return self._name
    
    @property
    def state(self) -> str:
        """Return the current state of the media player."""
        backend_state = self._backend.state
        
        state_mapping = {
            "idle": MediaPlayerState.IDLE,
            "playing": MediaPlayerState.PLAYING,
            "paused": MediaPlayerState.PAUSED,
            "buffering": MediaPlayerState.BUFFERING,
        }
        
        return state_mapping.get(backend_state, MediaPlayerState.IDLE)
    
    @property
    def volume_level(self) -> Optional[float]:
        """Return the volume level of the media player (0..1)."""
        return self._backend.volume_level
    
    @property
    def is_volume_muted(self) -> Optional[bool]:
        """Return boolean if volume is currently muted."""
        return self._backend.is_muted
    
    @property
    def media_content_type(self) -> Optional[str]:
        """Return the media content type."""
        return self._media_content_type
    
    @property
    def media_title(self) -> Optional[str]:
        """Return the title of current playing media."""
        return self._media_title
    
    @property
    def media_artist(self) -> Optional[str]:
        """Return the artist of current playing media."""
        return self._media_artist
    
    @property
    def media_album_name(self) -> Optional[str]:
        """Return the album name of current playing media."""
        return self._media_album
    
    @property
    def media_duration(self) -> Optional[int]:
        """Return the duration of current playing media in seconds."""
        duration = self._backend.media_duration
        return int(duration) if duration and duration > 0 else None
    
    @property
    def media_position(self) -> Optional[int]:
        """Return the position of current playing media in seconds."""
        position = self._backend.media_position
        return int(position) if position else None
    
    @property
    def media_position_updated_at(self):
        """Return the last time position was updated."""
        return self._media_position_updated_at
    
    async def async_play_media(self, media_type: str, media_id: str, **kwargs):
        """Play media from a URL or file path."""
        try:
            _LOGGER.info(f"Playing media: {media_id} (type: {media_type})")
            
            # Extract metadata if it's a local file
            if Path(media_id).exists():
                metadata = await self._metadata_handler.extract_metadata(media_id)
                self._media_title = metadata.get("title")
                self._media_artist = metadata.get("artist")
                self._media_album = metadata.get("album")
            else:
                # For URLs, use the filename as title
                self._media_title = Path(media_id).name or "Unknown"
                self._media_artist = None
                self._media_album = None
            
            # Determine content type
            if media_type == MediaType.MUSIC:
                self._media_content_type = MediaType.MUSIC
            elif media_type == MediaType.PODCAST:
                self._media_content_type = MediaType.PODCAST
            else:
                self._media_content_type = MediaType.MUSIC  # Default
            
            await self._backend.play_media(media_id, media_type)
            self.async_schedule_update_ha_state()
            
        except Exception as e:
            _LOGGER.error(f"Error playing media {media_id}: {e}")
            raise
    
    async def async_media_play(self):
        """Send play command."""
        if self.state == MediaPlayerState.PAUSED:
            await self._backend.resume()
        else:
            _LOGGER.warning("Cannot play - no media loaded or already playing")
    
    async def async_media_pause(self):
        """Send pause command."""
        await self._backend.pause()
    
    async def async_media_stop(self):
        """Send stop command."""
        await self._backend.stop()
        self._clear_media_info()
        self.async_schedule_update_ha_state()
    
    async def async_set_volume_level(self, volume: float):
        """Set volume level, range 0..1."""
        await self._backend.set_volume(volume)
        self.async_schedule_update_ha_state()
    
    async def async_mute_volume(self, mute: bool):
        """Mute (true) or unmute (false) media player."""
        await self._backend.set_mute(mute)
        self.async_schedule_update_ha_state()
    
    async def async_media_seek(self, position: float):
        """Send seek command."""
        await self._backend.seek(position)
        self.async_schedule_update_ha_state()
    
    def _clear_media_info(self):
        """Clear current media information."""
        self._media_title = None
        self._media_artist = None
        self._media_album = None
        self._media_content_type = None
        self._media_duration = None
        self._media_position = None