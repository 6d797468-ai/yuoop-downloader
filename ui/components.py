"""
Reusable UI components for the application.
Modern dark theme design with improved UX.
"""

from __future__ import annotations

import customtkinter as ctk
from typing import Callable, Optional
from PIL import Image
import threading
import logging

Image.init()

from utils.thumbnail_cache import ThumbnailCache


class VideoCard(ctk.CTkFrame):
    """
    Widget representing a single video in the playlist.
    Contains checkbox, thumbnail, title, duration, and status.
    Modern design with hover effects and smooth transitions.
    """
    
    COLORS = {
        "bg": "#17181d",
        "bg_hover": "#20232a",
        "text_primary": "#f4f6f8",
        "text_secondary": "#a6adb8",
        "text_muted": "#76808f",
        "border": "#2a2f37",
        "selected": "#2fb8a6",
        "success": "#2fb86f",
        "danger": "#e25555",
        "warning": "#d8a13a",
    }
    
    FONTS = {
        "title": ("Segoe UI", 12, "bold"),
        "meta": ("Segoe UI", 10),
        "status": ("Segoe UI", 10, "bold"),
    }
    
    _thumbnail_cache: Optional[ThumbnailCache] = None
    
    def __init__(
        self,
        parent,
        video_id: str,
        title: str,
        duration: str,
        thumbnail_url: str,
        subtitle: str = "",
        load_thumbnail: bool = True,
        on_select: Optional[Callable[[str, bool], None]] = None,
        on_double_click: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        """
        Initialize video card.
        
        Args:
            parent: Parent widget
            video_id: Unique video ID
            title: Video title
            duration: Duration string (e.g., "12:34")
            thumbnail_url: URL to thumbnail image
            on_select: Callback when checkbox toggled (video_id, is_selected)
            on_double_click: Callback for double-click (video_id)
        """
        super().__init__(parent, **kwargs)
        
        self.video_id = video_id
        self.title = title
        self.duration = duration
        self.thumbnail_url = thumbnail_url
        self.subtitle = subtitle
        self.load_thumbnail = load_thumbnail
        self.on_select = on_select
        self.on_double_click = on_double_click
        self.is_selected = ctk.BooleanVar(value=False)
        self.thumbnail_image = None
        self.thumbnail_pil_image: Optional[Image.Image] = None
        self.logger = logging.getLogger(__name__)
        
        if VideoCard._thumbnail_cache is None:
            VideoCard._thumbnail_cache = ThumbnailCache()
        
        self._build_ui()
        if self.load_thumbnail and self.thumbnail_url:
            self._load_thumbnail_async()
        
    def _build_ui(self) -> None:
        """Build the video card UI."""
        self.configure(corner_radius=8, border_width=1, border_color=self.COLORS["border"])
        self.grid_columnconfigure(2, weight=1)
        
        self.checkbox = ctk.CTkCheckBox(
            self,
            text="",
            variable=self.is_selected,
            command=self._on_checkbox_toggled,
            width=30,
            fg_color=self.COLORS["selected"],
            hover_color="#269b8d",
            border_color=self.COLORS["border"],
        )
        self.checkbox.grid(row=0, column=0, padx=(10, 6), pady=8)
        
        self.thumbnail_label = ctk.CTkLabel(
            self,
            text="Video",
            font=self.FONTS["meta"],
            text_color=self.COLORS["text_secondary"],
            width=88,
            height=50,
            fg_color=self.COLORS["border"],
            corner_radius=6,
        )
        self.thumbnail_label.grid(row=0, column=1, padx=(0, 10), pady=8)
        self.thumbnail_label.bind("<Button-1>", self._on_preview_handler)
        
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.grid(row=0, column=2, padx=0, pady=8, sticky="ew")
        info_frame.grid_columnconfigure(0, weight=1)
        
        self.title_label = ctk.CTkLabel(
            info_frame,
            text=self.title,
            font=self.FONTS["title"],
            text_color=self.COLORS["text_primary"],
            anchor="w",
            wraplength=520,
        )
        self.title_label.grid(row=0, column=0, sticky="ew")

        meta_text = self.duration
        if self.subtitle:
            meta_text = f"{self.duration}  |  {self.subtitle}" if self.duration else self.subtitle
        
        self.duration_label = ctk.CTkLabel(
            info_frame,
            text=meta_text,
            font=self.FONTS["meta"],
            text_color=self.COLORS["text_muted"],
            anchor="w",
        )
        self.duration_label.grid(row=1, column=0, sticky="w", pady=(3, 0))
        
        self.status_label = ctk.CTkLabel(
            self,
            text="Pending",
            font=self.FONTS["status"],
            text_color=self.COLORS["text_secondary"],
            fg_color="#242933",
            corner_radius=12,
            width=92,
            height=26,
        )
        self.status_label.grid(row=0, column=3, padx=(12, 10), pady=8)
        
        self.bind("<Button-1>", self._on_preview_handler)
        for widget in (self.thumbnail_label, info_frame, self.title_label, self.duration_label):
            widget.bind("<Button-1>", self._on_preview_handler)
        
    def _load_thumbnail_async(self) -> None:
        """Load thumbnail in background thread."""
        thread = threading.Thread(
            target=self._load_thumbnail,
            daemon=True
        )
        thread.start()
    
    def _load_thumbnail(self) -> None:
        """Load and display thumbnail image."""
        try:
            cache = VideoCard._thumbnail_cache
            pil_image = cache.fetch(self.thumbnail_url, size=(88, 50))
            
            if pil_image:
                self._update_thumbnail_safe(pil_image)
            else:
                self.logger.debug(f"Thumbnail fetch returned None for {self.thumbnail_url}")
        except Exception as e:
            self.logger.error(f"Error loading thumbnail for {self.title}: {e}")
    
    def _update_thumbnail_safe(self, pil_image: Image.Image) -> None:
        """Update thumbnail label thread-safely."""
        def update():
            try:
                if self.winfo_exists():
                    self.thumbnail_pil_image = pil_image
                    self.thumbnail_image = ctk.CTkImage(
                        light_image=pil_image,
                        dark_image=pil_image,
                        size=(88, 50)
                    )
                    self.thumbnail_label.configure(image=self.thumbnail_image, text="")
            except Exception as e:
                self.logger.error(f"Error updating thumbnail label: {e}")
        
        self.after(0, update)
    
    def set_status(self, status: str) -> None:
        """Update status label."""
        normalized = status.lower()
        color = "#242933"
        text_color = self.COLORS["text_secondary"]

        if "downloaded" in normalized or "complete" in normalized:
            color = "#163d2b"
            text_color = "#7fe3a2"
        elif "failed" in normalized:
            color = "#4b2024"
            text_color = "#ff9b9b"
        elif "canceled" in normalized:
            color = "#3c3447"
            text_color = "#c9b7e8"
        elif "%" in normalized or "queued" in normalized:
            color = "#173f3b"
            text_color = "#7bdacf"

        self.status_label.configure(text=status, fg_color=color, text_color=text_color)
    
    def is_checked(self) -> bool:
        """Check if video is selected."""
        return self.is_selected.get()
    
    def set_checked(self, checked: bool) -> None:
        """Set checkbox state."""
        self.is_selected.set(checked)
    
    def _on_checkbox_toggled(self) -> None:
        """Handle checkbox toggle."""
        if self.on_select:
            self.on_select(self.video_id, self.is_selected.get())
    
    def _on_preview_handler(self, event) -> None:
        """Handle preview request."""
        if self.on_double_click:
            self.on_double_click(self.video_id)


class ProgressBar(ctk.CTkFrame):
    """
    Custom progress bar with label and percentage.
    Modern design with smooth animation.
    """
    
    COLORS = {
        "bg": "#17181d",
        "text_primary": "#f4f6f8",
        "text_secondary": "#a6adb8",
        "accent": "#2fb8a6",
    }
    
    FONTS = {
        "small": ("Segoe UI", 11),
    }
    
    def __init__(self, parent, label: str = "", **kwargs):
        """
        Initialize progress bar.
        
        Args:
            parent: Parent widget
            label: Label text
        """
        super().__init__(parent, **kwargs)
        
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=0, pady=0)
        
        self.label = ctk.CTkLabel(
            header_frame,
            text=label,
            font=self.FONTS["small"],
            text_color=self.COLORS["text_primary"]
        )
        self.label.pack(side="left")
        
        self.percent_label = ctk.CTkLabel(
            header_frame,
            text="0%",
            font=self.FONTS["small"],
            text_color=self.COLORS["text_secondary"]
        )
        self.percent_label.pack(side="right")
        
        self.progress_bar = ctk.CTkProgressBar(
            self,
            height=10,
            progress_color=self.COLORS["accent"],
            fg_color="#252a32",
        )
        self.progress_bar.pack(fill="x", padx=0, pady=5)
        self.progress_bar.set(0)
        
        self.current_value = 0
        self.max_value = 100
    
    def set_progress(self, current: int, maximum: int = None) -> None:
        """
        Update progress.
        
        Args:
            current: Current value
            maximum: Maximum value (default: 100)
        """
        if maximum is not None:
            self.max_value = maximum
        
        self.current_value = current
        
        if self.max_value > 0:
            ratio = min(current / self.max_value, 1.0)
            percent = int(ratio * 100)
        else:
            ratio = 0
            percent = 0
        
        self.progress_bar.set(ratio)
        self.percent_label.configure(text=f"{percent}%")
    
    def set_label(self, label: str) -> None:
        """Update label text."""
        self.label.configure(text=label)


