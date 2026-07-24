from utils.validators import is_valid_youtube_url, sanitize_filename


def test_youtube_url_detection():
    cases = [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", True, "video"),
        ("https://youtu.be/dQw4w9WgXcQ", True, "video"),
        ("https://www.youtube.com/playlist?list=PL123456789", True, "playlist"),
        ("https://www.youtube.com/@OpenAI", True, "channel"),
        ("https://example.com/watch?v=dQw4w9WgXcQ", False, None),
    ]

    for url, expected_valid, expected_type in cases:
        valid, url_type = is_valid_youtube_url(url)
        assert valid is expected_valid
        assert url_type == expected_type


def test_sanitize_filename_removes_unsafe_characters():
    assert sanitize_filename('bad:file/name*test?') == "bad_file_name_test_"
    assert len(sanitize_filename("a" * 300)) == 200
