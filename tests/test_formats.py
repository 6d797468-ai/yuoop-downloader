from downloader.formats import FormatManager


def test_format_lists_are_stable():
    assert "MP4 720p" in FormatManager.get_video_formats()
    assert "MP3 320kbps" in FormatManager.get_audio_formats()
    assert set(FormatManager.get_all_formats()) >= {"MP4 1080p", "MP4 720p", "MP3 192kbps", "WAV"}


def test_format_mapping_and_extensions():
    assert FormatManager.get_extension("MP4 720p") == ".mp4"
    assert FormatManager.get_extension("MP3 192kbps") == ".mp3"
    assert FormatManager.get_audio_quality("MP3 192kbps") == "192K"
    assert FormatManager.get_audio_quality("MP3 320kbps") == "320K"
    assert FormatManager.is_audio_only("WAV") is True
    assert FormatManager.is_audio_only("MP4 480p") is False
