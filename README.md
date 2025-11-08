# PipePlay - PipeWire Media Player

A lightweight media player designed for seamless integration with Home Assistant, using PipeWire for audio playback.

## Features

- **PipeWire Integration**: Uses PipeWire via PulseAudio compatibility for robust audio playback
- **Home Assistant Ready**: Provides HTTP API and Zeroconf discovery for HA integration
- **Metadata Support**: Extracts and displays media metadata (title, artist, album, etc.)
- **Audio Controls**: Play, pause, stop, volume control, seek, and mute functionality
- **Multiple Audio Formats**: Supports MP3, FLAC, WAV, OGG, M4A, AAC
- **Standalone Operation**: Can run independently or as a service

## Installation

### Prerequisites

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install python3-pip pipewire pulseaudio-utils libmpv2 libmpv-dev
```

#### Fedora/RHEL
```bash
sudo dnf install python3-pip pipewire pulseaudio-utils mpv mpv-devel
```

### Install PipePlay

```bash
git clone <repository-url>
cd pipeplay
pip install -e .
```

## Configuration

The configuration file is automatically created at `~/.config/pipeplay/config.json` on first run.

### Basic Configuration

```json
{
  "name": "PipePlay Player",
  "unique_id": "pipeplay_player",
  "device_class": "speaker",
  "api": {
    "enabled": true,
    "host": "0.0.0.0",
    "port": 8080
  },
  "discovery": {
    "enabled": true,
    "name": "PipePlay Player"
  },
  "audio": {
    "default_volume": 0.5,
    "volume_step": 0.1
  }
}
```

## Usage

### Command Line

```bash
# Interactive mode
pipeplay

# Play a file immediately
pipeplay --play /path/to/music.mp3

# Run as daemon service
pipeplay --daemon

# Use custom config
pipeplay --config /path/to/config.json
```

### Interactive Commands

When running in interactive mode:

- `play <file/url>` - Play media file or stream
- `pause` - Pause playback
- `resume` - Resume playback
- `stop` - Stop playback
- `volume <0-1>` - Set volume level
- `status` - Show current status
- `quit` - Exit

## Home Assistant Integration

PipePlay provides automatic discovery and API endpoints for Home Assistant integration:

- **HTTP API**: Runs on port 8080 by default
- **Zeroconf Discovery**: Broadcasts as `_pipeplay._tcp.local.`
- **Real-time Updates**: Live status via HTTP polling

For Home Assistant integration, install the [PipePlay Home Assistant Integration](https://github.com/coagentpai/pipeplay-ha).

## API Endpoints

- `GET /api/status` - Get current player status
- `POST /api/command` - Send control commands
- `GET /api/info` - Get service information
- `GET /health` - Health check

### Example Commands

```bash
# Get status
curl http://localhost:8080/api/status

# Play media
curl -X POST http://localhost:8080/api/command \
  -H "Content-Type: application/json" \
  -d '{"command": "play_media", "media_type": "music", "media_id": "/path/to/file.mp3"}'

# Set volume
curl -X POST http://localhost:8080/api/command \
  -H "Content-Type: application/json" \
  -d '{"command": "volume", "level": 0.5}'
```

## Docker

### Docker Compose

Run PipePlay using Docker Compose for Home Assistant integration:

```yaml
version: '3.8'

services:
  pipeplay:
    build: .
    container_name: pipeplay-service
    ports:
      - "8080:8080"
    volumes:
      - ./config:/app/.config/pipeplay
      - /run/user/1000/pipewire-0:/run/user/1000/pipewire-0
    environment:
      - XDG_RUNTIME_DIR=/run/user/1000
      - PIPEWIRE_RUNTIME_DIR=/run/user/1000/pipewire-0
    user: "1000:1000"  # Match your host user ID
    restart: unless-stopped
    network_mode: host  # Required for Zeroconf discovery
```

Save this as `docker-compose.yml` and run:

```bash
# Build and start the service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the service
docker-compose down
```

### Docker Build

Build the Docker image manually:

```bash
# Build the image
docker build -t pipeplay:latest .

# Run the container
docker run -d \
  --name pipeplay \
  --network host \
  --user 1000:1000 \
  -e XDG_RUNTIME_DIR=/run/user/1000 \
  -e PIPEWIRE_RUNTIME_DIR=/run/user/1000/pipewire-0 \
  -v ./config:/app/.config/pipeplay \
  -v /run/user/1000/pipewire-0:/run/user/1000/pipewire-0 \
  pipeplay:latest
```

## Development

### Project Structure

```
pipeplay/
├── __init__.py
├── main.py              # Main entry point and service
├── media_player.py      # Home Assistant media player entity
├── pipewire_backend.py  # PipeWire audio backend
├── metadata_handler.py  # Media metadata extraction
├── api_server.py        # HTTP API server
├── zeroconf_discovery.py # Zeroconf service registration
├── discovery.py         # Home Assistant integration helpers
└── config.py           # Configuration management
```

### Dependencies

- **pulsectl**: PulseAudio/PipeWire control
- **python-mpv**: Media playback via libmpv
- **mutagen**: Audio metadata extraction
- **aiohttp**: HTTP API server
- **zeroconf**: Network service discovery

## Troubleshooting

### Common Issues

1. **No audio output**
   - Check PipeWire/PulseAudio is running: `systemctl --user status pipewire`
   - Verify audio devices: `pactl list sinks`

2. **Media files not playing**
   - Check file permissions
   - Verify supported format
   - Check logs for MPV errors

3. **Service not discovered**
   - Verify API server is running on port 8080
   - Check firewall settings
   - Ensure zeroconf/avahi is available

### Logging

Enable debug logging in config:

```json
{
  "logging": {
    "level": "DEBUG"
  }
}
```

## License

MIT License - see LICENSE file for details.