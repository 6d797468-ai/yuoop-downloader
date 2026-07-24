import sys
import tempfile
import time
from pathlib import Path

from downloader.queue_manager import DownloadQueueManager, DownloadTask


def test_queue_manager_reports_progress_and_completion():
    progress = []
    completed = []

    manager = DownloadQueueManager(num_workers=1)
    manager._build_download_command = lambda task: [
        sys.executable,
        "-c",
        "print('[download] 25.0%', flush=True); print('[download] 100.0%', flush=True)",
    ]
    manager.start()
    manager.enqueue_task(
        DownloadTask(
            video_id="ok",
            title="ok",
            url="https://example.invalid",
            format_name="MP4 720p",
            output_path=Path(tempfile.gettempdir()),
            on_progress=lambda video_id, current, maximum: progress.append((video_id, current, maximum)),
            on_complete=lambda video_id, success, error: completed.append((video_id, success, error)),
        )
    )

    for _ in range(30):
        if completed:
            break
        time.sleep(0.1)

    manager.stop()

    assert ("ok", 25, 100) in progress
    assert completed == [("ok", True, None)]


def test_queue_manager_stop_cancels_active_process():
    completed = []

    manager = DownloadQueueManager(num_workers=1)
    manager._build_download_command = lambda task: [
        sys.executable,
        "-c",
        "import time; print('[download] 5.0%', flush=True); time.sleep(20)",
    ]
    manager.start()
    manager.enqueue_task(
        DownloadTask(
            video_id="stop",
            title="stop",
            url="https://example.invalid",
            format_name="MP4 720p",
            output_path=Path(tempfile.gettempdir()),
            on_complete=lambda video_id, success, error: completed.append((video_id, success, error)),
        )
    )

    time.sleep(0.5)
    manager.stop()

    assert completed == [("stop", False, "Canceled")]
