"""Configuration management for PipePlay."""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import os

_LOGGER = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "name": "PipePlay Player",
    "unique_id": "pipeplay_player",
    "device_class": "speaker",
    "api": {
        "enabled": True,
        "host": "0.0.0.0",
        "port": 8080,
    },
    "discovery": {
        "enabled": True,
        "name": "PipePlay Player",
    },
    "homeassistant": {
        "discovery_prefix": "homeassistant",
        "device_name": "PipePlay Media Player",
        "device_manufacturer": "PipePlay",
        "device_model": "PipeWire Player",
        "device_identifier": "pipeplay_pipewire_player",
    },
    "mqtt": {
        "enabled": False,
        "broker": "localhost",
        "port": 1883,
        "username": None,
        "password": None,
        "base_topic": "pipeplay",
    },
    "audio": {
        "default_volume": 0.5,
        "volume_step": 0.1,
        "fade_duration": 0.5,
    },
    "media": {
        "supported_formats": [".mp3", ".flac", ".wav", ".ogg", ".m4a", ".aac"],
        "metadata_cache_size": 1000,
        "metadata_cache_ttl": 3600,
    },
    "logging": {
        "level": "INFO",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    },
}


class Config:
    """Configuration manager for PipePlay."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration."""
        self._config_path = Path(config_path) if config_path else self._get_default_config_path()
        self._config = DEFAULT_CONFIG.copy()
        self._load_config()
    
    def _get_default_config_path(self) -> Path:
        """Get default configuration file path."""
        config_dir = Path.home() / ".config" / "pipeplay"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "config.json"
    
    def _load_config(self):
        """Load configuration from file."""
        try:
            if self._config_path.exists():
                with open(self._config_path, 'r') as f:
                    user_config = json.load(f)
                    self._merge_config(self._config, user_config)
                _LOGGER.info(f"Configuration loaded from {self._config_path}")
            else:
                self._save_config()
                _LOGGER.info(f"Created default configuration at {self._config_path}")
        except Exception as e:
            _LOGGER.error(f"Failed to load configuration: {e}")
            _LOGGER.info("Using default configuration")
    
    def _merge_config(self, base: Dict[str, Any], override: Dict[str, Any]):
        """Recursively merge configuration dictionaries."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value
    
    def _save_config(self):
        """Save current configuration to file."""
        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._config_path, 'w') as f:
                json.dump(self._config, f, indent=2)
            _LOGGER.info(f"Configuration saved to {self._config_path}")
        except Exception as e:
            _LOGGER.error(f"Failed to save configuration: {e}")
    
    def get(self, key: str, default=None):
        """Get configuration value using dot notation."""
        keys = key.split('.')
        value = self._config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any):
        """Set configuration value using dot notation."""
        keys = key.split('.')
        config = self._config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
        self._save_config()
    
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration values."""
        return self._config.copy()
    
    def update(self, updates: Dict[str, Any]):
        """Update multiple configuration values."""
        self._merge_config(self._config, updates)
        self._save_config()
    
    def reset_to_defaults(self):
        """Reset configuration to defaults."""
        self._config = DEFAULT_CONFIG.copy()
        self._save_config()
        _LOGGER.info("Configuration reset to defaults")
    
    @property
    def config_path(self) -> Path:
        """Get configuration file path."""
        return self._config_path


def load_config(config_path: Optional[str] = None) -> Config:
    """Load configuration from file or create default."""
    return Config(config_path)


def setup_logging(config: Config):
    """Set up logging based on configuration."""
    log_level = getattr(logging, config.get('logging.level', 'INFO').upper())
    log_format = config.get('logging.format', DEFAULT_CONFIG['logging']['format'])
    
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.StreamHandler(),
        ]
    )
    
    # Set specific logger levels
    logging.getLogger('pipeplay').setLevel(log_level)
    logging.getLogger('mpv').setLevel(logging.WARNING)  # MPV can be verbose