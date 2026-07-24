"""
Main application window and orchestration.
Modern dark theme design with improved UX.
"""

from __future__ import annotations

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import sys
import subprocess
import threading
from pathlib import Path
from typing import Optional, Dict, List

from config.settings import get_config
from downloader.youtube import YouTubePlaylistExtractor, VideoInfo
from downloader.formats import FormatManager
from downloader.queue_manager import DownloadQueueManager, DownloadTask
from ui.components import VideoCard, ProgressBar
from utils.validators import is_valid_youtube_url
from utils.logger import get_logger
from player.video_player import VideoPlayer


class YuoopApp(ctk.CTk):
    """Main application window with modern dark theme."""

    QUEUE_PAGE_SIZE = 16
    QUEUE_RENDER_BATCH_SIZE = 4
    
    COLORS = {
        "bg_primary": "#0f1115",
        "bg_secondary": "#171a20",
        "bg_panel": "#1d2128",
        "bg_card": "#15181d",
        "bg_accent": "#252a32",
        "border": "#2d333d",
        "accent": "#2fb8a6",
        "accent_hover": "#269b8d",
        "danger": "#d94f4f",
        "danger_hover": "#bd4141",
        "text_primary": "#f4f6f8",
        "text_secondary": "#a6adb8",
        "text_muted": "#747f8d",
        "success": "#2fb86f",
        "warning": "#d8a13a",
    }
    
    FONTS = {
        "title": ("Segoe UI", 22, "bold"),
        "heading": ("Segoe UI", 14, "bold"),
        "body": ("Segoe UI", 11),
        "small": ("Segoe UI", 10),
        "tiny": ("Segoe UI", 9),
    }
    
    def __init__(self):
        """Initialize the application."""
        super().__init__()
        
        self.config_manager = get_config()
        self.logger = get_logger()
        
        self._setup_window()
        self._setup_state()
        self._build_ui()
        self._register_callbacks()
        
    def _setup_window(self) -> None:
        """Configure main window appearance."""
        self.title("Yuoop - YouTube Downloader")
        width = self.config_manager.get("ui.window_width", 1200)
        height = self.config_manager.get("ui.window_height", 800)
        self.geometry(f"{width}x{height}")
        self.minsize(1040, 680)
        
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.configure(fg_color=self.COLORS["bg_primary"])
        self._set_window_icon()

    def _set_window_icon(self) -> None:
        """Set application icon when bundled assets are available."""
        base_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
        assets_dir = base_dir / "assets"
        icon_ico = assets_dir / "icon.ico"
        icon_png = assets_dir / "icon.png"

        try:
            if icon_ico.exists():
                self.iconbitmap(str(icon_ico))
        except Exception:
            pass

        try:
            if icon_png.exists():
                self._window_icon = tk.PhotoImage(file=str(icon_png))
                self.iconphoto(True, self._window_icon)
        except Exception:
            pass
    
    def _setup_state(self) -> None:
        """Initialize application state."""
        self.videos: Dict[str, VideoInfo] = {}
        self.video_order: List[str] = []
        self.video_cards: Dict[str, VideoCard] = {}
        self.video_status: Dict[str, str] = {}
        self.selected_videos: set = set()
        self.download_progress: Dict[str, int] = {}
        self.download_total = 0
        self.download_completed = 0
        self.is_downloading = False
        self.download_cancel_requested = False
        self.current_preview_video_id: Optional[str] = None
        self.rendered_video_count = 0
        self.queue_load_more_btn: Optional[ctk.CTkButton] = None
        self.queue_render_job: Optional[str] = None
        self.queue_render_generation = 0
        self.download_manager = DownloadQueueManager(
            self.config_manager.get("download.parallel_workers", 2)
        )
        self.download_manager.start()
        self.ffmpeg_available = self.config_manager.detect_ffmpeg()
        self.ffplay_available = self.config_manager.detect_ffplay()
        self._pil_initialized = False
        
        self._init_pil()
        
        if not self.ffmpeg_available:
            self.logger.warning("FFmpeg not found - audio formats disabled")
        if not self.ffplay_available:
            self.logger.warning("ffplay not found - embedded preview playback disabled")
    
    def _init_pil(self) -> None:
        """Initialize PIL plugins early to prevent DEBUG spam."""
        if self._pil_initialized:
            return
        from PIL import Image
        Image.init()
        self._pil_initialized = True
    
    def _build_ui(self) -> None:
        """Build the modern UI layout."""
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self._build_header()
        self._build_main_content()
        self._build_status_bar()
        self._display_empty_state("Paste a YouTube source above to fill the queue.")
        
        self.logger.info("Application started")
        
    def _build_header(self) -> None:
        """Build the header with URL input."""
        header = ctk.CTkFrame(self, height=128, fg_color=self.COLORS["bg_secondary"], corner_radius=0)
        header.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        header.grid_propagate(False)
        header.grid_columnconfigure(0, weight=1)
        
        inner = ctk.CTkFrame(header, fg_color="transparent")
        inner.grid(row=0, column=0, padx=22, pady=12, sticky="ew")
        inner.grid_columnconfigure(0, weight=1)
        
        top_row = ctk.CTkFrame(inner, fg_color="transparent")
        top_row.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        top_row.grid_columnconfigure(0, weight=1)

        title_group = ctk.CTkFrame(top_row, fg_color="transparent")
        title_group.grid(row=0, column=0, sticky="w")

        title = ctk.CTkLabel(
            title_group,
            text="Yuoop",
            font=self.FONTS["title"],
            text_color=self.COLORS["text_primary"]
        )
        title.pack(anchor="w")

        ctk.CTkLabel(
            title_group,
            text="Simple preview-first downloads, crafted with care",
            font=self.FONTS["small"],
            text_color=self.COLORS["text_secondary"]
        ).pack(anchor="w", pady=(2, 0))

        system_status_text, system_status_color, system_status_bg = self._media_status_style()
        self.system_status_label = ctk.CTkLabel(
            top_row,
            text=system_status_text,
            font=("Segoe UI", 10, "bold"),
            text_color=system_status_color,
            fg_color=system_status_bg,
            corner_radius=12,
            width=118,
            height=26,
        )
        self.system_status_label.grid(row=0, column=1, sticky="e")

        input_row = ctk.CTkFrame(inner, fg_color="transparent")
        input_row.grid(row=1, column=0, sticky="ew")
        input_row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            input_row,
            text="Source",
            font=self.FONTS["small"],
            text_color=self.COLORS["text_secondary"]
        ).grid(row=0, column=0, padx=(0, 10))
        
        self.url_entry = ctk.CTkEntry(
            input_row,
            placeholder_text="Paste YouTube playlist, mix, or channel URL...",
            font=self.FONTS["body"],
            height=38,
            fg_color="#101217",
            border_color=self.COLORS["border"],
        )
        self.url_entry.grid(row=0, column=1, sticky="ew")
        self.url_entry.bind("<Return>", lambda e: self._on_analyze_click())
        
        self.analyze_btn = ctk.CTkButton(
            input_row,
            text="Analyze",
            command=self._on_analyze_click,
            font=self.FONTS["small"],
            height=38,
            width=120,
            fg_color=self.COLORS["accent"],
            hover_color=self.COLORS["accent_hover"],
        )
        self.analyze_btn.grid(row=0, column=2, padx=(10, 0))

    def _media_status_style(self) -> tuple[str, str, str]:
        """Return status text and colors for media dependencies."""
        if self.ffmpeg_available and self.ffplay_available:
            return "Media ready", "#7fe3a2", "#163d2b"
        if self.ffmpeg_available:
            return "Preview off", "#f0c96a", "#3f321a"
        return "Video only", "#f0c96a", "#3f321a"
        
    def _build_main_content(self) -> None:
        """Build the main content area."""
        self.main_tabs = ctk.CTkTabview(
            self,
            fg_color=self.COLORS["bg_primary"],
            segmented_button_fg_color=self.COLORS["bg_secondary"],
            segmented_button_selected_color=self.COLORS["accent"],
            segmented_button_selected_hover_color=self.COLORS["accent_hover"],
            segmented_button_unselected_color=self.COLORS["bg_accent"],
            segmented_button_unselected_hover_color="#303641",
            text_color=self.COLORS["text_primary"],
        )
        self.main_tabs.grid(row=1, column=0, sticky="nsew", padx=14, pady=(8, 6))

        download_tab = self.main_tabs.add("Download")
        settings_tab = self.main_tabs.add("Settings")

        download_tab.grid_rowconfigure(0, weight=1)
        download_tab.grid_columnconfigure(0, weight=0)
        download_tab.grid_columnconfigure(1, weight=1)
        download_tab.grid_columnconfigure(2, weight=0)
        
        self._build_control_panel(download_tab)
        self._build_video_list(download_tab)
        self._build_preview_sidebar(download_tab)
        self._build_settings_tab(settings_tab)
        
    def _build_video_list(self, parent) -> None:
        """Build the video list panel."""
        container = ctk.CTkFrame(
            parent,
            fg_color=self.COLORS["bg_secondary"],
            corner_radius=8,
            border_width=1,
            border_color=self.COLORS["border"],
        )
        container.grid(row=0, column=1, sticky="nsew", padx=10)
        container.grid_rowconfigure(2, weight=1)
        container.grid_columnconfigure(0, weight=1)
        
        header = ctk.CTkFrame(container, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 8))
        header.grid_columnconfigure(0, weight=1)
        
        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            title_frame,
            text="Queue",
            font=self.FONTS["heading"],
            text_color=self.COLORS["text_primary"]
        ).pack(anchor="w")

        self.queue_state_label = ctk.CTkLabel(
            title_frame,
            text="Ready",
            font=self.FONTS["tiny"],
            text_color=self.COLORS["text_muted"]
        )
        self.queue_state_label.pack(anchor="w", pady=(2, 0))

        action_row = ctk.CTkFrame(header, fg_color="transparent")
        action_row.grid(row=0, column=1, sticky="e")

        self.download_btn_header = ctk.CTkButton(
            action_row,
            text="Start",
            command=self._on_download_click,
            font=self.FONTS["small"],
            height=32,
            width=96,
            fg_color=self.COLORS["accent"],
            hover_color=self.COLORS["accent_hover"],
            state="disabled",
        )
        self.download_btn_header.pack(side="right", padx=(8, 0))

        self.deselect_all_btn = ctk.CTkButton(
            action_row,
            text="Clear selection",
            command=self._deselect_all,
            font=self.FONTS["tiny"],
            width=110,
            height=30,
            fg_color=self.COLORS["bg_accent"],
            hover_color="#303641",
        )
        self.deselect_all_btn.pack(side="right", padx=4)

        self.select_all_btn = ctk.CTkButton(
            action_row,
            text="Select all",
            command=self._select_all,
            font=self.FONTS["tiny"],
            width=90,
            height=30,
            fg_color=self.COLORS["bg_accent"],
            hover_color="#303641",
        )
        self.select_all_btn.pack(side="right", padx=4)

        metrics = ctk.CTkFrame(container, fg_color="transparent")
        metrics.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 8))

        self.video_count_label = ctk.CTkLabel(
            metrics,
            text="Videos (0)",
            font=self.FONTS["small"],
            text_color=self.COLORS["text_secondary"],
            fg_color=self.COLORS["bg_accent"],
            corner_radius=12,
            height=26,
            width=96,
        )
        self.video_count_label.pack(side="left", padx=(0, 6))
        
        self.selected_count_label = ctk.CTkLabel(
            metrics,
            text="Selected: 0",
            font=self.FONTS["small"],
            text_color=self.COLORS["text_secondary"],
            fg_color=self.COLORS["bg_accent"],
            corner_radius=12,
            height=26,
            width=104,
        )
        self.selected_count_label.pack(side="left", padx=6)
        
        self.scrollable_frame = ctk.CTkScrollableFrame(
            container,
            fg_color=self.COLORS["bg_card"],
            corner_radius=6,
            scrollbar_button_color=self.COLORS["bg_accent"],
            scrollbar_button_hover_color="#303641",
        )
        self.scrollable_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.scrollable_frame.grid_columnconfigure(0, weight=1)
        
    def _build_control_panel(self, parent) -> None:
        """Build the left sidebar with download controls."""
        sidebar = ctk.CTkFrame(
            parent,
            width=286,
            fg_color=self.COLORS["bg_secondary"],
            corner_radius=8,
            border_width=1,
            border_color=self.COLORS["border"],
        )
        sidebar.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(0, weight=1)
        sidebar.grid_columnconfigure(0, weight=1)
        
        self._build_download_panel(sidebar)

    def _build_preview_sidebar(self, parent) -> None:
        """Build the right sidebar dedicated to preview and selected video details."""
        sidebar = ctk.CTkFrame(
            parent,
            width=314,
            fg_color=self.COLORS["bg_secondary"],
            corner_radius=8,
            border_width=1,
            border_color=self.COLORS["border"],
        )
        sidebar.grid(row=0, column=2, sticky="nsew", padx=(10, 0))
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(1, weight=1)
        sidebar.grid_columnconfigure(0, weight=1)

        self._build_preview_panel(sidebar)
        self._build_detail_panel(sidebar)
        
    def _build_preview_panel(self, parent) -> None:
        """Build the video preview panel."""
        preview = ctk.CTkFrame(parent, fg_color="transparent")
        preview.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 8))
        
        ctk.CTkLabel(
            preview,
            text="Preview",
            font=self.FONTS["heading"],
            text_color=self.COLORS["text_primary"]
        ).pack(anchor="w", pady=(0, 5))

        preview_shell = ctk.CTkFrame(
            preview,
            fg_color="#111318",
            corner_radius=8,
            border_width=1,
            border_color=self.COLORS["border"],
        )
        preview_shell.pack(fill="x")
        
        self.video_player = VideoPlayer(preview_shell, height=150, status_callback=self._set_status_line)

    def _build_detail_panel(self, parent) -> None:
        """Build selected video details panel."""
        panel = ctk.CTkFrame(parent, fg_color="transparent")
        panel.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 12))
        panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            panel,
            text="Details",
            font=self.FONTS["heading"],
            text_color=self.COLORS["text_primary"],
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        detail_box = ctk.CTkFrame(
            panel,
            fg_color="#111318",
            corner_radius=8,
            border_width=1,
            border_color=self.COLORS["border"],
        )
        detail_box.grid(row=1, column=0, sticky="ew")
        detail_box.grid_columnconfigure(0, weight=1)

        self.preview_title_label = ctk.CTkLabel(
            detail_box,
            text="No video selected",
            font=("Segoe UI", 12, "bold"),
            text_color=self.COLORS["text_primary"],
            anchor="w",
            justify="left",
            wraplength=260,
        )
        self.preview_title_label.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 4))

        self.preview_meta_label = ctk.CTkLabel(
            detail_box,
            text="Click a queue item to preview it.",
            font=self.FONTS["small"],
            text_color=self.COLORS["text_muted"],
            anchor="w",
            justify="left",
            wraplength=260,
        )
        self.preview_meta_label.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 12))

        action_row = ctk.CTkFrame(panel, fg_color="transparent")
        action_row.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        action_row.grid_columnconfigure(0, weight=1)
        action_row.grid_columnconfigure(1, weight=1)

        self.preview_select_btn = ctk.CTkButton(
            action_row,
            text="Select",
            command=self._select_preview_video,
            height=30,
            fg_color=self.COLORS["accent"],
            hover_color=self.COLORS["accent_hover"],
            state="disabled",
        )
        self.preview_select_btn.grid(row=0, column=0, sticky="ew", padx=(0, 5))

        self.preview_exclude_btn = ctk.CTkButton(
            action_row,
            text="Exclude",
            command=self._exclude_preview_video,
            height=30,
            fg_color=self.COLORS["bg_accent"],
            hover_color="#303641",
            state="disabled",
        )
        self.preview_exclude_btn.grid(row=0, column=1, sticky="ew", padx=(5, 0))
        
    def _build_download_panel(self, parent) -> None:
        """Build the download controls panel."""
        panel = ctk.CTkFrame(parent, fg_color="transparent")
        panel.grid(row=0, column=0, sticky="nsew", padx=16, pady=12)
        
        panel.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            panel,
            text="Controls",
            font=self.FONTS["heading"],
            text_color=self.COLORS["text_primary"]
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))
        
        format_frame = ctk.CTkFrame(panel, fg_color="transparent")
        format_frame.grid(row=1, column=0, sticky="ew", pady=2)
        
        ctk.CTkLabel(
            format_frame,
            text="Format:",
            font=self.FONTS["small"],
            text_color=self.COLORS["text_secondary"]
        ).pack(anchor="w", pady=(0, 3))
        
        self.format_var = ctk.StringVar(
            value=self.config_manager.get("download.last_format", "MP4 720p")
        )
        
        format_values = (
            FormatManager.get_all_formats() 
            if self.ffmpeg_available 
            else FormatManager.get_video_formats()
        )
        
        self.format_combo = ctk.CTkComboBox(
            format_frame,
            values=format_values,
            variable=self.format_var,
            command=self._on_format_change,
            font=self.FONTS["small"],
            height=32,
            dropdown_font=self.FONTS["small"],
            fg_color="#101217",
            border_color=self.COLORS["border"],
            button_color=self.COLORS["bg_accent"],
            button_hover_color="#303641",
        )
        self.format_combo.pack(fill="x", pady=3)
        
        folder_frame = ctk.CTkFrame(panel, fg_color="transparent")
        folder_frame.grid(row=2, column=0, sticky="ew", pady=2)
        
        ctk.CTkLabel(
            folder_frame,
            text="Folder:",
            font=self.FONTS["small"],
            text_color=self.COLORS["text_secondary"]
        ).pack(anchor="w", pady=(5, 3))
        
        folder_row = ctk.CTkFrame(folder_frame, fg_color="transparent")
        folder_row.pack(fill="x", pady=1)
        
        self.folder_label = ctk.CTkLabel(
            folder_row,
            text="Downloads",
            font=self.FONTS["small"],
            text_color=self.COLORS["text_muted"],
            anchor="w",
        )
        self.folder_label.pack(side="left", fill="x", expand=True)
        
        self.browse_btn = ctk.CTkButton(
            folder_row,
            text="Browse",
            command=self._select_folder,
            font=self.FONTS["tiny"],
            width=74,
            height=28,
            fg_color=self.COLORS["bg_accent"],
            hover_color="#303641",
        )
        self.browse_btn.pack(side="right", padx=(8, 0))
        
        self.download_folder = Path(
            self.config_manager.get("download.last_folder") 
            or str(Path.home() / "Downloads")
        )
        self.folder_label.configure(text=self._format_folder_label(self.download_folder))
        
        action_buttons = ctk.CTkFrame(panel, fg_color="transparent")
        action_buttons.grid(row=3, column=0, sticky="ew", pady=(8, 6))
        action_buttons.grid_columnconfigure(0, weight=1)
        action_buttons.grid_columnconfigure(1, weight=1)

        self.open_folder_btn = ctk.CTkButton(
            action_buttons,
            text="Open folder",
            command=self._open_download_folder,
            font=self.FONTS["small"],
            height=32,
            fg_color=self.COLORS["bg_accent"],
            hover_color="#303641",
        )
        self.open_folder_btn.grid(row=0, column=0, sticky="ew", padx=(0, 5))

        self.stop_btn = ctk.CTkButton(
            action_buttons,
            text="Stop",
            command=self._on_stop_click,
            font=self.FONTS["small"],
            height=32,
            fg_color=self.COLORS["danger"],
            hover_color=self.COLORS["danger_hover"],
            state="disabled",
        )
        self.stop_btn.grid(row=0, column=1, sticky="ew", padx=(5, 0))

        self.start_btn_sidebar = ctk.CTkButton(
            panel,
            text="Start selected",
            command=self._on_download_click,
            font=self.FONTS["small"],
            height=34,
            fg_color=self.COLORS["accent"],
            hover_color=self.COLORS["accent_hover"],
            state="disabled",
        )
        self.start_btn_sidebar.grid(row=4, column=0, sticky="ew", pady=(0, 8))
        
        self.progress = ProgressBar(panel, label="Progress")
        self.progress.grid(row=5, column=0, sticky="ew", pady=(2, 0))

    def _build_settings_tab(self, parent) -> None:
        """Build the application settings tab."""
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        content = ctk.CTkScrollableFrame(
            parent,
            fg_color=self.COLORS["bg_primary"],
            scrollbar_button_color=self.COLORS["bg_accent"],
            scrollbar_button_hover_color="#303641",
        )
        content.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            content,
            text="Settings",
            font=("Segoe UI", 18, "bold"),
            text_color=self.COLORS["text_primary"],
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(2, 12))

        download_card = self._settings_card(content, "Download defaults")
        download_card.grid(row=1, column=0, sticky="nsew", padx=(8, 6), pady=(0, 12))

        self.settings_format_var = ctk.StringVar(value=self.format_var.get())
        ctk.CTkLabel(
            download_card,
            text="Default format",
            font=self.FONTS["small"],
            text_color=self.COLORS["text_secondary"],
        ).grid(row=1, column=0, sticky="w", padx=14, pady=(10, 4))

        self.settings_format_combo = ctk.CTkComboBox(
            download_card,
            values=list(self.format_combo.cget("values")),
            variable=self.settings_format_var,
            command=self._on_setting_format_change,
            font=self.FONTS["small"],
            height=34,
            fg_color="#101217",
            border_color=self.COLORS["border"],
            button_color=self.COLORS["bg_accent"],
            button_hover_color="#303641",
        )
        self.settings_format_combo.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 10))

        ctk.CTkLabel(
            download_card,
            text="Parallel downloads",
            font=self.FONTS["small"],
            text_color=self.COLORS["text_secondary"],
        ).grid(row=3, column=0, sticky="w", padx=14, pady=(0, 4))

        self.settings_workers_var = ctk.StringVar(
            value=str(self.config_manager.get("download.parallel_workers", 2))
        )
        self.settings_workers_combo = ctk.CTkComboBox(
            download_card,
            values=["1", "2", "3", "4"],
            variable=self.settings_workers_var,
            command=self._on_parallel_workers_change,
            font=self.FONTS["small"],
            height=34,
            width=120,
            fg_color="#101217",
            border_color=self.COLORS["border"],
            button_color=self.COLORS["bg_accent"],
            button_hover_color="#303641",
        )
        self.settings_workers_combo.grid(row=4, column=0, sticky="w", padx=14, pady=(0, 10))

        folder_row = ctk.CTkFrame(download_card, fg_color="transparent")
        folder_row.grid(row=5, column=0, sticky="ew", padx=14, pady=(0, 14))
        folder_row.grid_columnconfigure(0, weight=1)

        self.settings_folder_label = ctk.CTkLabel(
            folder_row,
            text=self._format_folder_label(self.download_folder),
            font=self.FONTS["small"],
            text_color=self.COLORS["text_muted"],
            anchor="w",
        )
        self.settings_folder_label.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        ctk.CTkButton(
            folder_row,
            text="Change folder",
            command=self._select_folder,
            font=self.FONTS["small"],
            width=120,
            height=30,
            fg_color=self.COLORS["bg_accent"],
            hover_color="#303641",
        ).grid(row=0, column=1, sticky="e")

        app_card = self._settings_card(content, "Application")
        app_card.grid(row=1, column=1, sticky="nsew", padx=(6, 8), pady=(0, 12))

        self.confirm_quit_var = ctk.BooleanVar(
            value=self.config_manager.get("ui.confirm_on_quit", True)
        )
        ctk.CTkSwitch(
            app_card,
            text="Confirm before quitting",
            variable=self.confirm_quit_var,
            command=self._on_confirm_quit_changed,
            font=self.FONTS["small"],
            text_color=self.COLORS["text_secondary"],
            fg_color=self.COLORS["bg_accent"],
            progress_color=self.COLORS["accent"],
            button_color=self.COLORS["text_secondary"],
            button_hover_color=self.COLORS["text_primary"],
        ).grid(row=1, column=0, sticky="w", padx=14, pady=(10, 12))

        ctk.CTkLabel(
            app_card,
            text="Preview player",
            font=self.FONTS["small"],
            text_color=self.COLORS["text_secondary"],
        ).grid(row=2, column=0, sticky="w", padx=14, pady=(0, 4))

        ctk.CTkLabel(
            app_card,
            text=f"{self.config_manager.get('preview.player', 'ffplay')} {'ready' if self.ffplay_available else 'not found'} | Quality auto",
            font=self.FONTS["small"],
            text_color=self.COLORS["text_muted"],
            anchor="w",
        ).grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 14))

        about_card = self._settings_card(content, "About")
        about_card.grid(row=2, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 8))

        ctk.CTkLabel(
            about_card,
            text="Yuoop is a free desktop app focused on clear, preview-first downloads.",
            font=self.FONTS["small"],
            text_color=self.COLORS["text_secondary"],
            anchor="w",
            justify="left",
            wraplength=760,
        ).grid(row=1, column=0, sticky="ew", padx=14, pady=(10, 8))

        ctk.CTkButton(
            about_card,
            text="Show credits",
            command=self._toggle_about_section,
            font=self.FONTS["small"],
            width=120,
            height=30,
            fg_color=self.COLORS["bg_accent"],
            hover_color="#303641",
        ).grid(row=2, column=0, sticky="w", padx=14, pady=(0, 12))

        self.about_frame = ctk.CTkFrame(
            about_card,
            fg_color="#111318",
            corner_radius=6,
            border_width=1,
            border_color=self.COLORS["border"],
        )
        self.about_frame.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 14))
        self.about_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.about_frame,
            text="Nawfel Reghai",
            font=("Segoe UI", 13, "bold"),
            text_color=self.COLORS["text_primary"],
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 2))

        ctk.CTkLabel(
            self.about_frame,
            text=(
                "Application gratuite creee avec soin. Merci de l'utiliser, "
                "de la partager, et de la faire vivre avec exigence."
            ),
            font=self.FONTS["small"],
            text_color=self.COLORS["text_muted"],
            anchor="w",
            justify="left",
            wraplength=760,
        ).grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 10))

        self.about_frame.grid_remove()

    def _settings_card(self, parent, title: str) -> ctk.CTkFrame:
        """Return a simple settings group frame."""
        card = ctk.CTkFrame(
            parent,
            fg_color=self.COLORS["bg_secondary"],
            corner_radius=8,
            border_width=1,
            border_color=self.COLORS["border"],
        )
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            card,
            text=title,
            font=self.FONTS["heading"],
            text_color=self.COLORS["text_primary"],
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 2))
        return card
        
    def _build_status_bar(self) -> None:
        """Build a compact status line instead of a full log console."""
        status = ctk.CTkFrame(self, height=34, fg_color=self.COLORS["bg_secondary"], corner_radius=0)
        status.grid(row=2, column=0, sticky="ew", padx=0, pady=0)
        status.grid_propagate(False)
        status.grid_columnconfigure(0, weight=1)

        self.status_line_label = ctk.CTkLabel(
            status,
            text="Ready",
            font=self.FONTS["small"],
            text_color=self.COLORS["text_secondary"],
            anchor="w",
        )
        self.status_line_label.grid(row=0, column=0, sticky="ew", padx=(16, 8), pady=6)

        self.author_status_label = ctk.CTkLabel(
            status,
            text="Free app by Nawfel Reghai",
            font=self.FONTS["tiny"],
            text_color=self.COLORS["text_muted"],
        )
        self.author_status_label.grid(row=0, column=1, sticky="e", padx=(8, 16), pady=6)
        
    def _register_callbacks(self) -> None:
        """Register event callbacks."""
        self.logger.add_ui_callback(self._log_callback)
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _on_format_change(self, value: str) -> None:
        """Persist format changes made from the download controls."""
        self.config_manager.set("download.last_format", value)
        self.config_manager.save_config()
        if hasattr(self, "settings_format_var"):
            self.settings_format_var.set(value)
        self._set_status_line(f"Default format: {value}")

    def _on_setting_format_change(self, value: str) -> None:
        """Apply a default format selected from settings."""
        self.format_var.set(value)
        self._on_format_change(value)

    def _on_parallel_workers_change(self, value: str) -> None:
        """Persist and apply parallel worker setting when possible."""
        try:
            workers = max(1, min(int(value), 4))
        except ValueError:
            workers = 2

        self.settings_workers_var.set(str(workers))
        self.config_manager.set("download.parallel_workers", workers)
        self.config_manager.save_config()

        if self.is_downloading:
            self._set_status_line(f"Parallel downloads set to {workers}; applies after this batch.")
            return

        self.download_manager.stop()
        self.download_manager = DownloadQueueManager(workers)
        self.download_manager.start()
        self._set_status_line(f"Parallel downloads: {workers}")

    def _on_confirm_quit_changed(self) -> None:
        """Persist quit confirmation preference."""
        enabled = bool(self.confirm_quit_var.get())
        self.config_manager.set("ui.confirm_on_quit", enabled)
        self.config_manager.save_config()
        self._set_status_line("Quit confirmation enabled" if enabled else "Quit confirmation disabled")

    def _toggle_about_section(self) -> None:
        """Show or hide author credits."""
        if not hasattr(self, "about_frame"):
            return
        if self.about_frame.winfo_ismapped():
            self.about_frame.grid_remove()
            self._set_status_line("Credits hidden")
        else:
            self.about_frame.grid()
            self._set_status_line("Created by Nawfel Reghai")

    def _set_download_folder(self, folder: Path) -> None:
        """Persist and reflect the current download folder in every view."""
        self.download_folder = folder
        self.config_manager.set("download.last_folder", str(self.download_folder))
        self.config_manager.save_config()
        label = self._format_folder_label(self.download_folder)
        if hasattr(self, "folder_label"):
            self.folder_label.configure(text=label)
        if hasattr(self, "settings_folder_label"):
            self.settings_folder_label.configure(text=label)
        self._set_status_line(f"Download folder: {label}")

    def _set_status_line(self, message: str) -> None:
        """Show latest activity line."""
        if hasattr(self, "status_line_label"):
            self.status_line_label.configure(text=message)

    def _run_on_ui(self, callback, *args) -> None:
        """Schedule a callback on the Tk main thread."""
        try:
            if self.winfo_exists():
                self.after(0, callback, *args)
        except Exception:
            pass
        
    def _on_analyze_click(self, event=None) -> None:
        """Handle analyze button click."""
        url = self.url_entry.get().strip()
        
        if not url:
            messagebox.showerror("Error", "Please enter a YouTube URL")
            return
            
        is_valid, url_type = is_valid_youtube_url(url)
        if not is_valid:
            messagebox.showerror("Error", "Invalid YouTube URL")
            return
        
        self._show_loading_state()
        self.queue_state_label.configure(text="Analyzing source")
        self.analyze_btn.configure(state="disabled")
        
        thread = threading.Thread(
            target=self._fetch_playlist,
            args=(url,),
            daemon=True
        )
        thread.start()
    
    def _show_loading_state(self) -> None:
        """Display loading indicator in video list."""
        self._clear_queue_widgets()
        self.videos.clear()
        self.video_order.clear()
        self.video_status.clear()
        self.selected_videos.clear()
        self.current_preview_video_id = None
        self.video_count_label.configure(text="Videos (0)")
        self.selected_count_label.configure(text="Selected: 0")
        self.download_btn_header.configure(text="Start", state="disabled")
        self.start_btn_sidebar.configure(text="Start selected", state="disabled")
        if hasattr(self, "preview_title_label"):
            self.preview_title_label.configure(text="No video selected")
            self.preview_meta_label.configure(text="Click a queue item to preview it.")
            self.preview_select_btn.configure(state="disabled")
            self.preview_exclude_btn.configure(state="disabled")
        if hasattr(self, "video_player"):
            self.video_player.clear("No video selected")
            
        loading = ctk.CTkLabel(
            self.scrollable_frame,
            text="Analyzing source...\nLarge playlists can take 1-2 minutes.",
            font=self.FONTS["body"],
            text_color=self.COLORS["text_secondary"]
        )
        loading.pack(pady=40)
    
    def _fetch_playlist(self, url: str) -> None:
        """Fetch playlist in background thread."""
        try:
            is_valid, url_type = is_valid_youtube_url(url)
            extractor = YouTubePlaylistExtractor()
            
            if url_type == 'video':
                videos, error = extractor.extract_single_video(url)
            else:
                videos, error = extractor.extract_videos(url)

            self._run_on_ui(self._handle_playlist_result, videos, error)
        finally:
            self._run_on_ui(lambda: self.analyze_btn.configure(state="normal"))

    def _handle_playlist_result(self, videos: List[VideoInfo], error: Optional[str]) -> None:
        """Handle playlist extraction result on the UI thread."""
        if error:
            self.logger.error(f"Failed: {error}")
            messagebox.showerror("Error", f"Failed to analyze URL:\n{error}")
            self._display_empty_state("No videos loaded")
            return

        self.logger.success(f"Found {len(videos)} videos")
        self._display_videos(videos)
        
    def _display_videos(self, videos: List[VideoInfo]) -> None:
        """Display videos in the list."""
        self._clear_queue_widgets()
        self.videos = {v.video_id: v for v in videos}
        self.video_order = [v.video_id for v in videos]
        self.video_status.clear()
        self.selected_videos.clear()
        self.rendered_video_count = 0
        self.current_preview_video_id = None
        
        self.video_count_label.configure(text=f"Videos ({len(videos)})")
        self.queue_state_label.configure(text="Preparing queue")
        self._set_status_line(f"Preparing queue: {len(videos)} videos")
        self._update_selection_ui()
        generation = self.queue_render_generation
        self.queue_render_job = self.after(1, lambda: self._render_next_video_page(generation))

    def _clear_queue_widgets(self) -> None:
        """Remove every rendered queue widget and reset queue render state."""
        if self.queue_render_job is not None:
            try:
                self.after_cancel(self.queue_render_job)
            except Exception:
                pass
            self.queue_render_job = None
        self.queue_render_generation += 1
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.video_cards.clear()
        self.queue_load_more_btn = None
        self.rendered_video_count = 0

    def _render_next_video_page(self, generation: Optional[int] = None) -> None:
        """Render the next page of queue cards without locking up the UI."""
        if generation is None:
            generation = self.queue_render_generation
        if generation != self.queue_render_generation:
            return
        self.queue_render_job = None

        if self.queue_load_more_btn and self.queue_load_more_btn.winfo_exists():
            self.queue_load_more_btn.destroy()
        self.queue_load_more_btn = None

        total = len(self.video_order)
        target = min(self.rendered_video_count + self.QUEUE_PAGE_SIZE, total)
        self.queue_state_label.configure(text=f"Loading queue {self.rendered_video_count}/{total}")
        self._render_video_batch(target, generation)

    def _render_video_batch(self, target: int, generation: int) -> None:
        """Render a small batch of video cards, then yield back to Tk."""
        if generation != self.queue_render_generation:
            return
        self.queue_render_job = None

        total = len(self.video_order)
        start = self.rendered_video_count
        end = min(start + self.QUEUE_RENDER_BATCH_SIZE, target)

        for video_id in self.video_order[start:end]:
            video = self.videos[video_id]
            card = self._create_video_card(video)
            card.pack(fill="x", padx=3, pady=2)
            self.video_cards[video_id] = card

            if video_id in self.selected_videos:
                card.set_checked(True)
            if video_id in self.video_status:
                card.set_status(self.video_status[video_id])

        self.rendered_video_count = end
        self._update_selection_ui()

        if end < target:
            self.queue_render_job = self.after(1, lambda: self._render_video_batch(target, generation))
            return

        self._build_load_more_button()
        if total:
            if self.rendered_video_count < total:
                self._set_status_line(f"Showing {self.rendered_video_count}/{total} videos. Load more when needed.")
            else:
                self._set_status_line(f"Queue ready: {total} videos")

    def _create_video_card(self, video: VideoInfo) -> VideoCard:
        """Create a queue card for one video."""
        duration = YouTubePlaylistExtractor.format_duration(video.duration)
        subtitle = video.uploader or "YouTube"
        return VideoCard(
            self.scrollable_frame,
            video_id=video.video_id,
            title=video.title,
            duration=duration,
            thumbnail_url=video.thumbnail_url,
            subtitle=subtitle,
            load_thumbnail=True,
            on_select=self._on_video_select,
            on_double_click=self._on_video_double_click,
            fg_color=self.COLORS["bg_card"],
        )

    def _build_load_more_button(self) -> None:
        """Add a compact pagination control for very large queues."""
        total = len(self.video_order)
        if self.rendered_video_count >= total:
            return

        self.queue_load_more_btn = ctk.CTkButton(
            self.scrollable_frame,
            text=f"Show more videos ({self.rendered_video_count}/{total})",
            command=self._render_next_video_page,
            font=self.FONTS["small"],
            height=34,
            fg_color=self.COLORS["bg_accent"],
            hover_color="#303641",
        )
        self.queue_load_more_btn.pack(fill="x", padx=3, pady=(8, 4))

    def _display_empty_state(self, message: str) -> None:
        """Display an empty state in the video list."""
        self._clear_queue_widgets()

        self.videos.clear()
        self.video_order.clear()
        self.video_status.clear()
        self.selected_videos.clear()
        self.current_preview_video_id = None
        self.video_count_label.configure(text="Videos (0)")
        self.queue_state_label.configure(text="Ready")
        self._update_selection_ui()
        if hasattr(self, "preview_title_label"):
            self.preview_title_label.configure(text="No video selected")
            self.preview_meta_label.configure(text="Click a queue item to preview it.")
            self.preview_select_btn.configure(state="disabled")
            self.preview_exclude_btn.configure(state="disabled")
        if hasattr(self, "video_player"):
            self.video_player.clear()

        ctk.CTkLabel(
            self.scrollable_frame,
            text=message,
            font=self.FONTS["body"],
            text_color=self.COLORS["text_secondary"]
        ).pack(pady=40)
    
    def _on_video_select(self, video_id: str, is_selected: bool) -> None:
        """Handle video selection."""
        if is_selected:
            self.selected_videos.add(video_id)
        else:
            self.selected_videos.discard(video_id)
        
        self._update_selection_ui()
    
    def _update_selection_ui(self) -> None:
        """Update selection counter display."""
        count = len(self.selected_videos)
        total = len(self.videos)
        self.selected_count_label.configure(text=f"Selected: {count}")
        button_text = f"Start ({count})" if count > 0 else "Start"
        self.download_btn_header.configure(text=button_text)
        self.start_btn_sidebar.configure(text=f"Start selected ({count})" if count > 0 else "Start selected")
        if count == 0 or self.is_downloading:
            self.download_btn_header.configure(state="disabled")
            self.start_btn_sidebar.configure(state="disabled")
        else:
            self.download_btn_header.configure(state="normal")
            self.start_btn_sidebar.configure(state="normal")

        if self.is_downloading:
            self.queue_state_label.configure(text=f"Downloading {self.download_completed}/{self.download_total}")
        elif self.videos:
            shown = min(self.rendered_video_count, total)
            selection = f"{count} selected" if count else "Select items to build a batch"
            if shown < total:
                selection = f"{selection} | showing {shown}/{total}"
            self.queue_state_label.configure(text=selection)
        else:
            self.queue_state_label.configure(text="Ready")
    
    def _on_video_double_click(self, video_id: str) -> None:
        """Handle queue item click for preview."""
        if video_id in self.videos:
            video = self.videos[video_id]
            self.logger.info(f"Preview: {video.title}")
            self._update_preview_details(video)
            self.video_player.load_video(video.url, video.thumbnail_url, video.duration)

    def _update_preview_details(self, video: VideoInfo) -> None:
        """Update right-side details for the selected video."""
        self.current_preview_video_id = video.video_id
        duration = YouTubePlaylistExtractor.format_duration(video.duration)
        details = []
        if duration:
            details.append(duration)
        if video.uploader:
            details.append(video.uploader)
        if video.upload_date:
            details.append(video.upload_date)

        self.preview_title_label.configure(text=video.title)
        self.preview_meta_label.configure(text=" | ".join(details) if details else video.url)
        self.preview_select_btn.configure(state="normal")
        self.preview_exclude_btn.configure(state="normal")

    def _select_preview_video(self) -> None:
        """Select the currently previewed video for download."""
        if not self.current_preview_video_id:
            return
        self._set_video_checked(self.current_preview_video_id, True)

    def _exclude_preview_video(self) -> None:
        """Remove the currently previewed video from the download selection."""
        if not self.current_preview_video_id:
            return
        self._set_video_checked(self.current_preview_video_id, False)

    def _set_video_checked(self, video_id: str, checked: bool) -> None:
        """Set checked state for a video card and update selection state."""
        card = self.video_cards.get(video_id)
        if card and card.winfo_exists():
            card.set_checked(checked)

        if checked:
            self.selected_videos.add(video_id)
            action = "Selected"
        else:
            self.selected_videos.discard(video_id)
            action = "Excluded"
        self._update_selection_ui()
        if video_id in self.videos:
            self._set_status_line(f"{action}: {self.videos[video_id].title}")
    
    def _select_all(self) -> None:
        """Select all videos."""
        self.selected_videos = set(self.videos.keys())
        for card in self.video_cards.values():
            if card.winfo_exists():
                card.set_checked(True)
        self._update_selection_ui()
            
    def _deselect_all(self) -> None:
        """Deselect all videos."""
        for card in self.video_cards.values():
            if card.winfo_exists():
                card.set_checked(False)
        self.selected_videos.clear()
        self._update_selection_ui()
        
    def _select_folder(self) -> None:
        """Open folder selection dialog."""
        folder = filedialog.askdirectory(
            title="Select Download Folder",
            initialdir=str(self.download_folder)
        )
        
        if folder:
            self._set_download_folder(Path(folder))

    def _format_folder_label(self, folder: Path) -> str:
        """Return compact folder label for the sidebar."""
        try:
            home = Path.home()
            if folder == home:
                return "~"
            if home in folder.parents:
                return f"~/{folder.relative_to(home)}"
        except ValueError:
            pass
        return str(folder)

    def _open_download_folder(self) -> None:
        """Open the current download folder in the system file manager."""
        try:
            self.download_folder.mkdir(parents=True, exist_ok=True)

            if os.name == "nt":
                os.startfile(self.download_folder)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(self.download_folder)])
            else:
                subprocess.Popen(["xdg-open", str(self.download_folder)])
            self._set_status_line(f"Opened folder: {self._format_folder_label(self.download_folder)}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder:\n{e}")
            self._set_status_line("Could not open download folder")

    def _on_download_click(self) -> None:
        """Handle download button click."""
        if not self.selected_videos:
            messagebox.showwarning("Warning", "Please select at least one video")
            return
            
        format_name = self.format_var.get()
        if not format_name:
            messagebox.showerror("Error", "Please select a format")
            return
            
        self.download_folder.mkdir(parents=True, exist_ok=True)
        
        tasks = []
        for video_id in self.selected_videos:
            if video_id not in self.videos:
                continue
                
            video = self.videos[video_id]
            tasks.append(DownloadTask(
                video_id=video_id,
                title=video.title,
                url=video.url,
                format_name=format_name,
                output_path=self.download_folder,
                on_progress=self._on_download_progress,
                on_complete=self._on_download_complete
            ))
            
        self.config_manager.set("download.last_format", format_name)
        self.config_manager.save_config()
        
        count = self.download_manager.enqueue_tasks(tasks)
        if count > 0:
            self.is_downloading = True
            self.download_cancel_requested = False
            self.download_total = count
            self.download_completed = 0
            self.download_progress = {task.video_id: 0 for task in tasks}
            self.logger.info(f"Queued {count} downloads")
            self.progress.set_label(f"Queued 0/{count}")
            self.progress.set_progress(0, 100)
            self.queue_state_label.configure(text=f"Downloading 0/{count}")
            for task in tasks:
                self._update_video_status(task.video_id, "Queued")
            self.download_btn_header.configure(state="disabled")
            self.start_btn_sidebar.configure(state="disabled")
            self.stop_btn.configure(state="normal")
        else:
            messagebox.showerror("Error", "Failed to enqueue downloads")

    def _on_download_progress(self, video_id: str, current: int, maximum: int) -> None:
        """Handle download progress callback."""
        self._run_on_ui(self._apply_download_progress, video_id, current, maximum)

    def _apply_download_progress(self, video_id: str, current: int, maximum: int) -> None:
        """Update progress indicators on the UI thread."""
        if maximum <= 0:
            return

        percent = max(0, min(int((current / maximum) * 100), 100))
        if video_id in self.download_progress:
            self.download_progress[video_id] = percent

        if percent < 100:
            self._update_video_status(video_id, f"{percent}%")

        if self.download_progress:
            average = int(sum(self.download_progress.values()) / len(self.download_progress))
            self.progress.set_progress(average, 100)
            self.progress.set_label(f"Downloading {self.download_completed}/{self.download_total}")
            self.queue_state_label.configure(text=f"Downloading {self.download_completed}/{self.download_total}")

    def _on_download_complete(self, video_id: str, success: bool, error_msg: Optional[str]) -> None:
        """Handle download completion callback."""
        self._run_on_ui(self._apply_download_complete, video_id, success, error_msg)

    def _apply_download_complete(self, video_id: str, success: bool, error_msg: Optional[str]) -> None:
        """Update completion state on the UI thread."""
        self.download_completed += 1
        if video_id in self.download_progress:
            self.download_progress[video_id] = 100

        if success:
            self._update_video_status(video_id, "Downloaded")
        elif error_msg == "Canceled":
            self._update_video_status(video_id, "Canceled")
        else:
            self._update_video_status(video_id, "Failed")

        if self.download_total:
            self.progress.set_progress(self.download_completed, self.download_total)
            label = "Canceled" if self.download_cancel_requested else "Completed"
            self.progress.set_label(f"{label} {self.download_completed}/{self.download_total}")
            self.queue_state_label.configure(text=f"{label} {self.download_completed}/{self.download_total}")

        if self.download_completed >= self.download_total:
            self.is_downloading = False
            self.stop_btn.configure(state="disabled")
            self._update_selection_ui()
            
    def _update_video_status(self, video_id: str, status: str) -> None:
        """Update video card status."""
        self.video_status[video_id] = status
        card = self.video_cards.get(video_id)
        if card and card.winfo_exists():
            card.set_status(status)
                
    def _on_stop_click(self) -> None:
        """Handle stop button click."""
        self.stop_btn.configure(state="disabled")
        self.download_cancel_requested = True
        self.download_manager.stop()
        self.download_manager = DownloadQueueManager(
            self.config_manager.get("download.parallel_workers", 2)
        )
        self.download_manager.start()
        
        self.logger.warning("Downloads stopped")
        self.is_downloading = False
        self.progress.set_label("Canceled")
        self.progress.set_progress(0, 100)
        self._update_selection_ui()
        self.queue_state_label.configure(text="Canceled")
        
        for video_id in list(self.selected_videos):
            self._update_video_status(video_id, "Canceled")
                    
    def _log_callback(self, message: str) -> None:
        """Receive log messages for display."""
        self._run_on_ui(self._set_status_line, message)
        
    def _on_closing(self) -> None:
        """Handle window close."""
        confirm = self.config_manager.get("ui.confirm_on_quit", True)
        if confirm and not messagebox.askokcancel("Quit", "Are you sure you want to quit?"):
            return

        self.logger.info("Shutting down...")
        self.logger.remove_ui_callback(self._log_callback)
        if hasattr(self, "video_player"):
            self.video_player.clear()
        self.download_manager.stop()

        self.config_manager.set("ui.window_width", self.winfo_width())
        self.config_manager.set("ui.window_height", self.winfo_height())
        self.config_manager.save_config()

        self.destroy()
