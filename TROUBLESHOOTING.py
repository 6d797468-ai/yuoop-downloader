"""
Troubleshooting guide and common issues for Yuoop downloader.
"""

COMMON_ISSUES = {
    "timeout_error": {
        "description": "Timeout when analyzing playlist",
        "causes": [
            "Large playlist (1000+ videos)",
            "Slow internet connection",
            "YouTube rate limiting",
            "Invalid URL"
        ],
        "solutions": [
            "Wait longer - analysis can take 1-2 minutes",
            "Check your internet connection",
            "Try a smaller playlist first",
            "Verify the URL is correct and accessible",
            "Wait a few minutes before trying again if rate limited"
        ]
    },
    
    "yt_dlp_not_found": {
        "description": "yt-dlp command not found",
        "causes": [
            "yt-dlp not installed",
            "Virtual environment not activated"
        ],
        "solutions": [
            "Install: pip install yt-dlp",
            "Activate virtual environment: source venv/bin/activate",
            "Or use: python -m yt_dlp to test"
        ]
    },
    
    "ffmpeg_missing": {
        "description": "FFmpeg not found when downloading audio",
        "causes": [
            "FFmpeg not installed",
            "FFmpeg not in PATH"
        ],
        "solutions": [
            "Download from https://ffmpeg.org/download.html",
            "Windows: Add to PATH or put ffmpeg.exe in app directory",
            "Linux: sudo apt-get install ffmpeg",
            "macOS: brew install ffmpeg"
        ]
    },
    
    "ui_freezes": {
        "description": "Application UI freezes during operations",
        "causes": [
            "Long operation not in background thread",
            "Too many videos in list",
            "Slow computer"
        ],
        "solutions": [
            "Close other applications",
            "Try with a smaller playlist",
            "Restart the application",
            "Increase RAM if available"
        ]
    },
    
    "downloads_fail": {
        "description": "Downloads fail with no clear error",
        "causes": [
            "Video restricted in your region",
            "Video was deleted",
            "Age-restricted content",
            "Network disconnected"
        ],
        "solutions": [
            "Check if video is accessible in your browser",
            "Verify internet connection",
            "Try a different video",
            "Check application logs in yuoop.log"
        ]
    },
    
    "slow_performance": {
        "description": "Application or downloads are very slow",
        "causes": [
            "Slow internet connection",
            "Many parallel downloads",
            "System resources exhausted",
            "YouTube rate limiting"
        ],
        "solutions": [
            "Reduce parallel downloads (config file)",
            "Download smaller playlists",
            "Close other bandwidth-consuming apps",
            "Wait before trying again (rate limiting)"
        ]
    }
}


def print_troubleshooting():
    """Print troubleshooting guide."""
    print("=" * 70)
    print("YUOOP TROUBLESHOOTING GUIDE")
    print("=" * 70)
    print()
    
    for issue_key, issue_data in COMMON_ISSUES.items():
        print(f"ISSUE: {issue_data['description'].upper()}")
        print("-" * 70)
        
        print("\nPossible Causes:")
        for i, cause in enumerate(issue_data['causes'], 1):
            print(f"  {i}. {cause}")
        
        print("\nSolutions:")
        for i, solution in enumerate(issue_data['solutions'], 1):
            print(f"  {i}. {solution}")
        
        print()


def get_issue_help(keyword: str) -> str:
    """Get help for a specific issue."""
    keyword = keyword.lower()
    
    for issue_key, issue_data in COMMON_ISSUES.items():
        if keyword in issue_key.lower() or keyword in issue_data['description'].lower():
            help_text = f"ISSUE: {issue_data['description']}\n\n"
            help_text += "Solutions:\n"
            for i, solution in enumerate(issue_data['solutions'], 1):
                help_text += f"  {i}. {solution}\n"
            return help_text
    
    return "No help found for that issue. Try one of these:\n" + \
           ", ".join(COMMON_ISSUES.keys())


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        keyword = " ".join(sys.argv[1:])
        print(get_issue_help(keyword))
    else:
        print_troubleshooting()
