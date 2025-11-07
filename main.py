"""Main entry point for PipePlay."""

import asyncio
import argparse
import logging
import signal
import sys
from pathlib import Path
from typing import Optional

from .config import load_config, setup_logging
from .media_player import PipePlayPlayer
from .discovery import HomeAssistantIntegration
from .api_server import PipePlayAPIServer
from .zeroconf_discovery import PipePlayZeroconfService


_LOGGER = logging.getLogger(__name__)


class PipePlayService:
    """Main PipePlay service."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the service."""
        self._config = load_config(config_path)
        setup_logging(self._config)
        
        self._media_player: Optional[PipePlayPlayer] = None
        self._ha_integration: Optional[HomeAssistantIntegration] = None
        self._api_server: Optional[PipePlayAPIServer] = None
        self._zeroconf_service: Optional[PipePlayZeroconfService] = None
        self._running = False
        self._shutdown_event = asyncio.Event()
    
    async def start(self):
        """Start the PipePlay service."""
        try:
            _LOGGER.info("Starting PipePlay service...")
            
            # Initialize media player
            self._media_player = PipePlayPlayer(
                hass=None,  # For standalone mode
                name=self._config.get('name', 'PipePlay Player')
            )
            
            # Start HTTP API server for HA custom component
            api_config = self._config.get('api', {})
            if api_config.get('enabled', True):  # Enabled by default
                host = api_config.get('host', '0.0.0.0')
                port = api_config.get('port', 8080)
                self._api_server = PipePlayAPIServer(self._media_player, host, port)
                await self._api_server.start()
                
                # Start Zeroconf discovery for automatic detection
                discovery_config = self._config.get('discovery', {})
                if discovery_config.get('enabled', True):  # Enabled by default
                    service_name = discovery_config.get('name', self._config.get('name', 'PipePlay Player'))
                    self._zeroconf_service = PipePlayZeroconfService(service_name, port, host)
                    await self._zeroconf_service.start()

            # Initialize HA integration if enabled (for MQTT option)
            ha_config = self._config.get('homeassistant', {})
            if ha_config:
                self._ha_integration = HomeAssistantIntegration(ha_config)
                await self._ha_integration.setup_mqtt_state_publishing()
                
                # Print configuration snippet for manual integration
                if self._ha_integration._mqtt_client:
                    print("MQTT enabled. Add this to your Home Assistant configuration.yaml:")
                    print(self._ha_integration.generate_hass_config())
            
            # Set up signal handlers
            self._setup_signal_handlers()
            
            self._running = True
            _LOGGER.info("PipePlay service started successfully")
            
            # Main service loop
            await self._run_service()
            
        except Exception as e:
            _LOGGER.error(f"Failed to start service: {e}")
            raise
    
    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            _LOGGER.info(f"Received signal {signum}, initiating shutdown...")
            self._shutdown_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def _run_service(self):
        """Main service loop."""
        try:
            # Wait for shutdown signal
            await self._shutdown_event.wait()
            
        except Exception as e:
            _LOGGER.error(f"Error in service loop: {e}")
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the PipePlay service."""
        if not self._running:
            return
        
        _LOGGER.info("Stopping PipePlay service...")
        self._running = False
        
        # Clean up media player
        if self._media_player:
            try:
                await self._media_player.async_will_remove_from_hass()
            except Exception as e:
                _LOGGER.error(f"Error stopping media player: {e}")
        
        # Clean up HA integration
        if self._ha_integration:
            try:
                await self._ha_integration.cleanup()
            except Exception as e:
                _LOGGER.error(f"Error cleaning up HA integration: {e}")
        
        # Clean up API server
        if self._api_server:
            try:
                await self._api_server.stop()
            except Exception as e:
                _LOGGER.error(f"Error stopping API server: {e}")
        
        # Clean up Zeroconf service
        if self._zeroconf_service:
            try:
                await self._zeroconf_service.stop()
            except Exception as e:
                _LOGGER.error(f"Error stopping Zeroconf service: {e}")
        
        _LOGGER.info("PipePlay service stopped")
    
    async def play_media(self, media_url: str, media_type: str = "music"):
        """Play media - for API/external control."""
        if self._media_player:
            await self._media_player.async_play_media(media_type, media_url)
    
    async def get_state(self) -> dict:
        """Get current player state."""
        if not self._media_player:
            return {"state": "unavailable"}
        
        return {
            "state": self._media_player.state,
            "volume_level": self._media_player.volume_level,
            "is_muted": self._media_player.is_volume_muted,
            "media_title": self._media_player.media_title,
            "media_artist": self._media_player.media_artist,
            "media_album": self._media_player.media_album_name,
            "media_position": self._media_player.media_position,
            "media_duration": self._media_player.media_duration,
        }


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="PipePlay - PipeWire Media Player for Home Assistant")
    parser.add_argument(
        "--config", "-c",
        type=str,
        help="Path to configuration file"
    )
    parser.add_argument(
        "--play",
        type=str,
        help="Play media file or URL immediately"
    )
    parser.add_argument(
        "--daemon", "-d",
        action="store_true",
        help="Run as daemon service"
    )
    parser.add_argument(
        "--version", "-v",
        action="version",
        version="PipePlay 0.1.0"
    )
    
    args = parser.parse_args()
    
    try:
        service = PipePlayService(args.config)
        
        if args.play:
            # Quick play mode
            _LOGGER.info(f"Playing media: {args.play}")
            await service.start()
            await service.play_media(args.play)
            # Keep playing until interrupted
            await service._shutdown_event.wait()
        elif args.daemon:
            # Daemon mode
            await service.start()
        else:
            # Interactive mode
            print("PipePlay Media Player")
            print("Commands: play <file/url>, pause, resume, stop, volume <0-1>, quit")
            
            await service.start()
            
            # Simple interactive loop
            while service._running:
                try:
                    cmd = input("> ").strip().split()
                    if not cmd:
                        continue
                    
                    if cmd[0] == "quit":
                        break
                    elif cmd[0] == "play" and len(cmd) > 1:
                        await service.play_media(cmd[1])
                    elif cmd[0] == "pause":
                        if service._media_player:
                            await service._media_player.async_media_pause()
                    elif cmd[0] == "resume":
                        if service._media_player:
                            await service._media_player.async_media_play()
                    elif cmd[0] == "stop":
                        if service._media_player:
                            await service._media_player.async_media_stop()
                    elif cmd[0] == "volume" and len(cmd) > 1:
                        try:
                            vol = float(cmd[1])
                            if service._media_player:
                                await service._media_player.async_set_volume_level(vol)
                        except ValueError:
                            print("Invalid volume level")
                    elif cmd[0] == "status":
                        state = await service.get_state()
                        print(f"State: {state}")
                    else:
                        print("Unknown command")
                        
                except (EOFError, KeyboardInterrupt):
                    break
                except Exception as e:
                    print(f"Error: {e}")
    
    except KeyboardInterrupt:
        _LOGGER.info("Interrupted by user")
    except Exception as e:
        _LOGGER.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())