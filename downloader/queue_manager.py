"""
Download queue manager with parallel workers.
Handles threading and download coordination.
"""

from __future__ import annotations

import threading
import queue
import subprocess
import time
import re
from collections import deque
from pathlib import Path
from typing import Callable, Optional, Dict
from dataclasses import dataclass

from downloader.formats import FormatManager
from utils.logger import get_logger
from utils.validators import sanitize_filename
from utils.yt_dlp_runner import build_yt_dlp_command


@dataclass
class DownloadTask:
    """A single download task."""
    video_id: str
    title: str
    url: str
    format_name: str
    output_path: Path
    on_progress: Optional[Callable[[str, int, int], None]] = None
    on_complete: Optional[Callable[[str, bool, Optional[str]], None]] = None
    
    def __hash__(self):
        return hash(self.video_id)


class DownloadQueueManager:
    """
    Manages a queue of download tasks with parallel workers.
    """
    
    def __init__(self, num_workers: int = 2):
        """
        Initialize download queue manager.
        
        Args:
            num_workers: Number of parallel download workers (2-3 recommended)
        """
        self.num_workers = max(1, min(num_workers, 4))  # Clamp to 1-4
        self.task_queue: queue.Queue[Optional[DownloadTask]] = queue.Queue()
        self.workers: list[threading.Thread] = []
        self.active_downloads: Dict[str, bool] = {}
        self.active_processes: Dict[str, subprocess.Popen] = {}
        self.running = False
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.logger = get_logger()
    
    def start(self) -> None:
        """Start the download worker threads."""
        if self.running:
            return
        
        self.running = True
        self.stop_event.clear()
        self.logger.info(f"Starting download manager with {self.num_workers} workers")
        
        for i in range(self.num_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"DownloadWorker-{i+1}",
                daemon=True
            )
            worker.start()
            self.workers.append(worker)
    
    def stop(self) -> None:
        """Stop all workers and clear queue."""
        if not self.running and not self.workers:
            return

        self.running = False
        self.stop_event.set()
        self.logger.info("Stopping download manager")

        self._terminate_active_processes()
        self._clear_pending_tasks()
        
        # Send stop signals to workers
        for _ in range(self.num_workers):
            self.task_queue.put(None)
        
        # Wait for workers to finish
        for worker in self.workers:
            worker.join(timeout=5)
        
        self.workers.clear()
        with self.lock:
            self.active_downloads.clear()
            self.active_processes.clear()
    
    def enqueue_task(self, task: DownloadTask) -> bool:
        """
        Enqueue a download task.
        
        Args:
            task: DownloadTask to add
            
        Returns:
            True if enqueued, False if queue full or not running
        """
        if not self.running:
            return False
        
        try:
            with self.lock:
                self.active_downloads[task.video_id] = True
            self.task_queue.put(task, timeout=2)
            return True
        except queue.Full:
            with self.lock:
                self.active_downloads.pop(task.video_id, None)
            self.logger.error(f"Download queue full, cannot add {task.title}")
            return False
    
    def enqueue_tasks(self, tasks: list[DownloadTask]) -> int:
        """
        Enqueue multiple tasks.
        
        Args:
            tasks: List of DownloadTask objects
            
        Returns:
            Number of tasks successfully enqueued
        """
        count = 0
        for task in tasks:
            if self.enqueue_task(task):
                count += 1
        return count
    
    def cancel_download(self, video_id: str) -> bool:
        """
        Cancel a specific download (if not already in progress).
        
        Args:
            video_id: Video ID to cancel
            
        Returns:
            True if cancelled, False if already downloading or not found
        """
        with self.lock:
            if video_id in self.active_downloads:
                del self.active_downloads[video_id]
                process = self.active_processes.pop(video_id, None)
                if process and process.poll() is None:
                    self._terminate_process(process)
                return True
        return False
    
    def is_active(self, video_id: str) -> bool:
        """Check if a video is actively downloading."""
        with self.lock:
            return self.active_downloads.get(video_id, False)
    
    def _worker_loop(self) -> None:
        """Main loop for download worker thread."""
        while True:
            try:
                # Get task from queue (timeout to allow checking running flag)
                task = self.task_queue.get(timeout=1)
                
                if task is None:  # Stop signal
                    self.task_queue.task_done()
                    break

                if self.stop_event.is_set():
                    self._notify_complete(task, False, "Canceled")
                    self.task_queue.task_done()
                    continue
                
                self._execute_download(task)
                self.task_queue.task_done()
                
            except queue.Empty:
                if not self.running:
                    break
                continue
            except Exception as e:
                self.logger.error(f"Worker error: {e}")
    
    def _execute_download(self, task: DownloadTask, retry_count: int = 0) -> None:
        """
        Execute a single download task with retry logic.
        
        Args:
            task: DownloadTask to execute
            retry_count: Current retry attempt number
        """
        max_retries = 3
        
        try:
            if not self.is_active(task.video_id) or self.stop_event.is_set():
                return
            
            self.logger.info(f"Starting download: {task.title}")

            cmd = self._build_download_command(task)
            attempt = retry_count

            while attempt <= max_retries and not self.stop_event.is_set():
                success, error_msg = self._run_download_process(task, cmd)

                if success:
                    self.logger.success(f"Downloaded: {task.title}")
                    self._notify_complete(task, True, None)
                    return

                if error_msg == "Canceled" or self.stop_event.is_set():
                    self.logger.warning(f"Canceled: {task.title}")
                    self._notify_complete(task, False, "Canceled")
                    return

                self.logger.error(f"Failed to download {task.title}: {error_msg}")

                if attempt < max_retries:
                    delay = (2 ** attempt) * 1.5
                    self.logger.warning(
                        f"Retrying {task.title} in {delay:.1f}s (attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(delay)
                    attempt += 1
                    continue

                self._notify_complete(task, False, error_msg)
                return

        except Exception as e:
            self.logger.error(f"Error downloading {task.title}: {str(e)}")
            self._notify_complete(task, False, str(e))
        finally:
            with self.lock:
                self.active_downloads.pop(task.video_id, None)
                self.active_processes.pop(task.video_id, None)

    def _build_download_command(self, task: DownloadTask) -> list[str]:
        """Build yt-dlp command for a task."""
        sanitized_title = sanitize_filename(task.title)
        output_template = str(task.output_path / f"{sanitized_title}.%(ext)s")
        format_string = FormatManager.get_format_string(task.format_name)

        cmd = build_yt_dlp_command(
            "-f", format_string,
            "-o", output_template,
            "--no-warnings",
            "--newline",
        )

        if FormatManager.is_audio_only(task.format_name):
            audio_format = FormatManager.get_audio_format(task.format_name)
            cmd.extend(["-x", "--audio-format", audio_format])
            if audio_format == 'mp3':
                cmd.extend(["--audio-quality", FormatManager.get_audio_quality(task.format_name)])
        else:
            cmd.extend(["--merge-output-format", "mp4"])

        cmd.append(task.url)
        return cmd

    def _run_download_process(self, task: DownloadTask, cmd: list[str]) -> tuple[bool, str | None]:
        """Run yt-dlp and stream progress from its output."""
        recent_lines: deque[str] = deque(maxlen=12)

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
        except FileNotFoundError:
            return False, "yt-dlp not found. Please install: pip install yt-dlp"

        with self.lock:
            self.active_processes[task.video_id] = process

        self._notify_progress(task, 0, 100)

        try:
            assert process.stdout is not None
            for line in process.stdout:
                if self.stop_event.is_set() or not self.is_active(task.video_id):
                    self._terminate_process(process)
                    return False, "Canceled"

                clean_line = line.strip()
                if not clean_line:
                    continue

                recent_lines.append(clean_line)
                self._handle_progress_line(task, clean_line)

            return_code = process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self._terminate_process(process)
            return False, "Timeout"
        finally:
            with self.lock:
                self.active_processes.pop(task.video_id, None)

        if self.stop_event.is_set():
            return False, "Canceled"

        if return_code == 0:
            self._notify_progress(task, 100, 100)
            return True, None

        return False, self._summarize_error(recent_lines)

    def _handle_progress_line(self, task: DownloadTask, line: str) -> None:
        """Parse yt-dlp progress lines and notify the task."""
        match = re.search(r"\[download\]\s+(\d+(?:\.\d+)?)%", line)
        if match:
            percent = int(float(match.group(1)))
            self._notify_progress(task, percent, 100)

    def _summarize_error(self, lines: deque[str]) -> str:
        """Extract a compact error message from yt-dlp output."""
        if not lines:
            return "Unknown error"

        error_lines = [
            line for line in lines
            if "error" in line.lower() or "failed" in line.lower()
        ]
        selected = error_lines[-3:] if error_lines else list(lines)[-3:]
        return " | ".join(selected)[:500]

    def _notify_progress(self, task: DownloadTask, current: int, maximum: int) -> None:
        """Send progress to task callback."""
        if task.on_progress:
            task.on_progress(task.video_id, current, maximum)

    def _notify_complete(self, task: DownloadTask, success: bool, error_msg: Optional[str]) -> None:
        """Send completion to task callback."""
        if task.on_complete:
            task.on_complete(task.video_id, success, error_msg)

    def _clear_pending_tasks(self) -> None:
        """Drain queued tasks that have not started yet."""
        while True:
            try:
                task = self.task_queue.get_nowait()
            except queue.Empty:
                break

            if task is not None:
                self._notify_complete(task, False, "Canceled")
            self.task_queue.task_done()

    def _terminate_active_processes(self) -> None:
        """Terminate every active yt-dlp process."""
        with self.lock:
            processes = list(self.active_processes.values())

        for process in processes:
            self._terminate_process(process)

    @staticmethod
    def _terminate_process(process: subprocess.Popen) -> None:
        """Terminate a subprocess, killing it if it refuses to exit."""
        if process.poll() is not None:
            return

        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
