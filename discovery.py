"""Home Assistant integration helpers."""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

try:
    import asyncio_mqtt as aiomqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False

_LOGGER = logging.getLogger(__name__)


class HomeAssistantIntegration:
    """Handle Home Assistant integration (custom component approach)."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize integration helper."""
        self._config = config
        self._mqtt_client: Optional[aiomqtt.Client] = None
        self._entity_id = config.get('unique_id', 'pipeplay_player')
        self._base_topic = config.get('mqtt', {}).get('base_topic', 'pipeplay')
    
    async def setup_mqtt_state_publishing(self) -> bool:
        """Set up MQTT state publishing for manual integration."""
        if not MQTT_AVAILABLE:
            _LOGGER.warning("asyncio-mqtt not available - MQTT disabled")
            return False
        
        mqtt_config = self._config.get('mqtt', {})
        if not mqtt_config.get('enabled', False):
            _LOGGER.info("MQTT disabled in configuration")
            return False
        
        try:
            self._mqtt_client = aiomqtt.Client(
                hostname=mqtt_config.get('broker', 'localhost'),
                port=mqtt_config.get('port', 1883),
                username=mqtt_config.get('username'),
                password=mqtt_config.get('password'),
            )
            
            _LOGGER.info("MQTT client configured for state publishing")
            return True
            
        except Exception as e:
            _LOGGER.error(f"Failed to setup MQTT: {e}")
            return False
    
    async def publish_state(self, state_data: Dict[str, Any]):
        """Publish current state to MQTT for manual media_player configuration."""
        if not self._mqtt_client:
            return
        
        try:
            async with self._mqtt_client:
                # Publish state topics that can be used in manual MQTT media_player config
                await self._mqtt_client.publish(f"{self._base_topic}/state", state_data.get('state', 'idle'))
                await self._mqtt_client.publish(f"{self._base_topic}/volume", str(state_data.get('volume_level', 0.5)))
                await self._mqtt_client.publish(f"{self._base_topic}/muted", 'true' if state_data.get('is_muted', False) else 'false')
                
                if 'media_position' in state_data and state_data['media_position'] is not None:
                    await self._mqtt_client.publish(f"{self._base_topic}/position", str(state_data['media_position']))
                
                if 'media_duration' in state_data and state_data['media_duration'] is not None:
                    await self._mqtt_client.publish(f"{self._base_topic}/duration", str(state_data['media_duration']))
                
                if 'media_title' in state_data and state_data['media_title']:
                    await self._mqtt_client.publish(f"{self._base_topic}/title", state_data['media_title'])
                
                if 'media_artist' in state_data and state_data['media_artist']:
                    await self._mqtt_client.publish(f"{self._base_topic}/artist", state_data['media_artist'])
                
                if 'media_album' in state_data and state_data['media_album']:
                    await self._mqtt_client.publish(f"{self._base_topic}/album", state_data['media_album'])
                
                # Availability
                await self._mqtt_client.publish(f"{self._base_topic}/availability", "online", retain=True)
                
        except Exception as e:
            _LOGGER.error(f"Failed to publish state: {e}")
    
    async def listen_for_commands(self, command_callback):
        """Listen for MQTT commands and call callback function."""
        if not self._mqtt_client:
            return
        
        try:
            async with self._mqtt_client:
                # Subscribe to command topics
                await self._mqtt_client.subscribe(f"{self._base_topic}/command")
                await self._mqtt_client.subscribe(f"{self._base_topic}/volume/set")
                await self._mqtt_client.subscribe(f"{self._base_topic}/mute/set")
                await self._mqtt_client.subscribe(f"{self._base_topic}/seek/set")
                
                async for message in self._mqtt_client.messages:
                    topic = message.topic.value
                    payload = message.payload.decode()
                    
                    if topic == f"{self._base_topic}/command":
                        await command_callback('media_command', payload)
                    elif topic == f"{self._base_topic}/volume/set":
                        await command_callback('volume', float(payload))
                    elif topic == f"{self._base_topic}/mute/set":
                        await command_callback('mute', payload.lower() in ['true', '1', 'on'])
                    elif topic == f"{self._base_topic}/seek/set":
                        await command_callback('seek', float(payload))
                        
        except Exception as e:
            _LOGGER.error(f"Error listening for commands: {e}")
    
    async def cleanup(self):
        """Clean up MQTT resources."""
        if self._mqtt_client:
            try:
                async with self._mqtt_client:
                    await self._mqtt_client.publish(f"{self._base_topic}/availability", "offline", retain=True)
            except Exception as e:
                _LOGGER.error(f"Error during MQTT cleanup: {e}")
    
    def generate_hass_config(self) -> str:
        """Generate Home Assistant configuration.yaml snippet for manual integration."""
        config = f"""
# Add this to your Home Assistant configuration.yaml:

media_player:
  - platform: mqtt
    name: "{self._config.get('name', 'PipePlay Player')}"
    unique_id: "{self._entity_id}"
    state_topic: "{self._base_topic}/state"
    command_topic: "{self._base_topic}/command"
    volume_state_topic: "{self._base_topic}/volume"
    volume_command_topic: "{self._base_topic}/volume/set"
    mute_state_topic: "{self._base_topic}/muted"
    mute_command_topic: "{self._base_topic}/mute/set"
    media_position_topic: "{self._base_topic}/position"
    media_duration_topic: "{self._base_topic}/duration"
    media_title_topic: "{self._base_topic}/title"
    media_artist_topic: "{self._base_topic}/artist"
    media_album_name_topic: "{self._base_topic}/album"
    availability_topic: "{self._base_topic}/availability"
    payload_available: "online"
    payload_not_available: "offline"
    supported_features:
      - play
      - pause  
      - stop
      - volume_set
      - volume_mute
      - seek
"""
        return config


def create_custom_component_files(output_dir: str, config: Dict[str, Any]):
    """Create Home Assistant custom component files."""
    component_dir = Path(output_dir) / "custom_components" / "pipeplay"
    component_dir.mkdir(parents=True, exist_ok=True)
    
    # __init__.py
    init_content = '''"""PipePlay PipeWire Media Player integration."""
import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

DOMAIN = "pipeplay"

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the PipePlay component."""
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up PipePlay from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    await hass.config_entries.async_forward_entry_setups(entry, ["media_player"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, ["media_player"])
'''
    
    # manifest.json
    manifest_content = {
        "domain": "pipeplay",
        "name": "PipePlay PipeWire Media Player",
        "version": "0.1.0",
        "documentation": "https://github.com/coagentpai/pipeplay",
        "requirements": [
            "pulsectl>=22.3.2",
            "python-mpv>=1.0.4",
            "mutagen>=1.47.0",
        ],
        "codeowners": ["@pipeplay"],
        "config_flow": True,
        "dependencies": [],
        "after_dependencies": [],
        "iot_class": "local_polling",
        "quality_scale": "silver",
    }
    
    # Write files
    with open(component_dir / "__init__.py", "w") as f:
        f.write(init_content)
    
    with open(component_dir / "manifest.json", "w") as f:
        json.dump(manifest_content, f, indent=2)
    
    _LOGGER.info(f"Custom component files created in {component_dir}")