class LogConsole(ctk.CTkFrame):
    """
    Text console for displaying logs and status messages.
    Modern terminal-inspired design.
    """
    
    COLORS = {
        "bg": "#111318",
        "header": "#1a1d23",
        "text": "#d8dee9",
        "text_secondary": "#a6adb8",
        "button": "#252a32",
    }
    
    FONTS = {
        "header": ("Segoe UI", 12, "bold"),
        "text": ("Consolas", 10),
    }
    
    def __init__(self, parent, on_clear: Optional[Callable[[], None]] = None, **kwargs):
        """Initialize log console."""
        super().__init__(parent, **kwargs)
        self.on_clear = on_clear
        
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=(8, 0))

        header = ctk.CTkLabel(
            header_frame,
            text="Activity",
            font=self.FONTS["header"],
            text_color=self.COLORS["text"]
        )
        header.pack(side="left")

        clear_btn = ctk.CTkButton(
            header_frame,
            text="Clear",
            command=self.clear,
            width=64,
            height=24,
            fg_color=self.COLORS["button"],
            hover_color="#303641",
            font=("Segoe UI", 9),
        )
        clear_btn.pack(side="right")
        
        text_frame = ctk.CTkFrame(self, fg_color=self.COLORS["header"])
        text_frame.pack(fill="both", expand=True, padx=10, pady=8)
        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)
        
        self.text = ctk.CTkTextbox(
            text_frame,
            font=self.FONTS["text"],
            text_color=self.COLORS["text"],
            fg_color=self.COLORS["bg"],
        )
        self.text.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        self.text.configure(state="disabled")
    
    def append_message(self, message: str) -> None:
        """
        Append message to log.
        
        Args:
            message: Message to append
        """
        self.text.configure(state="normal")
        self.text.insert("end", message + "\n")
        self.text.see("end")
        self.text.configure(state="disabled")
    
    def clear(self) -> None:
        """Clear all log messages."""
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")
    
    def get_all_text(self) -> str:
        """Get all log text."""
        return self.text.get("1.0", "end-1c")
