"""Media metadata extraction and handling."""

import asyncio
import logging
from typing import Dict, Any, Optional
from pathlib import Path
import aiofiles
from mutagen import File as MutagenFile
from mutagen.id3 import ID3NoHeaderError

_LOGGER = logging.getLogger(__name__)


class MetadataHandler:
    """Handle media file metadata extraction."""
    
    def __init__(self):
        """Initialize metadata handler."""
        self._cache = {}
    
    async def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata from media file."""
        try:
            # Check cache first
            if file_path in self._cache:
                return self._cache[file_path]
            
            # Run metadata extraction in thread pool to avoid blocking
            metadata = await asyncio.get_event_loop().run_in_executor(
                None, self._extract_metadata_sync, file_path
            )
            
            # Cache the result
            self._cache[file_path] = metadata
            return metadata
            
        except Exception as e:
            _LOGGER.error(f"Failed to extract metadata from {file_path}: {e}")
            return self._get_fallback_metadata(file_path)
    
    def _extract_metadata_sync(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata synchronously using mutagen."""
        try:
            audio_file = MutagenFile(file_path)
            if audio_file is None:
                return self._get_fallback_metadata(file_path)
            
            metadata = {}
            
            # Common tags across formats
            title = self._get_tag_value(audio_file, ['TIT2', 'TITLE', '\xa9nam'])
            artist = self._get_tag_value(audio_file, ['TPE1', 'ARTIST', '\xa9ART'])
            album = self._get_tag_value(audio_file, ['TALB', 'ALBUM', '\xa9alb'])
            date = self._get_tag_value(audio_file, ['TDRC', 'DATE', '\xa9day'])
            genre = self._get_tag_value(audio_file, ['TCON', 'GENRE', '\xa9gen'])
            track = self._get_tag_value(audio_file, ['TRCK', 'TRACKNUMBER', 'trkn'])
            
            metadata['title'] = title or Path(file_path).stem
            metadata['artist'] = artist
            metadata['album'] = album
            metadata['date'] = date
            metadata['genre'] = genre
            metadata['track'] = track
            
            # Duration
            if hasattr(audio_file, 'info') and audio_file.info:
                metadata['duration'] = getattr(audio_file.info, 'length', None)
            
            # Bitrate
            if hasattr(audio_file, 'info') and audio_file.info:
                metadata['bitrate'] = getattr(audio_file.info, 'bitrate', None)
            
            return metadata
            
        except (ID3NoHeaderError, Exception) as e:
            _LOGGER.debug(f"Could not extract metadata from {file_path}: {e}")
            return self._get_fallback_metadata(file_path)
    
    def _get_tag_value(self, audio_file, tag_keys: list) -> Optional[str]:
        """Get tag value from audio file, trying multiple possible keys."""
        for key in tag_keys:
            try:
                if key in audio_file:
                    value = audio_file[key]
                    if isinstance(value, list) and value:
                        return str(value[0])
                    elif value:
                        return str(value)
            except (KeyError, AttributeError):
                continue
        return None
    
    def _get_fallback_metadata(self, file_path: str) -> Dict[str, Any]:
        """Get fallback metadata when extraction fails."""
        return {
            'title': Path(file_path).stem,
            'artist': None,
            'album': None,
            'date': None,
            'genre': None,
            'track': None,
            'duration': None,
            'bitrate': None,
        }
    
    async def get_media_info(self, file_path: str) -> Dict[str, Any]:
        """Get comprehensive media information."""
        try:
            metadata = await self.extract_metadata(file_path)
            
            # Add file information
            path_obj = Path(file_path)
            if path_obj.exists():
                stat = path_obj.stat()
                metadata['file_size'] = stat.st_size
                metadata['file_modified'] = stat.st_mtime
            
            metadata['file_extension'] = path_obj.suffix.lower()
            metadata['file_name'] = path_obj.name
            
            return metadata
            
        except Exception as e:
            _LOGGER.error(f"Failed to get media info for {file_path}: {e}")
            return self._get_fallback_metadata(file_path)
    
    def clear_cache(self):
        """Clear metadata cache."""
        self._cache.clear()
        _LOGGER.info("Metadata cache cleared")
    
    async def preload_metadata(self, file_paths: list):
        """Preload metadata for multiple files."""
        tasks = [self.extract_metadata(path) for path in file_paths]
        await asyncio.gather(*tasks, return_exceptions=True)
        _LOGGER.info(f"Preloaded metadata for {len(file_paths)} files")