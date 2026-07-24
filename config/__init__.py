"""
Configuration module for Yuoop Downloader.

Provides access to user preferences, system detection, and application settings.
"""

from config.settings import ConfigManager, get_config

__all__ = ['ConfigManager', 'get_config']