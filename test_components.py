"""
Test script to verify all components work correctly.
Run this before distributing the application.
"""

import sys
import traceback
from pathlib import Path


def test_imports():
    """Test all module imports."""
    print("Testing imports...")
    modules = [
        ("config.settings", "get_config"),
        ("utils.validators", "is_valid_youtube_url"),
        ("utils.logger", "get_logger"),
        ("downloader.youtube", "YouTubePlaylistExtractor"),
        ("downloader.formats", "FormatManager"),
        ("downloader.queue_manager", "DownloadQueueManager"),
        ("player.video_player", "VideoPlayer"),
        ("ui.components", "VideoCard"),
        ("ui.app", "YuoopApp"),
    ]
    
    for module, cls in modules:
        try:
            mod = __import__(module, fromlist=[cls])
            getattr(mod, cls)
            print(f"  ✓ {module}.{cls}")
        except Exception as e:
            print(f"  ✗ {module}.{cls}: {e}")
            return False
    
    return True


def test_validators():
    """Test URL validators."""
    print("\nTesting validators...")
    from utils.validators import is_valid_youtube_url
    
    tests = [
        ("https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf", True),
        ("https://www.youtube.com/c/LinusTechTips", True),
        ("invalid", False),
    ]
    
    all_pass = True
    for url, should_be_valid in tests:
        is_valid, _ = is_valid_youtube_url(url)
        if is_valid == should_be_valid:
            print(f"  ✓ {url[:40]:<40} -> {'VALID' if is_valid else 'INVALID'}")
        else:
            print(f"  ✗ {url[:40]:<40} -> Expected {should_be_valid}")
            all_pass = False
    
    return all_pass


def test_formats():
    """Test format management."""
    print("\nTesting formats...")
    from downloader.formats import FormatManager
    
    formats = FormatManager.get_all_formats()
    if len(formats) == 6:
        print(f"  ✓ Found {len(formats)} formats")
        for fmt in formats:
            ext = FormatManager.get_extension(fmt)
            print(f"    - {fmt} -> {ext}")
        return True
    else:
        print(f"  ✗ Expected 6 formats, got {len(formats)}")
        return False


def test_config():
    """Test configuration system."""
    print("\nTesting configuration...")
    from config.settings import get_config
    
    config = get_config()
    
    # Test set/get
    config.set("test.value", "hello")
    value = config.get("test.value")
    if value == "hello":
        print("  ✓ Config set/get works")
    else:
        print(f"  ✗ Config set/get failed: {value}")
        return False
    
    # Test FFmpeg detection
    ffmpeg = config.detect_ffmpeg()
    print(f"  ✓ FFmpeg detection: {'Available' if ffmpeg else 'Not available'}")
    
    # Test colors
    color = config.get_color("accent_red")
    if color == "#ff0000":
        print(f"  ✓ Color retrieval works")
    else:
        print(f"  ✗ Color retrieval failed: {color}")
        return False
    
    return True


def test_logger():
    """Test logging system."""
    print("\nTesting logger...")
    from utils.logger import get_logger
    
    logger = get_logger()
    messages = []
    
    def capture(msg):
        messages.append(msg)
    
    logger.add_ui_callback(capture)
    logger.info("Test message")
    logger.success("Success message")
    logger.error("Error message")
    
    if len(messages) >= 3:
        print(f"  ✓ Logger received {len(messages)} messages")
        return True
    else:
        print(f"  ✗ Logger failed to capture messages: {len(messages)}")
        return False


def test_downloader_components():
    """Test downloader components."""
    print("\nTesting downloader components...")
    
    # Test queue manager initialization
    from downloader.queue_manager import DownloadQueueManager
    
    manager = DownloadQueueManager(num_workers=2)
    if manager.num_workers == 2:
        print("  ✓ DownloadQueueManager initialization works")
    else:
        print(f"  ✗ DownloadQueueManager init failed: {manager.num_workers}")
        return False
    
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Yuoop Downloader - Component Tests")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_validators,
        test_formats,
        test_config,
        test_logger,
        test_downloader_components,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"\n✗ Test failed with exception:")
            traceback.print_exc()
            results.append(False)
    
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} test groups passed")
    print("=" * 60)
    
    if all(results):
        print("\n✓ All tests passed! Application is ready for use.")
        return 0
    else:
        print("\n✗ Some tests failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
