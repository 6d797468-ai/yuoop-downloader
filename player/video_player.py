"""
Embedded preview player powered by yt-dlp and ffplay.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
import tkinter as tk
from io import BytesIO
from typing import Callable, Optional

import customtkinter as ctk
import requests
from PIL import Image, ImageTk

from utils.yt_dlp_runner import build_yt_dlp_command, is_yt_dlp_available


class VideoPlayer:
    """
    Lightweight embedded media preview.

    The player resolves a YouTube preview stream with yt-dlp and renders it with
    ffplay inside a Tk frame when the platform supports SDL_WINDOWID.
    """

    COLORS = {
        "bg": "#0f1115",
        "panel": "#171a20",
        "button": "#252a32",
        "button_hover": "#303641",
        "accent": "#2fb8a6",
        "accent_hover": "#269b8d",
        "text": "#f4f6f8",
        "muted": "#8a93a2",
    }

    PREVIEW_FORMAT = (
        "best[protocol^=m3u8]/"
        "best[height<=720][vcodec!=none][acodec!=none]/"
        "best[vcodec!=none][acodec!=none]/best"
    )

    def __init__(
        self,
        parent_frame,
        height: int = 180,
        status_callback: Optional[Callable[[str], None]] = None,
        **kwargs,
    ):
        self.parent_frame = parent_frame
        self.height = height
        self.status_callback = status_callback

        self.source_url: Optional[str] = None
        self.thumbnail_url: Optional[str] = None
        self.stream_url: Optional[str] = None
        self.duration = 0
        self.position = 0.0
        self.started_at = 0.0
        self.is_playing = False
        self.is_paused = False
        self.is_resolving = False
        self.process: Optional[subprocess.Popen] = None
        self.fullscreen_window: Optional[tk.Toplevel] = None
        self.fullscreen_surface: Optional[tk.Frame] = None
        self.thumbnail_image = None
        self._tick_job = None
        self._seek_job = None

        self._build_ui()

    def _build_ui(self) -> None:
        """Build video surface and compact controls."""
        self.container = ctk.CTkFrame(self.parent_frame, fg_color="transparent")
        self.container.pack(fill="both", expand=True)
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(0, weight=1)

        self.surface = tk.Frame(self.container, bg=self.COLORS["bg"], height=self.height)
        self.surface.grid(row=0, column=0, sticky="nsew")
        self.surface.grid_propagate(False)

        self.placeholder = tk.Label(
            self.surface,
            text="No video selected",
            bg=self.COLORS["bg"],
            fg=self.COLORS["muted"],
            font=("Segoe UI", 12),
        )
        self.placeholder.place(relx=0.5, rely=0.5, anchor="center")

        controls = ctk.CTkFrame(self.container, fg_color=self.COLORS["panel"], corner_radius=0)
        controls.grid(row=1, column=0, sticky="ew")
        controls.grid_columnconfigure(1, weight=1)

        self.play_btn = ctk.CTkButton(
            controls,
            text="Play",
            command=self.toggle_play,
            width=64,
            height=28,
            fg_color=self.COLORS["accent"],
            hover_color=self.COLORS["accent_hover"],
        )
        self.play_btn.grid(row=0, column=0, padx=(8, 6), pady=7)

        self.seek_slider = ctk.CTkSlider(
            controls,
            from_=0,
            to=1,
            command=self._on_seek_changed,
            progress_color=self.COLORS["accent"],
            button_color=self.COLORS["accent"],
            button_hover_color=self.COLORS["accent_hover"],
            fg_color="#2a2f37",
        )
        self.seek_slider.grid(row=0, column=1, sticky="ew", padx=6)
        self.seek_slider.set(0)

        self.time_label = ctk.CTkLabel(
            controls,
            text="00:00 / 00:00",
            width=90,
            font=("Segoe UI", 10),
            text_color=self.COLORS["muted"],
        )
        self.time_label.grid(row=0, column=2, padx=6)

        self.fullscreen_btn = ctk.CTkButton(
            controls,
            text="Full",
            command=self.enter_fullscreen,
            width=58,
            height=28,
            fg_color=self.COLORS["button"],
            hover_color=self.COLORS["button_hover"],
        )
        self.fullscreen_btn.grid(row=0, column=3, padx=(6, 8), pady=7)

        self.quality_label = ctk.CTkLabel(
            self.container,
            text="Quality: Auto",
            font=("Segoe UI", 9),
            text_color=self.COLORS["muted"],
            anchor="w",
        )
        self.quality_label.grid(row=2, column=0, sticky="ew", padx=8, pady=(4, 0))

    def load_video(self, source_url: str, thumbnail_url: str = "", duration: int = 0) -> None:
        """Load a video for preview without starting playback."""
        self.stop()
        self.source_url = source_url
        self.thumbnail_url = thumbnail_url
        self.stream_url = None
        self.duration = max(0, int(duration or 0))
        self.position = 0.0
        self.seek_slider.configure(to=max(self.duration, 1))
        self.seek_slider.set(0)
        self._update_time_label()
        self.play_btn.configure(text="Play")
        self._set_status("Preview ready")

        if thumbnail_url:
            self.load_thumbnail(thumbnail_url)
        else:
            self._show_placeholder("Ready to preview")

    def load_thumbnail(self, thumbnail_url: str) -> bool:
        """Load and display thumbnail image."""
        if not thumbnail_url:
            self._show_placeholder("No thumbnail available")
            return False

        def _load() -> None:
            try:
                response = requests.get(thumbnail_url, timeout=5)
                response.raise_for_status()
                with Image.open(BytesIO(response.content)) as raw_img:
                    image = raw_img.convert("RGB")
                image.thumbnail((520, self.height), Image.Resampling.LANCZOS)
                self._run_on_ui(self._display_thumbnail, image)
            except Exception:
                self._run_on_ui(self._show_placeholder, "Thumbnail unavailable")

        threading.Thread(target=_load, daemon=True).start()
        return True

    def toggle_play(self) -> None:
        """Play, pause, or resume preview playback."""
        if not self.source_url:
            self._show_placeholder("Select a video first")
            return

        if self.is_resolving:
            return

        if self.process and self.process.poll() is None:
            if self.is_paused:
                self._resume_process()
            else:
                self._pause_process()
            return

        if not self.stream_url:
            self._resolve_stream_async(start_after=True)
            return

        self._start_process(self.position)

    def enter_fullscreen(self) -> None:
        """Open preview in a fullscreen Tk window."""
        if not self.source_url:
            self._show_placeholder("Select a video first")
            return

        if not self.stream_url:
            self._resolve_stream_async(start_after=False, fullscreen_after=True)
            return

        self._open_fullscreen_window()

    def stop(self) -> None:
        """Stop playback and reset process state."""
        self._terminate_process()
        self.is_playing = False
        self.is_paused = False
        self.play_btn.configure(text="Play")
        if self._tick_job:
            try:
                self.parent_frame.after_cancel(self._tick_job)
            except Exception:
                pass
            self._tick_job = None

    def clear(self, message: str = "No video selected") -> None:
        """Stop playback and reset the preview surface."""
        self.stop()
        self.source_url = None
        self.thumbnail_url = None
        self.stream_url = None
        self.duration = 0
        self.position = 0.0
        self.seek_slider.configure(to=1)
        self.seek_slider.set(0)
        self._update_time_label()
        if self.fullscreen_window and self.fullscreen_window.winfo_exists():
            self.fullscreen_window.destroy()
        self.fullscreen_window = None
        self.fullscreen_surface = None
        self._show_placeholder(message)

    def _resolve_stream_async(self, start_after: bool = False, fullscreen_after: bool = False) -> None:
        """Resolve direct media URL in a worker thread."""
        if self.is_resolving or not self.source_url:
            return

        self.is_resolving = True
        self.play_btn.configure(text="Loading")
        self._show_placeholder("Preparing preview...")
        self._set_status("Preparing preview stream")

        def _resolve() -> None:
            stream_url, error = self._resolve_stream_url(self.source_url)
            self._run_on_ui(self._on_stream_resolved, stream_url, error, start_after, fullscreen_after)

        threading.Thread(target=_resolve, daemon=True).start()

    def _resolve_stream_url(self, source_url: str) -> tuple[Optional[str], Optional[str]]:
        """Resolve preview stream URL with yt-dlp."""
        if not is_yt_dlp_available():
            return None, "yt-dlp not found"
        if not self._ffplay_executable():
            return None, "ffplay not found. Install FFmpeg with ffplay."

        cmd = build_yt_dlp_command(
            "-g",
            "-f",
            self.PREVIEW_FORMAT,
            "--no-warnings",
            "--no-playlist",
            source_url,
        )

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
        except subprocess.TimeoutExpired:
            return None, "Preview stream timed out"
        except Exception as e:
            return None, str(e)

        if result.returncode != 0:
            return None, (result.stderr.strip() or "Could not prepare preview")[:220]

        urls = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        if not urls:
            return None, "No preview stream found"

        return urls[0], None

    def _on_stream_resolved(
        self,
        stream_url: Optional[str],
        error: Optional[str],
        start_after: bool,
        fullscreen_after: bool,
    ) -> None:
        """Handle resolved stream URL on UI thread."""
        self.is_resolving = False
        if error or not stream_url:
            self.play_btn.configure(text="Play")
            self._show_placeholder(error or "Preview unavailable")
            self._set_status(error or "Preview unavailable")
            return

        self.stream_url = stream_url
        self._set_status("Preview stream ready")
        self.play_btn.configure(text="Play")

        if fullscreen_after:
            self._open_fullscreen_window()
        elif start_after:
            self._start_process(self.position)

    def _start_process(self, position: float = 0.0, surface: Optional[tk.Frame] = None) -> None:
        """Start ffplay in the given Tk surface."""
        if not self.stream_url:
            return

        self._terminate_process()
        target = surface or self.surface
        target.update_idletasks()

        env = os.environ.copy()
        env["SDL_WINDOWID"] = str(target.winfo_id())

        cmd = [
            self._ffplay_executable() or "ffplay",
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostats",
            "-autoexit",
            "-noborder",
        ]
        if position > 0:
            cmd.extend(["-ss", str(int(position))])
        cmd.extend(["-i", self.stream_url])

        try:
            self.placeholder.place_forget()
            self.process = subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            self._show_placeholder(f"Preview failed: {e}")
            self._set_status(f"Preview failed: {e}")
            return

        self.position = float(position)
        self.started_at = time.monotonic()
        self.is_playing = True
        self.is_paused = False
        self.play_btn.configure(text="Pause")
        self._set_status("Playing preview")
        self._schedule_tick()

    def _pause_process(self) -> None:
        """Pause active process."""
        if not self.process or self.process.poll() is not None:
            return

        self.position = self._current_position()
        if os.name != "nt":
            self.process.send_signal(signal.SIGSTOP)
            self.is_paused = True
            self.is_playing = False
            self.play_btn.configure(text="Play")
            self._set_status("Preview paused")
        else:
            self._terminate_process()
            self.is_paused = True
            self.is_playing = False
            self.play_btn.configure(text="Play")

    def _resume_process(self) -> None:
        """Resume paused process."""
        if self.process and self.process.poll() is None and os.name != "nt":
            self.process.send_signal(signal.SIGCONT)
            self.started_at = time.monotonic()
            self.is_paused = False
            self.is_playing = True
            self.play_btn.configure(text="Pause")
            self._set_status("Playing preview")
            self._schedule_tick()
            return

        self._start_process(self.position)

    def _terminate_process(self) -> None:
        """Terminate ffplay if running."""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=2)
        self.process = None

    def _on_seek_changed(self, value: float) -> None:
        """Handle slider changes with a small debounce."""
        self.position = float(value)
        self._update_time_label()

        if self._seek_job:
            try:
                self.parent_frame.after_cancel(self._seek_job)
            except Exception:
                pass

        if self.stream_url and (self.is_playing or self.is_paused):
            self._seek_job = self.parent_frame.after(350, lambda: self._seek_to(self.position))

    def _seek_to(self, position: float) -> None:
        """Seek by restarting ffplay at a new timestamp."""
        self.position = max(0.0, float(position))
        if self.is_paused:
            return
        self._start_process(self.position)

    def _current_position(self) -> float:
        """Return estimated current playback position."""
        if self.is_playing:
            current = self.position + (time.monotonic() - self.started_at)
            if self.duration:
                return min(current, float(self.duration))
            return current
        return self.position

    def _schedule_tick(self) -> None:
        """Schedule UI progress updates."""
        if self._tick_job:
            try:
                self.parent_frame.after_cancel(self._tick_job)
            except Exception:
                pass
        self._tick_job = self.parent_frame.after(500, self._tick)

    def _tick(self) -> None:
        """Update seek bar and detect playback end."""
        if self.process and self.process.poll() is not None:
            self.is_playing = False
            self.play_btn.configure(text="Play")
            self._set_status("Preview ended")
            return

        if self.is_playing:
            current = self._current_position()
            self.seek_slider.set(current)
            self._update_time_label(current)
            self._schedule_tick()

    def _update_time_label(self, position: Optional[float] = None) -> None:
        """Update time display."""
        pos = self.position if position is None else position
        self.time_label.configure(text=f"{self._format_time(pos)} / {self._format_time(self.duration)}")

    def _format_time(self, seconds: float | int) -> str:
        """Format seconds as MM:SS or HH:MM:SS."""
        seconds = int(seconds or 0)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        if hours:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    def _open_fullscreen_window(self) -> None:
        """Open an embedded fullscreen player."""
        if self.fullscreen_window and self.fullscreen_window.winfo_exists():
            self.fullscreen_window.focus_force()
            return

        position = self._current_position()
        was_playing = self.is_playing
        self._terminate_process()

        win = tk.Toplevel(self.parent_frame)
        win.configure(bg="black")
        win.attributes("-fullscreen", True)
        win.title("Yuoop Preview")
        win.bind("<Escape>", lambda _event, playing=was_playing: self._close_fullscreen(was_playing=playing))

        surface = tk.Frame(win, bg="black")
        surface.pack(fill="both", expand=True)
        hint = tk.Label(win, text="Esc to exit fullscreen", bg="black", fg="#d8dee9", font=("Segoe UI", 11))
        hint.pack(fill="x", pady=6)

        self.fullscreen_window = win
        self.fullscreen_surface = surface
        win.update_idletasks()
        self._start_process(position, surface=surface)
        if not was_playing:
            self._pause_process()

    def _close_fullscreen(self, was_playing: bool = True) -> None:
        """Close fullscreen and restore embedded player."""
        position = self._current_position()
        self._terminate_process()

        if self.fullscreen_window and self.fullscreen_window.winfo_exists():
            self.fullscreen_window.destroy()
        self.fullscreen_window = None
        self.fullscreen_surface = None

        self.position = position
        if was_playing:
            self._start_process(position)
        else:
            self.load_thumbnail(self.thumbnail_url or "")

    def _display_thumbnail(self, image: Image.Image) -> None:
        """Display thumbnail in video surface."""
        self.surface.update_idletasks()
        photo = ImageTk.PhotoImage(image)
        self.thumbnail_image = photo
        self.placeholder.configure(image=photo, text="")
        self.placeholder.image = photo
        self.placeholder.place(relx=0.5, rely=0.5, anchor="center")

    def _show_placeholder(self, text: str) -> None:
        """Show placeholder text."""
        self.placeholder.configure(text=text, image="")
        self.placeholder.image = None
        self.placeholder.place(relx=0.5, rely=0.5, anchor="center")

    def _run_on_ui(self, callback, *args) -> None:
        """Run callback on Tk thread."""
        try:
            self.parent_frame.after(0, callback, *args)
        except Exception:
            pass

    def _set_status(self, message: str) -> None:
        """Send player status to app."""
        if self.status_callback:
            self.status_callback(message)

    def _ffplay_executable(self) -> Optional[str]:
        """Find ffplay on PATH or next to the current executable."""
        from shutil import which

        executable = which("ffplay")
        if executable:
            return executable

        executable_dir = os.path.dirname(sys.executable)
        candidates = ["ffplay.exe", "ffplay"] if os.name == "nt" else ["ffplay", "ffplay.exe"]
        for name in candidates:
            candidate = os.path.join(executable_dir, name)
            if os.path.isfile(candidate):
                return candidate
        return None
