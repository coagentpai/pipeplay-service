"""HTTP API server for PipePlay."""

import asyncio
import logging
from typing import Any, Dict, Optional
from aiohttp import web, hdrs
from aiohttp.web import Request, Response, json_response
import json

_LOGGER = logging.getLogger(__name__)


class PipePlayAPIServer:
    """HTTP API server for Home Assistant integration."""
    
    def __init__(self, media_player, host: str = "0.0.0.0", port: int = 8080):
        """Initialize API server."""
        self._media_player = media_player
        self._host = host
        self._port = port
        self._app = None
        self._runner = None
        self._site = None
    
    async def start(self):
        """Start the HTTP API server."""
        self._app = web.Application()
        self._setup_routes()
        
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        
        self._site = web.TCPSite(self._runner, self._host, self._port)
        await self._site.start()
        
        _LOGGER.info(f"PipePlay API server started on {self._host}:{self._port}")
    
    async def stop(self):
        """Stop the HTTP API server."""
        if self._site:
            await self._site.stop()
        if self._runner:
            await self._runner.cleanup()
        _LOGGER.info("PipePlay API server stopped")
    
    def _setup_routes(self):
        """Set up API routes."""
        # Add CORS middleware
        self._app.middlewares.append(self._cors_middleware)
        
        # API routes
        self._app.router.add_get('/api/status', self._handle_status)
        self._app.router.add_post('/api/command', self._handle_command)
        self._app.router.add_get('/api/info', self._handle_info)
        
        # Health check
        self._app.router.add_get('/health', self._handle_health)
    
    @web.middleware
    async def _cors_middleware(self, request: Request, handler):
        """Add CORS headers."""
        response = await handler(request)
        response.headers[hdrs.ACCESS_CONTROL_ALLOW_ORIGIN] = '*'
        response.headers[hdrs.ACCESS_CONTROL_ALLOW_METHODS] = 'GET, POST, OPTIONS'
        response.headers[hdrs.ACCESS_CONTROL_ALLOW_HEADERS] = 'Content-Type'
        return response
    
    async def _handle_status(self, request: Request) -> Response:
        """Handle status request."""
        try:
            if not self._media_player:
                return json_response({
                    "service": "pipeplay",
                    "status": "no_player",
                    "error": "Media player not initialized"
                }, status=503)
            
            # Get state from media player
            state_data = {
                "service": "pipeplay",
                "status": "ok",
                "state": self._media_player.state,
                "volume_level": self._media_player.volume_level,
                "is_muted": self._media_player.is_volume_muted,
                "media_title": self._media_player.media_title,
                "media_artist": self._media_player.media_artist,
                "media_album": self._media_player.media_album_name,
                "media_position": self._media_player.media_position,
                "media_duration": self._media_player.media_duration,
                "media_content_type": self._media_player.media_content_type,
            }
            
            return json_response(state_data)
            
        except Exception as e:
            _LOGGER.error(f"Error handling status request: {e}")
            return json_response({
                "service": "pipeplay",
                "status": "error",
                "error": str(e)
            }, status=500)
    
    async def _handle_command(self, request: Request) -> Response:
        """Handle command request."""
        try:
            data = await request.json()
            command = data.get("command")
            
            if not self._media_player:
                return json_response({
                    "success": False,
                    "error": "Media player not initialized"
                }, status=503)
            
            if command == "play":
                await self._media_player.async_media_play()
            elif command == "pause":
                await self._media_player.async_media_pause()
            elif command == "stop":
                await self._media_player.async_media_stop()
            elif command == "play_media":
                media_type = data.get("media_type", "music")
                media_id = data.get("media_id")
                if not media_id:
                    return json_response({
                        "success": False,
                        "error": "media_id required for play_media command"
                    }, status=400)
                await self._media_player.async_play_media(media_type, media_id)
            elif command == "volume":
                level = data.get("level")
                if level is None or not 0 <= level <= 1:
                    return json_response({
                        "success": False,
                        "error": "level must be between 0 and 1"
                    }, status=400)
                await self._media_player.async_set_volume_level(level)
            elif command == "mute":
                muted = data.get("muted")
                if muted is None:
                    return json_response({
                        "success": False,
                        "error": "muted parameter required"
                    }, status=400)
                await self._media_player.async_mute_volume(muted)
            elif command == "seek":
                position = data.get("position")
                if position is None:
                    return json_response({
                        "success": False,
                        "error": "position parameter required"
                    }, status=400)
                await self._media_player.async_media_seek(position)
            else:
                return json_response({
                    "success": False,
                    "error": f"Unknown command: {command}"
                }, status=400)
            
            return json_response({"success": True})
            
        except json.JSONDecodeError:
            return json_response({
                "success": False,
                "error": "Invalid JSON"
            }, status=400)
        except Exception as e:
            _LOGGER.error(f"Error handling command: {e}")
            return json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def _handle_info(self, request: Request) -> Response:
        """Handle info request."""
        return json_response({
            "service": "pipeplay",
            "version": "0.1.0",
            "name": "PipePlay PipeWire Media Player",
            "api_version": "1.0",
            "supported_features": [
                "play", "pause", "stop", "volume_set", "volume_mute", 
                "seek", "play_media"
            ],
            "supported_media_types": [
                "music", "podcast", "url"
            ],
        })
    
    async def _handle_health(self, request: Request) -> Response:
        """Handle health check."""
        return json_response({
            "status": "healthy",
            "service": "pipeplay"
        })
    
    @property
    def port(self) -> int:
        """Get the server port."""
        return self._port
    
    @property
    def host(self) -> str:
        """Get the server host."""
        return self._host