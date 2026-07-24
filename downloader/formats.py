"""
Format definitions and yt-dlp format string mappings.
"""

from __future__ import annotations

from typing import Dict, Tuple


class FormatManager:
    """Manages video/audio formats and corresponding yt-dlp format strings."""
    
    # Format definitions: name -> (yt-dlp format string, audio_format)
    FORMATS: Dict[str, Tuple[str, str]] = {
        # Video formats
        'MP4 1080p': ('bestvideo[height<=1080]+bestaudio/best', 'mp4'),
        'MP4 720p': ('bestvideo[height<=720]+bestaudio/best', 'mp4'),
        'MP4 480p': ('bestvideo[height<=480]+bestaudio/best', 'mp4'),
        
        # Audio formats
        'MP3 320kbps': ('bestaudio/best', 'mp3'),
        'MP3 192kbps': ('bestaudio/best', 'mp3'),
        'WAV': ('bestaudio/best', 'wav'),
    }
    
    # Post-processing for different formats
    POSTPROCESSORS: Dict[str, Dict] = {
        'mp4': {
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        },
        'mp3': {
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '320',  # Will be adjusted based on format
        },
        'wav': {
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
        },
    }
    
    @classmethod
    def get_format_string(cls, format_name: str) -> str:
        """
        Get yt-dlp format string for a format name.
        
        Args:
            format_name: Format name (e.g., 'MP4 720p')
            
        Returns:
            yt-dlp format string
        """
        if format_name not in cls.FORMATS:
            return 'best'  # Fallback
        return cls.FORMATS[format_name][0]
    
    @classmethod
    def get_audio_format(cls, format_name: str) -> str:
        """
        Get audio format type for a format name.
        
        Args:
            format_name: Format name
            
        Returns:
            Audio format ('mp3', 'mp4', 'wav')
        """
        if format_name not in cls.FORMATS:
            return 'mp4'
        return cls.FORMATS[format_name][1]

    @classmethod
    def get_audio_quality(cls, format_name: str) -> str:
        """
        Get audio quality for an audio format.

        Args:
            format_name: Format name

        Returns:
            yt-dlp audio quality value
        """
        if '192kbps' in format_name:
            return '192K'
        if '320kbps' in format_name:
            return '320K'
        return '0'
    
    @classmethod
    def get_postprocessor(cls, format_name: str) -> Dict:
        """
        Get postprocessor configuration for a format.
        
        Args:
            format_name: Format name
            
        Returns:
            Postprocessor configuration dictionary
        """
        audio_format = cls.get_audio_format(format_name)
        
        if audio_format not in cls.POSTPROCESSORS:
            return {}
        
        pp = cls.POSTPROCESSORS[audio_format].copy()
        
        # Adjust quality for MP3
        if audio_format == 'mp3':
            if '320kbps' in format_name:
                pp['preferredquality'] = '320'
            elif '192kbps' in format_name:
                pp['preferredquality'] = '192'
        
        return pp
    
    @classmethod
    def get_extension(cls, format_name: str) -> str:
        """
        Get file extension for a format.
        
        Args:
            format_name: Format name
            
        Returns:
            File extension (e.g., '.mp4', '.mp3')
        """
        audio_format = cls.get_audio_format(format_name)
        if audio_format == 'mp4':
            return '.mp4'
        elif audio_format == 'mp3':
            return '.mp3'
        elif audio_format == 'wav':
            return '.wav'
        return '.mp4'
    
    @classmethod
    def is_audio_only(cls, format_name: str) -> bool:
        """
        Check if format is audio-only.
        
        Args:
            format_name: Format name
            
        Returns:
            True if audio-only format
        """
        return cls.get_audio_format(format_name) in ['mp3', 'wav']
    
    @classmethod
    def get_all_formats(cls) -> list[str]:
        """Get list of all available format names."""
        return list(cls.FORMATS.keys())
    
    @classmethod
    def get_video_formats(cls) -> list[str]:
        """Get list of video format names."""
        return [name for name in cls.FORMATS.keys() if 'MP4' in name]
    
    @classmethod
    def get_audio_formats(cls) -> list[str]:
        """Get list of audio format names."""
        return [name for name in cls.FORMATS.keys() if 'MP3' in name or 'WAV' in name]
