"""
Downloader module for Yuoop Downloader.

Provides YouTube playlist extraction, format management, and download queue management.
"""

from downloader.youtube import YouTubePlaylistExtractor, VideoInfo
from downloader.formats import FormatManager
from downloader.queue_manager import DownloadQueueManager, DownloadTask

__all__ = ['YouTubePlaylistExtractor', 'VideoInfo', 'FormatManager', 'DownloadQueueManager', 'DownloadTask']