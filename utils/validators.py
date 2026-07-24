"""
Validators for URLs, paths, and other inputs.
"""

import re
from urllib.parse import urlparse, parse_qs
from typing import Tuple, Optional


def is_valid_youtube_url(url: str) -> Tuple[bool, Optional[str]]:
    """
    Validate if URL is a valid YouTube playlist, mix, or channel.
    
    Args:
        url: URL string to validate
        
    Returns:
        Tuple of (is_valid, url_type) where url_type is 'playlist', 'mix', 'channel', 'video', or None
    """
    url = url.strip()
    if not url:
        return False, None
    
    try:
        parsed = urlparse(url)
    except Exception:
        return False, None
    
    # Check if it's a YouTube domain
    if parsed.netloc not in ['www.youtube.com', 'youtube.com', 'm.youtube.com', 'youtu.be']:
        return False, None
    
    # Playlist URL
    if 'list=' in parsed.query:
        query_params = parse_qs(parsed.query)
        list_id = query_params.get('list', [''])[0]
        if list_id.startswith('RD') or 'RD' in list_id:
            return True, 'mix'
        return True, 'playlist'
    
    # Channel URL
    if '/channel/' in parsed.path or '/c/' in parsed.path or '/user/' in parsed.path or '/@' in parsed.path:
        return True, 'channel'
    
    # Single video (might still be in a playlist context)
    if '/watch' in parsed.path or 'youtu.be' in parsed.netloc:
        return True, 'video'
    
    return False, None


def sanitize_filename(filename: str, max_length: int = 200) -> str:
    """
    Sanitize filename for filesystem compatibility.
    
    Args:
        filename: Original filename
        max_length: Maximum length
        
    Returns:
        Safe filename
    """
    # Remove invalid characters
    invalid_chars = r'[<>:"/\\|?*]'
    filename = re.sub(invalid_chars, '_', filename)
    
    # Replace multiple underscores
    filename = re.sub(r'_+', '_', filename)
    
    # Truncate if needed
    if len(filename) > max_length:
        # Keep extension if present
        if '.' in filename:
            name, ext = filename.rsplit('.', 1)
            filename = name[:max_length - len(ext) - 1] + '.' + ext
        else:
            filename = filename[:max_length]
    
    return filename.strip()


def is_valid_format(format_str: str) -> bool:
    """
    Check if format string is valid.
    
    Args:
        format_str: Format identifier (e.g., 'MP4 720p', 'MP3 320kbps')
        
    Returns:
        True if valid format
    """
    valid_formats = [
        'MP4 1080p', 'MP4 720p', 'MP4 480p',
        'MP3 320kbps', 'MP3 192kbps', 'WAV'
    ]
    return format_str in valid_formats


def get_file_extension(format_str: str) -> str:
    """
    Get file extension for a format.
    
    Args:
        format_str: Format identifier
        
    Returns:
        File extension (e.g., '.mp4', '.mp3')
    """
    if 'MP4' in format_str:
        return '.mp4'
    elif 'MP3' in format_str:
        return '.mp3'
    elif 'WAV' in format_str:
        return '.wav'
    return '.mp4'  # Default
