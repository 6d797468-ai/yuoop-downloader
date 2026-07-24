"""
YouTube playlist/mix extraction module.
Fetches video metadata without downloading.
"""

from __future__ import annotations

import subprocess
import json
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from utils.yt_dlp_runner import build_yt_dlp_command


@dataclass
class VideoInfo:
    """Information about a single video."""
    video_id: str
    title: str
    duration: int  # in seconds
    thumbnail_url: str
    url: str
    uploader: Optional[str] = None
    upload_date: Optional[str] = None


class YouTubePlaylistExtractor:
    """Extract video information from YouTube playlists, mixes, and channels."""
    
    def __init__(self):
        """Initialize extractor."""
        self.yt_dlp_cmd = build_yt_dlp_command
    
    def extract_videos(self, url: str, max_videos: Optional[int] = None) -> Tuple[List[VideoInfo], Optional[str]]:
        """
        Extract all video information from a playlist/mix/channel.
        
        Args:
            url: YouTube URL (playlist, mix, or channel)
            max_videos: Maximum number of videos to extract (None = all)
            
        Returns:
            Tuple of (list of VideoInfo, error_message)
            If error, returns ([], error_message)
        """
        try:
            # Build yt-dlp command with optimizations for playlist analysis
            cmd = self.yt_dlp_cmd(
                "--dump-json",
                "--no-warnings",
                "-i",  # Ignore errors for unavailable videos
                "--flat-playlist",  # Don't fetch full metadata, faster
                "--socket-timeout", "10",  # Network timeout
                url
            )
            
            # Add max videos limit if specified
            if max_videos:
                cmd.extend(["--playlist-items", f"1-{max_videos}"])
            
            # Execute command and capture output
            # Timeout increased to 120 seconds for large playlists
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                error_msg = result.stderr.strip() or "Unknown yt-dlp error"
                return [], error_msg
            
            # Parse JSON lines output
            videos = []
            for line in result.stdout.strip().split('\n'):
                if not line.strip():
                    continue
                
                try:
                    data = json.loads(line)
                    video = self._parse_video_data(data)
                    if video:
                        videos.append(video)
                except json.JSONDecodeError:
                    continue
            
            if not videos:
                return [], "No videos found in playlist"
            
            return videos, None
            
        except subprocess.TimeoutExpired:
            return [], "Timeout: Playlist analysis took too long (>120s). The URL might be invalid or your connection is slow. Try again or use a smaller playlist."
        except FileNotFoundError:
            return [], "yt-dlp not found. Please install: pip install yt-dlp"
        except Exception as e:
            return [], f"Error fetching playlist: {str(e)}"

    def extract_single_video(self, url: str) -> Tuple[List[VideoInfo], Optional[str]]:
        """
        Extract metadata for a single YouTube video.

        Args:
            url: YouTube video URL

        Returns:
            Tuple of (one-item VideoInfo list, error_message)
        """
        try:
            cmd = self.yt_dlp_cmd(
                "--dump-single-json",
                "--no-warnings",
                "--no-playlist",
                "--socket-timeout", "10",
                url,
            )

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip() or "Unknown yt-dlp error"
                return [], error_msg

            data = json.loads(result.stdout)
            video = self._parse_video_data(data)
            if not video:
                return [], "Could not parse video metadata"

            return [video], None

        except subprocess.TimeoutExpired:
            return [], "Timeout: Video analysis took too long (>60s). Try again or check your connection."
        except FileNotFoundError:
            return [], "yt-dlp not found. Please install: pip install yt-dlp"
        except json.JSONDecodeError:
            return [], "Could not parse yt-dlp response for this video"
        except Exception as e:
            return [], f"Error fetching video: {str(e)}"
    
    @staticmethod
    def _parse_video_data(data: Dict) -> Optional[VideoInfo]:
        """
        Parse video data from yt-dlp JSON output.
        
        Args:
            data: JSON data dictionary from yt-dlp
            
        Returns:
            VideoInfo object or None if parsing fails
        """
        try:
            # Extract video information
            video_id = data.get('id') or data.get('display_id')
            if not video_id:
                return None
            
            title = data.get('title', 'Untitled')
            duration = data.get('duration', 0)

            thumbnails = data.get('thumbnails') or []
            thumbnail_url = data.get('thumbnail') or ''
            if not thumbnail_url and thumbnails:
                thumbnail_url = thumbnails[-1].get('url', '')
            if not thumbnail_url:
                thumbnail_url = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"

            raw_url = data.get('webpage_url') or data.get('original_url') or data.get('url')
            url = raw_url if raw_url and str(raw_url).startswith('http') else f"https://www.youtube.com/watch?v={video_id}"
            uploader = data.get('uploader')
            upload_date = data.get('upload_date')
            
            return VideoInfo(
                video_id=video_id,
                title=title,
                duration=duration,
                thumbnail_url=thumbnail_url,
                url=url,
                uploader=uploader,
                upload_date=upload_date
            )
        except Exception:
            return None
    
    @staticmethod
    def format_duration(seconds: int) -> str:
        """
        Format duration in seconds to HH:MM:SS format.
        
        Args:
            seconds: Duration in seconds
            
        Returns:
            Formatted duration string
        """
        seconds = int(seconds) if seconds else 0
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"
