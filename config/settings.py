"""
Settings and configuration management for Yuoop Downloader.
Handles loading/saving user preferences, detecting system dependencies.
"""

import json
import os
import shutil
import logging
from pathlib import Path
from typing import Optional, Dict, Any


class ConfigManager:
    """Manages application configuration and user preferences."""
    
    def __init__(self, app_name: str = "yuoop-downloader"):
        """
        Initialize configuration manager.
        
        Args:
            app_name: Application name for config directory
        """
        self.app_name = app_name
        self.config_dir = self._get_config_dir()
        self.config_file = self.config_dir / "config.json"
        self.default_config_path = Path(__file__).parent / "default_config.json"
        self.logger = logging.getLogger(__name__)
        
        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Load or create config
        self.config = self._load_config()
    
    @staticmethod
    def _get_config_dir() -> Path:
        """Get OS-specific config directory."""
        if os.name == 'nt':  # Windows
            appdata = os.getenv('APPDATA')
            config_dir = Path(appdata) / "yuoop-downloader" if appdata else Path.home() / "yuoop-downloader"
        else:  # Linux/macOS
            config_dir = Path.home() / ".config" / "yuoop-downloader"
        return config_dir

    @staticmethod
    def _deep_merge(defaults: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
        """Merge user config over defaults without losing new default keys."""
        merged = defaults.copy()
        for key, value in overrides.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = ConfigManager._deep_merge(merged[key], value)
            else:
                merged[key] = value
        return merged
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file or create default.
        
        Returns:
            Configuration dictionary
        """
        with open(self.default_config_path, 'r', encoding='utf-8') as f:
            defaults = json.load(f)

        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                return self._deep_merge(defaults, user_config)
            except Exception as e:
                self.logger.warning(f"Failed to load config: {e}. Using defaults.")
                try:
                    backup_file = self.config_file.with_suffix(".json.bak")
                    shutil.copy2(self.config_file, backup_file)
                except Exception:
                    pass

        return defaults
    
    def save_config(self) -> bool:
        """
        Save current configuration to file.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get config value by dot-notation key (e.g., 'ui.theme')."""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default
    
    def set(self, key: str, value: Any) -> None:
        """Set config value by dot-notation key."""
        keys = key.split('.')
        config = self.config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
    
    @staticmethod
    def get_ffmpeg_binary_path() -> Optional[Path]:
        """
        Find FFmpeg binary path (system, bundled alongside exe, or in PyInstaller temp dir).

        Returns:
            Path object to ffmpeg binary if found, None otherwise
        """
        import sys
        binary_name = "ffmpeg.exe" if os.name == 'nt' else "ffmpeg"
        candidates = []

        # PyInstaller _MEIPASS
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            meipass_path = Path(sys._MEIPASS)
            candidates.extend([
                meipass_path / binary_name,
                meipass_path / "bin" / binary_name,
                meipass_path / "assets" / binary_name,
            ])

        # Next to executable
        exe_dir = Path(sys.executable).parent
        candidates.extend([
            exe_dir / binary_name,
            exe_dir / "bin" / binary_name,
            exe_dir / "ffmpeg" / binary_name,
        ])

        # Project root (dev mode)
        proj_root = Path(__file__).resolve().parent.parent
        candidates.extend([
            proj_root / binary_name,
            proj_root / "bin" / binary_name,
        ])

        for cand in candidates:
            if cand.is_file() and os.access(cand, os.X_OK):
                return cand

        which_path = shutil.which('ffmpeg')
        if which_path:
            return Path(which_path)

        return None

    @staticmethod
    def get_ffplay_binary_path() -> Optional[Path]:
        """Find FFplay binary path."""
        import sys
        binary_name = "ffplay.exe" if os.name == 'nt' else "ffplay"
        candidates = []

        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            meipass_path = Path(sys._MEIPASS)
            candidates.extend([
                meipass_path / binary_name,
                meipass_path / "bin" / binary_name,
                meipass_path / "assets" / binary_name,
            ])

        exe_dir = Path(sys.executable).parent
        candidates.extend([
            exe_dir / binary_name,
            exe_dir / "bin" / binary_name,
            exe_dir / "ffmpeg" / binary_name,
        ])

        proj_root = Path(__file__).resolve().parent.parent
        candidates.extend([
            proj_root / binary_name,
            proj_root / "bin" / binary_name,
        ])

        for cand in candidates:
            if cand.is_file() and os.access(cand, os.X_OK):
                return cand

        which_path = shutil.which('ffplay')
        if which_path:
            return Path(which_path)

        return None

    def detect_ffmpeg(self) -> bool:
        """
        Detect if FFmpeg is installed on system or bundled with app.
        
        Returns:
            True if FFmpeg found, False otherwise
        """
        path = self.get_ffmpeg_binary_path()
        if path:
            parent_str = str(path.parent)
            if parent_str not in os.environ.get('PATH', '').split(os.pathsep):
                os.environ['PATH'] = parent_str + os.pathsep + os.environ.get('PATH', '')
            return True
        return False

    def detect_ffplay(self) -> bool:
        """
        Detect if ffplay is installed on system or bundled with app.

        Returns:
            True if ffplay found, False otherwise
        """
        path = self.get_ffplay_binary_path()
        if path:
            parent_str = str(path.parent)
            if parent_str not in os.environ.get('PATH', '').split(os.pathsep):
                os.environ['PATH'] = parent_str + os.pathsep + os.environ.get('PATH', '')
            return True
        return False
    
    def get_color(self, color_name: str) -> str:
        """Get color value by name."""
        return self.config.get('colors', {}).get(color_name, '#ffffff')


# Global config instance
_config_manager: Optional[ConfigManager] = None


def get_config() -> ConfigManager:
    """Get or create global config manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
