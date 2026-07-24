"""
Yuoop - YouTube Downloader
A lightweight desktop application for downloading YouTube playlists and mixes.
"""

import sys
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


def setup_logging():
    """Configure logging system."""
    from utils.logger import get_log_file_path
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            RotatingFileHandler(
                get_log_file_path(),
                maxBytes=1_000_000,
                backupCount=3,
                encoding='utf-8'
            ),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)


def check_display():
    """Check if display is available (for GUI)."""
    if os.name == 'nt':  # Windows always has display
        return True
    
    # Linux/macOS: check DISPLAY variable
    return 'DISPLAY' in os.environ or 'WAYLAND_DISPLAY' in os.environ


def main():
    """Main entry point."""
    logger = setup_logging()
    
    try:
        # Check if running in GUI environment
        if not check_display() and os.name != 'nt':
            logger.error("No display available. Cannot run GUI application.")
            print("Error: No display available. Run with a display server (X11, Wayland, etc.)")
            return 1
        
        # Import and start application
        from ui.app import YuoopApp
        
        logger.info("Starting Yuoop downloader...")
        app = YuoopApp()
        app.mainloop()
        
        return 0
        
    except ImportError as e:
        logger.error(f"Import error: {e}")
        print(f"Error: Missing dependency - {e}")
        print("Run: pip install -r requirements.txt")
        return 1
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
