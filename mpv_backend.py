"""MPV audio backend for media playback."""

import asyncio
import logging
from typing import Optional, Dict, Any, Callable
import mpv
from threading import Lock
from pathlib import Path

_LOGGER = logging.getLogger(__name__)


class MPVBackend:
    """MPV-based audio backend for media playback."""
    
    def __init__(self):
        self._mpv_player = None
        self._volume = 1.0
        self._muted = False
        self._state = "idle"
        self._current_media = None
        self._position = 0
        self._duration = 0
        self._lock = Lock()
        self._state_callback: Optional[Callable] = None
        
    async def initialize(self):
        """Initialize the MPV backend."""
        try:
            # Initialize MPV player
            self._mpv_player = mpv.MPV(
                input_default_bindings=True,
                input_vo_keyboard=True,
                osc=True,
                audio_display='no',
                video='no'  # Audio only
            )
            
            # Set up MPV event handlers
            self._mpv_player.observe_property('time-pos', self._on_position_change)
            self._mpv_player.observe_property('duration', self._on_duration_change)
            self._mpv_player.observe_property('pause', self._on_pause_change)
            self._mpv_player.observe_property('eof-reached', self._on_eof)
            
            _LOGGER.info("MPV backend initialized successfully")
            
        except Exception as e:
            _LOGGER.error(f"Failed to initialize MPV backend: {e}")
            raise
    
    def set_state_callback(self, callback: Callable):
        """Set callback for state changes."""
        self._state_callback = callback
    
    def _notify_state_change(self):
        """Notify about state changes."""
        if self._state_callback:
            asyncio.create_task(self._state_callback())
    
    def _on_position_change(self, name, value):
        """Handle position changes."""
        if value is not None:
            with self._lock:
                self._position = value
            self._notify_state_change()
    
    def _on_duration_change(self, name, value):
        """Handle duration changes."""
        if value is not None:
            with self._lock:
                self._duration = value
            self._notify_state_change()
    
    def _on_pause_change(self, name, value):
        """Handle pause state changes."""
        with self._lock:
            if value:
                self._state = "paused"
            elif self._current_media:
                self._state = "playing"
        self._notify_state_change()
    
    def _on_eof(self, name, value):
        """Handle end of file."""
        if value:
            with self._lock:
                self._state = "idle"
                self._current_media = None
                self._position = 0
            self._notify_state_change()
    
    async def play_media(self, media_url: str, media_type: str = None):
        """Play media from URL or file path."""
        try:
            with self._lock:
                self._current_media = media_url
                self._state = "playing"
            
            self._mpv_player.play(media_url)
            _LOGGER.info(f"Playing media: {media_url}")
            
        except Exception as e:
            _LOGGER.error(f"Failed to play media {media_url}: {e}")
            with self._lock:
                self._state = "idle"
                self._current_media = None
            raise
    
    async def pause(self):
        """Pause playback."""
        if self._mpv_player:
            self._mpv_player.pause = True
            _LOGGER.info("Playback paused")
    
    async def resume(self):
        """Resume playback."""
        if self._mpv_player:
            self._mpv_player.pause = False
            _LOGGER.info("Playback resumed")
    
    async def stop(self):
        """Stop playback."""
        if self._mpv_player:
            self._mpv_player.stop()
            with self._lock:
                self._state = "idle"
                self._current_media = None
                self._position = 0
            _LOGGER.info("Playback stopped")
    
    async def set_volume(self, volume: float):
        """Set volume level (0.0 to 1.0)."""
        try:
            if self._mpv_player:
                self._mpv_player.volume = volume * 100  # MPV uses 0-100
            
            with self._lock:
                self._volume = volume
                
            _LOGGER.info(f"Volume set to {volume}")
            
        except Exception as e:
            _LOGGER.error(f"Failed to set volume: {e}")
    
    async def set_mute(self, muted: bool):
        """Set mute state."""
        try:
            if self._mpv_player:
                self._mpv_player.mute = muted
            
            with self._lock:
                self._muted = muted
                
            _LOGGER.info(f"Mute set to {muted}")
            
        except Exception as e:
            _LOGGER.error(f"Failed to set mute: {e}")
    
    async def seek(self, position: float):
        """Seek to position in seconds."""
        try:
            if self._mpv_player and self._current_media:
                self._mpv_player.seek(position, reference='absolute')
                _LOGGER.info(f"Seeked to position {position}")
                
        except Exception as e:
            _LOGGER.error(f"Failed to seek: {e}")
    
    @property
    def state(self) -> str:
        """Get current playback state."""
        with self._lock:
            return self._state
    
    @property
    def volume_level(self) -> float:
        """Get current volume level."""
        with self._lock:
            return self._volume
    
    @property
    def is_muted(self) -> bool:
        """Get mute state."""
        with self._lock:
            return self._muted
    
    @property
    def current_media(self) -> Optional[str]:
        """Get currently playing media."""
        with self._lock:
            return self._current_media
    
    @property
    def media_position(self) -> float:
        """Get current position in seconds."""
        with self._lock:
            return self._position
    
    @property
    def media_duration(self) -> float:
        """Get media duration in seconds."""
        with self._lock:
            return self._duration
    
    async def cleanup(self):
        """Clean up resources."""
        try:
            if self._mpv_player:
                self._mpv_player.terminate()
                self._mpv_player = None
                
            _LOGGER.info("MPV backend cleaned up")
            
        except Exception as e:
            _LOGGER.error(f"Error during cleanup: {e}")