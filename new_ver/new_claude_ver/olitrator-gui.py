#!/usr/bin/env python3
"""
Obliterator GUI Application
Purpose: Modern GUI interface for secure data wiping
Runtime: Python 3.x with CustomTkinter on Bookworm Puppy Linux
Privileges: root required for device access
Usage: python3 obliterator-gui.py [--test] [--config CONFIG_FILE]
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
import threading
import time
import json
import os
import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
import subprocess

# Import our modules
try:
    from device_detection import DeviceDetector
    from wiping_engine import WipingEngine, SanitizationMethod, WipeProgress, WipeStatus
except ImportError:
    # If modules are not in the same directory, try to import from lib
    sys.path.append('/opt/obliterator/lib')
    from device_detection import DeviceDetector
    from wiping_engine import WipingEngine, SanitizationMethod, WipeProgress, WipeStatus

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# CustomTkinter appearance and theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Purple theme colors
PURPLE_DARK = "#2D1B3D"
PURPLE_MEDIUM = "#4A2C5A"
PURPLE_LIGHT = "#6B3D7A"
PURPLE_ACCENT = "#8E4EC6"
PURPLE_BRIGHT = "#B565D8"
WHITE = "#FFFFFF"
GRAY_LIGHT = "#E0E0E0"
GRAY_DARK = "#4A4A4A"
RED = "#FF5555"
GREEN = "#55FF55"

@dataclass
class AppConfig:
    """Application configuration"""
    window_width: int = 1024
    window_height: int = 768
    theme: str = "dark"
    auto_detect_devices: bool = True
    confirm_wipes: bool = True
    show_advanced: bool = False
    log_level: str = "INFO"

class SplashScreen:
    """Splash screen shown during application startup"""

    def __init__(self):
        self.splash = ctk.CTkToplevel()
        self.splash.title("")
        self.splash.geometry("400x300")
        self.splash.resizable(False, False)

        # Center the splash screen
        self.splash.update_idletasks()
        x = (self.splash.winfo_screenwidth() // 2) - (400 // 2)
        y = (self.splash.winfo_screenheight() // 2) - (300 // 2)
        self.splash.geometry(f"+{x}+{y}")

        # Remove window decorations
        self.splash.overrideredirect(True)

        # Create splash content
        self.create_splash_content()

        # Make splash modal
        self.splash.transient()
        self.splash.grab_set()

    def create_splash_content(self):
        """Create splash screen content"""
        # Main frame with purple gradient effect
        main_frame = ctk.CTkFrame(self.splash, fg_color=PURPLE_DARK, corner_radius=10)
        main_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Logo/Title
        title_label = ctk.CTkLabel(
            main_frame,
            text="OBLITERATOR",
            font=ctk.CTkFont(family="Arial", size=36, weight="bold"),
            text_color=PURPLE_BRIGHT
        )
        title_label.pack(pady=(40, 10))

        # Subtitle
        subtitle_label = ctk.CTkLabel(
            main_frame,
            text="Secure Data Wiping Solution",
            font=ctk.CTkFont(family="Arial", size=14),
            text_color=GRAY_LIGHT
        )
        subtitle_label.pack(pady=(0, 20))

        # Version info
        version_label = ctk.CTkLabel(
            main_frame,
            text="Version 1.0.0 - NIST SP 800-88r2 Compliant",
            font=ctk.CTkFont(family="Arial", size=10),
            text_color=GRAY_LIGHT
        )
        version_label.pack(pady=(0, 20))

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(
            main_frame,
            width=300,
            height=10,
            fg_color=GRAY_DARK,
            progress_color=PURPLE_ACCENT
        )
        self.progress_bar.pack(pady=(0, 10))
        self.progress_bar.set(0)

        # Status label
        self.status_label = ctk.CTkLabel(
            main_frame,
            text="Initializing...",
            font=ctk.CTkFont(family="Arial", size=12),
            text_color=WHITE
        )
        self.status_label.pack(pady=(0, 40))

    def update_progress(self, value: float, status: str):
        """Update splash screen progress"""
        self.progress_bar.set(value)
        self.status_label.configure(text=status)
        self.splash.update()

    def close(self):
        """Close splash screen"""
        try:
            self.splash.grab_release()
            self.splash.destroy()
        except:
            pass

class ConfirmationDialog:
    """Multi-step confirmation dialog for destructive operations"""

    def __init__(self, parent, devices: List[Dict], method: str):
        self.result = False
        self.devices = devices
        self.method = method

        # Create dialog
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title("Confirm Destructive Operation")
        self.dialog.geometry("600x500")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (600 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (500 // 2)
        self.dialog.geometry(f"+{x}+{y}")

        self.create_dialog_content()

    def create_dialog_content(self):
        """Create confirmation dialog content"""
        # Warning header
        warning_frame = ctk.CTkFrame(self.dialog, fg_color=RED, corner_radius=5)
        warning_frame.pack(fill="x", padx=20, pady=(20, 10))

        warning_label = ctk.CTkLabel(
            warning_frame,
            text="⚠️ DESTRUCTIVE OPERATION WARNING ⚠️",
            font=ctk.CTkFont(family="Arial", size=16, weight="bold"),
            text_color=WHITE
        )
        warning_label.pack(pady=10)

        # Main content frame
        content_frame = ctk.CTkFrame(self.dialog, fg_color=PURPLE_DARK)
        content_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Warning message
        warning_text = (
            "You are about to perform a PERMANENT and IRREVERSIBLE operation that will "
            "COMPLETELY DESTROY ALL DATA on the selected devices.\n\n"
            "This action cannot be undone. All files, operating systems, and data will be "
            "permanently erased using cryptographically secure methods.\n\n"
            "Please review the devices and operation details below:"
        )

        warning_msg = ctk.CTkLabel(
            content_frame,
            text=warning_text,
            font=ctk.CTkFont(family="Arial", size=12),
            text_color=WHITE,
            wraplength=540,
            justify="left"
        )
        warning_msg.pack(pady=(20, 20), padx=20)

        # Device list
        device_frame = ctk.CTkFrame(content_frame, fg_color=PURPLE_MEDIUM)
        device_frame.pack(fill="x", padx=20, pady=(0, 20))

        device_header = ctk.CTkLabel(
            device_frame,
            text=f"Selected Devices ({len(self.devices)}):",
            font=ctk.CTkFont(family="Arial", size=14, weight="bold"),
            text_color=PURPLE_BRIGHT
        )
        device_header.pack(pady=(10, 5), padx=10, anchor="w")

        for device in self.devices:
            device_text = f"• {device['device']} - {device['model']} ({device['size_human']})"
            device_label = ctk.CTkLabel(
                device_frame,
                text=device_text,
                font=ctk.CTkFont(family="Courier", size=10),
                text_color=WHITE,
                anchor="w"
            )
            device_label.pack(pady=2, padx=20, anchor="w")

        method_label = ctk.CTkLabel(
            device_frame,
            text=f"Sanitization Method: {self.method.upper()}",
            font=ctk.CTkFont(family="Arial", size=12, weight="bold"),
            text_color=PURPLE_BRIGHT
        )
        method_label.pack(pady=(10, 10), padx=10)

        # Checkbox confirmation
        self.understand_var = tk.BooleanVar()
        understand_checkbox = ctk.CTkCheckBox(
            content_frame,
            text="I understand this will PERMANENTLY DESTROY ALL DATA",
            variable=self.understand_var,
            font=ctk.CTkFont(family="Arial", size=12, weight="bold"),
            text_color=WHITE,
            command=self.check_ready
        )
        understand_checkbox.pack(pady=(0, 15), padx=20)

        # Typed confirmation
        confirm_frame = ctk.CTkFrame(content_frame, fg_color=PURPLE_MEDIUM)
        confirm_frame.pack(fill="x", padx=20, pady=(0, 20))

        self.confirm_token = f"OBLITERATE-{len(self.devices)}-DEVICES"

        confirm_instruction = ctk.CTkLabel(
            confirm_frame,
            text=f"Type the following confirmation token exactly:\n{self.confirm_token}",
            font=ctk.CTkFont(family="Arial", size=12),
            text_color=WHITE
        )
        confirm_instruction.pack(pady=(10, 5), padx=10)

        self.confirm_entry = ctk.CTkEntry(
            confirm_frame,
            width=400,
            height=35,
            font=ctk.CTkFont(family="Courier", size=12),
            placeholder_text="Enter confirmation token here"
        )
        self.confirm_entry.pack(pady=(5, 15), padx=10)
        self.confirm_entry.bind("<KeyRelease>", self.check_ready)

        # Buttons
        button_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        button_frame.pack(fill="x", padx=20, pady=(0, 20))

        self.proceed_button = ctk.CTkButton(
            button_frame,
            text="PROCEED WITH WIPE",
            width=180,
            height=40,
            font=ctk.CTkFont(family="Arial", size=12, weight="bold"),
            fg_color=RED,
            hover_color="#CC4444",
            command=self.proceed,
            state="disabled"
        )
        self.proceed_button.pack(side="right", padx=(10, 0))

        cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            width=120,
            height=40,
            font=ctk.CTkFont(family="Arial", size=12),
            fg_color=GRAY_DARK,
            hover_color="#666666",
            command=self.cancel
        )
        cancel_button.pack(side="right")

    def check_ready(self, event=None):
        """Check if all confirmations are complete"""
        token_correct = self.confirm_entry.get() == self.confirm_token
        understand_checked = self.understand_var.get()

        if token_correct and understand_checked:
            self.proceed_button.configure(state="normal")
        else:
            self.proceed_button.configure(state="disabled")

    def proceed(self):
        """User confirmed the operation"""
        self.result = True
        self.dialog.destroy()

    def cancel(self):
        """User cancelled the operation"""
        self.result = False
        self.dialog.destroy()

    def show(self) -> bool:
        """Show dialog and return result"""
        self.dialog.wait_window()
        return self.result

class WipeProgressDialog:
    """Progress dialog for wipe operations"""

    def __init__(self, parent, devices: List[Dict]):
        self.devices = devices
        self.current_device_index = 0
        self.cancelled = False

        # Create dialog
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title("Wiping Devices...")
        self.dialog.geometry("700x500")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_close)

        # Center dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (700 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (500 // 2)
        self.dialog.geometry(f"+{x}+{y}")

        self.create_progress_content()

    def create_progress_content(self):
        """Create progress dialog content"""
        # Header
        header_frame = ctk.CTkFrame(self.dialog, fg_color=PURPLE_DARK)
        header_frame.pack(fill="x", padx=20, pady=(20, 10))

        self.header_label = ctk.CTkLabel(
            header_frame,
            text=f"Wiping {len(self.devices)} devices...",
            font=ctk.CTkFont(family="Arial", size=16, weight="bold"),
            text_color=WHITE
        )
        self.header_label.pack(pady=15)

        # Current device info
        device_frame = ctk.CTkFrame(self.dialog, fg_color=PURPLE_MEDIUM)
        device_frame.pack(fill="x", padx=20, pady=(0, 10))

        self.device_label = ctk.CTkLabel(
            device_frame,
            text="Initializing...",
            font=ctk.CTkFont(family="Arial", size=14),
            text_color=WHITE
        )
        self.device_label.pack(pady=10)

        # Overall progress
        overall_frame = ctk.CTkFrame(self.dialog, fg_color=PURPLE_DARK)
        overall_frame.pack(fill="x", padx=20, pady=(0, 10))

        overall_label = ctk.CTkLabel(
            overall_frame,
            text="Overall Progress:",
            font=ctk.CTkFont(family="Arial", size=12, weight="bold"),
            text_color=WHITE
        )
        overall_label.pack(pady=(10, 5), anchor="w", padx=15)

        self.overall_progress = ctk.CTkProgressBar(
            overall_frame,
            width=600,
            height=20,
            fg_color=GRAY_DARK,
            progress_color=PURPLE_ACCENT
        )
        self.overall_progress.pack(pady=(0, 10), padx=15)
        self.overall_progress.set(0)

        # Current pass progress
        pass_frame = ctk.CTkFrame(self.dialog, fg_color=PURPLE_DARK)
        pass_frame.pack(fill="x", padx=20, pady=(0, 10))

        self.pass_label = ctk.CTkLabel(
            pass_frame,
            text="Current Pass: Initializing",
            font=ctk.CTkFont(family="Arial", size=12, weight="bold"),
            text_color=WHITE
        )
        self.pass_label.pack(pady=(10, 5), anchor="w", padx=15)

        self.pass_progress = ctk.CTkProgressBar(
            pass_frame,
            width=600,
            height=15,
            fg_color=GRAY_DARK,
            progress_color=GREEN
        )
        self.pass_progress.pack(pady=(0, 10), padx=15)
        self.pass_progress.set(0)

        # Statistics
        stats_frame = ctk.CTkFrame(self.dialog, fg_color=PURPLE_MEDIUM)
        stats_frame.pack(fill="x", padx=20, pady=(0, 10))

        stats_grid = ctk.CTkFrame(stats_frame, fg_color="transparent")
        stats_grid.pack(fill="x", padx=15, pady=10)

        # Speed
        speed_label = ctk.CTkLabel(
            stats_grid,
            text="Speed:",
            font=ctk.CTkFont(family="Arial", size=10, weight="bold"),
            text_color=GRAY_LIGHT
        )
        speed_label.grid(row=0, column=0, sticky="w", padx=(0, 10))

        self.speed_value = ctk.CTkLabel(
            stats_grid,
            text="0 MB/s",
            font=ctk.CTkFont(family="Courier", size=10),
            text_color=WHITE
        )
        self.speed_value.grid(row=0, column=1, sticky="w", padx=(0, 30))

        # Time remaining
        time_label = ctk.CTkLabel(
            stats_grid,
            text="ETA:",
            font=ctk.CTkFont(family="Arial", size=10, weight="bold"),
            text_color=GRAY_LIGHT
        )
        time_label.grid(row=0, column=2, sticky="w", padx=(0, 10))

        self.time_value = ctk.CTkLabel(
            stats_grid,
            text="Calculating...",
            font=ctk.CTkFont(family="Courier", size=10),
            text_color=WHITE
        )
        self.time_value.grid(row=0, column=3, sticky="w", padx=(0, 30))

        # Elapsed time
        elapsed_label = ctk.CTkLabel(
            stats_grid,
            text="Elapsed:",
            font=ctk.CTkFont(family="Arial", size=10, weight="bold"),
            text_color=GRAY_LIGHT
        )
        elapsed_label.grid(row=1, column=0, sticky="w", padx=(0, 10), pady=(5, 0))

        self.elapsed_value = ctk.CTkLabel(
            stats_grid,
            text="00:00:00",
            font=ctk.CTkFont(family="Courier", size=10),
            text_color=WHITE
        )
        self.elapsed_value.grid(row=1, column=1, sticky="w", padx=(0, 30), pady=(5, 0))

        # Verification status
        verify_label = ctk.CTkLabel(
            stats_grid,
            text="Verification:",
            font=ctk.CTkFont(family="Arial", size=10, weight="bold"),
            text_color=GRAY_LIGHT
        )
        verify_label.grid(row=1, column=2, sticky="w", padx=(0, 10), pady=(5, 0))

        self.verify_value = ctk.CTkLabel(
            stats_grid,
            text="Pending",
            font=ctk.CTkFont(family="Courier", size=10),
            text_color=WHITE
        )
        self.verify_value.grid(row=1, column=3, sticky="w", padx=(0, 30), pady=(5, 0))

        # Log output
        log_frame = ctk.CTkFrame(self.dialog, fg_color=PURPLE_DARK)
        log_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        log_label = ctk.CTkLabel(
            log_frame,
            text="Progress Log:",
            font=ctk.CTkFont(family="Arial", size=12, weight="bold"),
            text_color=WHITE
        )
        log_label.pack(pady=(10, 5), anchor="w", padx=15)

        self.log_text = ctk.CTkTextbox(
            log_frame,
            width=650,
            height=100,
            font=ctk.CTkFont(family="Courier", size=9),
            fg_color=GRAY_DARK,
            text_color=WHITE
        )
        self.log_text.pack(pady=(0, 15), padx=15)

        # Control buttons
        button_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        button_frame.pack(fill="x", padx=20, pady=(0, 20))

        self.cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel Wipe",
            width=120,
            height=35,
            font=ctk.CTkFont(family="Arial", size=12),
            fg_color=RED,
            hover_color="#CC4444",
            command=self.cancel_wipe
        )
        self.cancel_button.pack(side="right")

        self.pause_button = ctk.CTkButton(
            button_frame,
            text="Pause",
            width=100,
            height=35,
            font=ctk.CTkFont(family="Arial", size=12),
            fg_color=GRAY_DARK,
            hover_color="#666666",
            command=self.toggle_pause
        )
        self.pause_button.pack(side="right", padx=(0, 10))

    def update_progress(self, progress: WipeProgress):
        """Update progress display"""
        # Calculate overall progress
        device_progress = (self.current_device_index / len(self.devices))
        current_device_progress = (progress.bytes_written / progress.total_bytes) / len(self.devices)
        overall = device_progress + current_device_progress

        self.overall_progress.set(overall)

        # Update current pass progress
        if progress.total_bytes > 0:
            pass_progress = progress.bytes_written / progress.total_bytes
            self.pass_progress.set(pass_progress)

        # Update labels
        current_device = self.devices[self.current_device_index]
        device_text = f"Device {self.current_device_index + 1}/{len(self.devices)}: {current_device['device']} - {current_device['model']}"
        self.device_label.configure(text=device_text)

        pass_text = f"Pass {progress.current_pass}/{progress.total_passes}: {progress.pass_name}"
        self.pass_label.configure(text=pass_text)

        # Update statistics
        speed_mb = progress.bytes_per_second / (1024 * 1024)
        self.speed_value.configure(text=f"{speed_mb:.1f} MB/s")

        if progress.estimated_remaining > 0:
            eta_str = self._format_time(progress.estimated_remaining)
            self.time_value.configure(text=eta_str)

        elapsed_str = self._format_time(progress.elapsed_time)
        self.elapsed_value.configure(text=elapsed_str)

        if progress.verification_status != "pending":
            self.verify_value.configure(text=progress.verification_status.title())

        # Add log entry
        if hasattr(progress, 'last_log_time'):
            if time.time() - progress.last_log_time > 5:  # Log every 5 seconds
                self._add_log(f"Pass {progress.current_pass}: {pass_progress*100:.1f}% complete ({speed_mb:.1f} MB/s)")
                progress.last_log_time = time.time()
        else:
            progress.last_log_time = time.time()
            self._add_log(f"Started {progress.pass_name}")

        # Update display
        self.dialog.update()

    def _format_time(self, seconds: float) -> str:
        """Format time in seconds to HH:MM:SS"""
        if seconds < 0:
            return "Unknown"

        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def _add_log(self, message: str):
        """Add message to log"""
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"

        self.log_text.insert("end", log_entry)
        self.log_text.see("end")

    def cancel_wipe(self):
        """Cancel the wipe operation"""
        self.cancelled = True
        self._add_log("Wipe cancellation requested...")
        self.cancel_button.configure(text="Cancelling...", state="disabled")

    def toggle_pause(self):
        """Toggle pause/resume"""
        if self.pause_button.cget("text") == "Pause":
            self.pause_button.configure(text="Resume")
            self._add_log("Wipe paused")
        else:
            self.pause_button.configure(text="Pause")
            self._add_log("Wipe resumed")

    def on_close(self):
        """Handle dialog close"""
        if not self.cancelled:
            result = messagebox.askyesno(
                "Cancel Wipe?",
                "Are you sure you want to cancel the wipe operation?\n\nThis may leave devices in a partially wiped state.",
                parent=self.dialog
            )
            if result:
                self.cancel_wipe()

    def complete(self, success: bool, message: str = ""):
        """Mark operation as complete"""
        if success:
            self.header_label.configure(text="Wipe Completed Successfully!")
            self._add_log("All devices wiped successfully")
            self.cancel_button.configure(text="Close", fg_color=GREEN, state="normal")
        else:
            self.header_label.configure(text="Wipe Failed!")
            self._add_log(f"Wipe failed: {message}")
            self.cancel_button.configure(text="Close", fg_color=RED, state="normal")

        self.pause_button.configure(state="disabled")

class ObliteratorGUI:
    """Main Obliterator GUI application"""

    def __init__(self):
        self.config = AppConfig()
        self.detector = DeviceDetector()
        self.engine = WipingEngine()
        self.devices = []
        self.selected_devices = []

        # Initialize main window
        self.root = ctk.CTk()
        self.root.title("Obliterator - Secure Data Wiping")
        self.root.geometry(f"{self.config.window_width}x{self.config.window_height}")

        # Set window icon (if available)
        try:
            self.root.iconbitmap("/opt/obliterator/gui/obliterator-icon.ico")
        except:
            pass

        # Initialize splash screen
        self.splash = SplashScreen()
        self.initialize_application()

    def initialize_application(self):
        """Initialize application with splash screen"""
        self.splash.update_progress(0.1, "Loading configuration...")
        time.sleep(0.5)

        self.splash.update_progress(0.3, "Initializing GUI components...")
        self.create_main_interface()
        time.sleep(0.5)

        self.splash.update_progress(0.6, "Detecting storage devices...")
        self.refresh_devices()
        time.sleep(0.5)

        self.splash.update_progress(0.9, "Finalizing...")
        time.sleep(0.5)

        self.splash.update_progress(1.0, "Ready!")
        time.sleep(0.5)

        # Close splash and show main window
        self.splash.close()
        self.root.deiconify()

    def create_main_interface(self):
        """Create the main GUI interface"""
        # Hide main window during splash
        self.root.withdraw()

        # Configure grid weights
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)

        # Header frame
        self.create_header()

        # Main content frame
        main_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        main_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)

        # Device list frame
        self.create_device_list(main_frame)

        # Control frame
        self.create_controls(main_frame)

        # Status bar
        self.create_status_bar()

    def create_header(self):
        """Create application header"""
        header_frame = ctk.CTkFrame(self.root, fg_color=PURPLE_DARK, height=80)
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        header_frame.grid_propagate(False)

        # Title
        title_label = ctk.CTkLabel(
            header_frame,
            text="OBLITERATOR",
            font=ctk.CTkFont(family="Arial", size=28, weight="bold"),
            text_color=PURPLE_BRIGHT
        )
        title_label.pack(side="left", padx=20, pady=20)

        # Subtitle
        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="NIST SP 800-88r2 Compliant Secure Data Wiping",
            font=ctk.CTkFont(family="Arial", size=12),
            text_color=GRAY_LIGHT
        )
        subtitle_label.pack(side="left", padx=(0, 20), pady=20)

        # Refresh button
        refresh_button = ctk.CTkButton(
            header_frame,
            text="🔄 Refresh Devices",
            width=140,
            height=35,
            font=ctk.CTkFont(family="Arial", size=12),
            fg_color=PURPLE_ACCENT,
            hover_color=PURPLE_LIGHT,
            command=self.refresh_devices
        )
        refresh_button.pack(side="right", padx=20, pady=20)

    def create_device_list(self, parent):
        """Create device list display"""
        # Device list header
        list_header = ctk.CTkFrame(parent, fg_color=PURPLE_MEDIUM, height=40)
        list_header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        list_header.grid_propagate(False)

        header_label = ctk.CTkLabel(
            list_header,
            text="Detected Storage Devices",
            font=ctk.CTkFont(family="Arial", size=16, weight="bold"),
            text_color=WHITE
        )
        header_label.pack(side="left", padx=20, pady=10)

        # Device selection info
        self.selection_label = ctk.CTkLabel(
            list_header,
            text="No devices selected",
            font=ctk.CTkFont(family="Arial", size=12),
            text_color=GRAY_LIGHT
        )
        self.selection_label.pack(side="right", padx=20, pady=10)

        # Scrollable device list
        self.device_frame = ctk.CTkScrollableFrame(
            parent,
            fg_color=PURPLE_DARK,
            corner_radius=10
        )
        self.device_frame.grid(row=1, column=0, sticky="nsew")

    def create_controls(self, parent):
        """Create control panel"""
        control_frame = ctk.CTkFrame(parent, fg_color=PURPLE_MEDIUM, height=100)
        control_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        control_frame.grid_propagate(False)
        control_frame.grid_columnconfigure(1, weight=1)

        # Sanitization method selection
        method_label = ctk.CTkLabel(
            control_frame,
            text="Method:",
            font=ctk.CTkFont(family="Arial", size=12, weight="bold"),
            text_color=WHITE
        )
        method_label.grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")

        self.method_var = ctk.StringVar(value="clear")
        method_frame = ctk.CTkFrame(control_frame, fg_color="transparent")
        method_frame.grid(row=0, column=1, padx=(0, 20), pady=(15, 5), sticky="w")

        clear_radio = ctk.CTkRadioButton(
            method_frame,
            text="Clear (Single pass)",
            variable=self.method_var,
            value="clear",
            font=ctk.CTkFont(family="Arial", size=11),
            text_color=WHITE
        )
        clear_radio.pack(side="left", padx=(0, 20))

        purge_radio = ctk.CTkRadioButton(
            method_frame,
            text="Purge (Multi-pass secure)",
            variable=self.method_var,
            value="purge",
            font=ctk.CTkFont(family="Arial", size=11),
            text_color=WHITE
        )
        purge_radio.pack(side="left", padx=(0, 20))

        destroy_radio = ctk.CTkRadioButton(
            method_frame,
            text="Destroy (Physical destruction)",
            variable=self.method_var,
            value="destroy",
            font=ctk.CTkFont(family="Arial", size=11),
            text_color=WHITE
        )
        destroy_radio.pack(side="left")

        # Wipe button
        self.wipe_button = ctk.CTkButton(
            control_frame,
            text="🗑️ START WIPE",
            width=150,
            height=40,
            font=ctk.CTkFont(family="Arial", size=14, weight="bold"),
            fg_color=RED,
            hover_color="#CC4444",
            command=self.start_wipe,
            state="disabled"
        )
        self.wipe_button.grid(row=0, column=2, rowspan=2, padx=20, pady=15)

    def create_status_bar(self):
        """Create status bar"""
        self.status_frame = ctk.CTkFrame(self.root, fg_color=GRAY_DARK, height=30)
        self.status_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 20))
        self.status_frame.grid_propagate(False)

        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="Ready - Select devices to begin wiping",
            font=ctk.CTkFont(family="Arial", size=10),
            text_color=WHITE
        )
        self.status_label.pack(side="left", padx=15, pady=5)

    def refresh_devices(self):
        """Refresh device list"""
        self.update_status("Detecting devices...")

        # Clear existing device widgets
        for widget in self.device_frame.winfo_children():
            widget.destroy()

        # Detect devices in background
        def detect_devices():
            try:
                self.devices = self.detector.detect_all_devices()
                self.root.after(0, self.populate_device_list)
            except Exception as e:
                logger.error(f"Device detection failed: {e}")
                self.root.after(0, lambda: self.update_status(f"Error: {e}"))

        thread = threading.Thread(target=detect_devices, daemon=True)
        thread.start()

    def populate_device_list(self):
        """Populate device list with detected devices"""
        if not self.devices:
            no_devices_label = ctk.CTkLabel(
                self.device_frame,
                text="No storage devices detected",
                font=ctk.CTkFont(family="Arial", size=14),
                text_color=GRAY_LIGHT
            )
            no_devices_label.pack(pady=50)
            self.update_status("No devices detected")
            return

        self.device_checkboxes = []

        for i, device in enumerate(self.devices):
            device_widget = self.create_device_widget(device, i)
            device_widget.pack(fill="x", padx=10, pady=5)

        self.update_status(f"Detected {len(self.devices)} storage devices")
        self.update_selection()

    def create_device_widget(self, device: Dict, index: int):
        """Create widget for individual device"""
        # Main device frame
        device_frame = ctk.CTkFrame(self.device_frame, fg_color=PURPLE_LIGHT)

        # Checkbox for selection
        var = tk.BooleanVar()
        checkbox = ctk.CTkCheckBox(
            device_frame,
            text="",
            variable=var,
            width=20,
            command=self.update_selection
        )
        checkbox.pack(side="left", padx=(15, 10), pady=15)

        # Store checkbox reference
        self.device_checkboxes.append((var, device))

        # Device info frame
        info_frame = ctk.CTkFrame(device_frame, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, padx=(0, 15), pady=10)

        # Primary info (device, model, size)
        primary_text = f"{device['device']} - {device['model']} ({device['size_human']})"
        primary_label = ctk.CTkLabel(
            info_frame,
            text=primary_text,
            font=ctk.CTkFont(family="Arial", size=12, weight="bold"),
            text_color=WHITE,
            anchor="w"
        )
        primary_label.pack(fill="x", pady=(0, 2))

        # Secondary info (serial, type, status)
        secondary_parts = [
            f"S/N: {device['serial'][:15]}..." if len(device['serial']) > 15 else f"S/N: {device['serial']}",
            f"Type: {device['media_type']}",
            f"Status: {device['wipe_status']}"
        ]

        if device['mount_points']:
            secondary_parts.append(f"Mounted: {', '.join(device['mount_points'])}")

        if device['hpa_enabled']:
            secondary_parts.append("HPA detected")

        if device['dco_enabled']:
            secondary_parts.append("DCO detected")

        secondary_text = " | ".join(secondary_parts)
        secondary_label = ctk.CTkLabel(
            info_frame,
            text=secondary_text,
            font=ctk.CTkFont(family="Courier", size=10),
            text_color=GRAY_LIGHT,
            anchor="w"
        )
        secondary_label.pack(fill="x")

        # Disable checkbox if device is protected
        if device['wipe_status'] != 'Ready':
            checkbox.configure(state="disabled")
            device_frame.configure(fg_color=GRAY_DARK)

        return device_frame

    def update_selection(self):
        """Update selection status and enable/disable wipe button"""
        if not hasattr(self, 'device_checkboxes'):
            return

        self.selected_devices = []

        for var, device in self.device_checkboxes:
            if var.get() and device['wipe_status'] == 'Ready':
                self.selected_devices.append(device)

        count = len(self.selected_devices)

        if count == 0:
            self.selection_label.configure(text="No devices selected")
            self.wipe_button.configure(state="disabled")
        else:
            total_size = sum(device['size_bytes'] for device in self.selected_devices)
            size_text = self._format_size(total_size)
            self.selection_label.configure(text=f"{count} device(s) selected ({size_text})")
            self.wipe_button.configure(state="normal")

    def start_wipe(self):
        """Start the wipe operation"""
        if not self.selected_devices:
            messagebox.showwarning("No Selection", "Please select at least one device to wipe.")
            return

        method = self.method_var.get()

        # Show confirmation dialog
        confirm_dialog = ConfirmationDialog(self.root, self.selected_devices, method)
        if not confirm_dialog.show():
            return

        # Start wipe operation
        self.perform_wipe(method)

    def perform_wipe(self, method: str):
        """Perform the actual wipe operation"""
        # Create progress dialog
        progress_dialog = WipeProgressDialog(self.root, self.selected_devices)

        def wipe_thread():
            """Wipe operation in separate thread"""
            sanitization_method = SanitizationMethod(method)
            success = True
            error_message = ""

            try:
                # Set up progress callback
                def progress_callback(progress: WipeProgress):
                    self.root.after(0, lambda: progress_dialog.update_progress(progress))

                self.engine.set_progress_callback(progress_callback)

                # Wipe each selected device
                for i, device in enumerate(self.selected_devices):
                    if progress_dialog.cancelled:
                        break

                    progress_dialog.current_device_index = i

                    # Generate confirmation token for this device
                    device_name = os.path.basename(device['device']).upper()
                    confirm_token = f"OBLITERATE-{device_name}"

                    # Perform wipe
                    device_success = self.engine.wipe_device(
                        device['device'],
                        sanitization_method,
                        confirm_token,
                        dry_run=False
                    )

                    if not device_success:
                        success = False
                        error_message = f"Failed to wipe {device['device']}"
                        break

                # Update dialog with final result
                self.root.after(0, lambda: progress_dialog.complete(success, error_message))

            except Exception as e:
                logger.error(f"Wipe operation failed: {e}")
                error_message = str(e)
                self.root.after(0, lambda: progress_dialog.complete(False, error_message))

        # Start wipe thread
        thread = threading.Thread(target=wipe_thread, daemon=True)
        thread.start()

    def update_status(self, message: str):
        """Update status bar message"""
        self.status_label.configure(text=message)
        logger.info(message)

    def _format_size(self, size_bytes: int) -> str:
        """Format size in bytes to human readable format"""
        if size_bytes == 0:
            return "0 B"

        units = ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB']
        unit_index = 0
        size = float(size_bytes)

        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1

        if unit_index == 0:
            return f"{int(size)} {units[unit_index]}"
        else:
            return f"{size:.1f} {units[unit_index]}"

    def run(self):
        """Run the GUI application"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            logger.info("Application interrupted by user")
        except Exception as e:
            logger.error(f"Application error: {e}")
            messagebox.showerror("Error", f"Application error: {e}")

def main():
    """Main application entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Obliterator GUI Application')
    parser.add_argument('--test', action='store_true', help='Run in test mode')
    parser.add_argument('--config', help='Configuration file path')
    parser.add_argument('--verbose', action='store_true', help='Verbose logging')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Check if running as root (required for device access)
    if os.geteuid() != 0 and not args.test:
        print("Error: Obliterator requires root privileges for device access.")
        print("Please run with: sudo python3 obliterator-gui.py")
        sys.exit(1)

    try:
        app = ObliteratorGUI()
        app.run()
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        print(f"Failed to start Obliterator: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

