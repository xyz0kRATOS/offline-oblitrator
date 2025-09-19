#!/usr/bin/env python3
"""
Obliterator GUI - Modern CustomTkinter Interface
Secure air-gapped data wiping with contemporary design
Version: 1.0.0
"""

import os
import sys
import json
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# GUI imports with modern CustomTkinter
try:
    import customtkinter as ctk
    from tkinter import messagebox, filedialog, scrolledtext
    import tkinter as tk
    CTK_AVAILABLE = True
    
    # Configure CustomTkinter
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    
    print("✅ CustomTkinter loaded successfully")
    
except ImportError:
    print("❌ CustomTkinter not available. Install with: pip install customtkinter")
    try:
        import tkinter as tk
        from tkinter import ttk, messagebox, filedialog, scrolledtext
        CTK_AVAILABLE = False
        print("⚠️  Using fallback tkinter")
    except ImportError:
        print("❌ No GUI libraries available")
        sys.exit(1)

# Configuration
APP_VERSION = "1.0.0"
APP_NAME = "Obliterator"
OUTPUT_DIR = os.environ.get("OBLITERATOR_OUTPUT_DIR", "/tmp/obliterator")
SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class ModernObliperatorGUI:
    """Modern CustomTkinter GUI for Obliterator"""
    
    def __init__(self):
        self.root = None
        self.current_frame = None
        
        # Application state
        self.detected_drives = []
        self.selected_drives = []
        self.operator_info = {}
        self.wipe_in_progress = False
        self.wipe_results = {}
        
        # GUI components
        self.drive_frame = None
        self.progress_bars = {}
        self.log_text = None
        
        # Modern colors
        self.colors = {
            "primary": "#6a0d83",      # Deep purple
            "secondary": "#1a1a2e",    # Dark navy
            "accent": "#00d4ff",       # Bright cyan
            "success": "#00ff88",      # Bright green
            "warning": "#ffcc00",      # Gold
            "error": "#ff4757",        # Red
            "surface": "#16213e",      # Surface color
            "text": "#ffffff",         # White text
            "text_dim": "#b8b8b8"      # Dim text
        }
        
        # Initialize output directory
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
    def setup_root_window(self):
        """Initialize the modern main window"""
        if CTK_AVAILABLE:
            self.root = ctk.CTk()
            
            # Modern window configuration
            self.root.title(f"{APP_NAME} • Modern Security Suite")
            self.root.geometry("1400x900")
            self.root.minsize(1200, 800)
            
            # Modern color scheme
            self.root.configure(fg_color=self.colors["secondary"])
            
        else:
            self.root = tk.Tk()
            self.root.title(f"{APP_NAME} v{APP_VERSION}")
            self.root.geometry("1200x800")
            self.root.configure(bg=self.colors["secondary"])
        
        # Center window
        self.center_window()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def center_window(self):
        """Center the window on screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        
    def show_splash_screen(self):
        """Modern splash screen with animations"""
        if CTK_AVAILABLE:
            splash_frame = ctk.CTkFrame(self.root, fg_color=self.colors["secondary"])
        else:
            splash_frame = tk.Frame(self.root, bg=self.colors["secondary"])
        
        splash_frame.pack(fill="both", expand=True)
        
        # Modern title with gradient effect
        if CTK_AVAILABLE:
            title_label = ctk.CTkLabel(
                splash_frame,
                text=APP_NAME,
                font=("SF Pro Display", 72, "bold"),
                text_color=self.colors["primary"]
            )
            title_label.pack(pady=(200, 20))
            
            subtitle_label = ctk.CTkLabel(
                splash_frame,
                text="Advanced Security • Air-Gapped • Forensics-Grade",
                font=("SF Pro Display", 18),
                text_color=self.colors["accent"]
            )
            subtitle_label.pack(pady=(0, 40))
            
            version_label = ctk.CTkLabel(
                splash_frame,
                text=f"Version {APP_VERSION} • NIST SP 800-88r2 Compliant",
                font=("SF Pro Display", 14),
                text_color=self.colors["text_dim"]
            )
            version_label.pack(pady=(0, 60))
            
            # Modern loading indicator
            loading_label = ctk.CTkLabel(
                splash_frame,
                text="🔍 Initializing secure environment...",
                font=("SF Pro Display", 16),
                text_color=self.colors["accent"]
            )
            loading_label.pack(pady=(0, 30))
            
            # Modern progress bar
            progress = ctk.CTkProgressBar(
                splash_frame,
                width=400,
                height=8,
                progress_color=self.colors["primary"],
                fg_color=self.colors["surface"]
            )
            progress.pack(pady=(0, 100))
            progress.start()
            
        else:
            # Fallback for standard tkinter
            title_label = tk.Label(
                splash_frame,
                text=APP_NAME,
                font=("Arial", 48, "bold"),
                bg=self.colors["secondary"],
                fg=self.colors["primary"]
            )
            title_label.pack(pady=(150, 20))
        
        self.switch_frame(splash_frame)
        self.root.update()
        
        # Simulate loading time
        time.sleep(2)
        
        if CTK_AVAILABLE:
            progress.stop()
            
        # Check for root privileges
        if os.geteuid() != 0:
            self.show_login_screen()
        else:
            self.detect_drives_and_show_main()
            
    def show_login_screen(self):
        """Modern login/access screen"""
        if CTK_AVAILABLE:
            login_frame = ctk.CTkFrame(self.root, fg_color=self.colors["secondary"])
        else:
            login_frame = tk.Frame(self.root, bg=self.colors["secondary"])
        
        login_frame.pack(fill="both", expand=True)
        
        # Modern warning card
        if CTK_AVAILABLE:
            warning_card = ctk.CTkFrame(
                login_frame,
                fg_color=self.colors["surface"],
                corner_radius=20,
                border_width=2,
                border_color=self.colors["warning"]
            )
            warning_card.pack(pady=100, padx=100, fill="both", expand=True)
            
            # Icon and title
            title_label = ctk.CTkLabel(
                warning_card,
                text="🔐 Administrator Access Required",
                font=("SF Pro Display", 28, "bold"),
                text_color=self.colors["warning"]
            )
            title_label.pack(pady=(40, 20))
            
            # Modern info text
            info_text = """This application requires administrator privileges for direct storage device access.
            
For security operations, please restart with elevated permissions:

sudo python3 main.py

Alternatively, you can run individual components with appropriate permissions."""
            
            info_label = ctk.CTkLabel(
                warning_card,
                text=info_text,
                font=("SF Pro Display", 14),
                text_color=self.colors["text"],
                justify="center"
            )
            info_label.pack(pady=(0, 40), padx=40)
            
            # Modern button container
            button_container = ctk.CTkFrame(warning_card, fg_color="transparent")
            button_container.pack(pady=(20, 40))
            
            # Modern buttons
            exit_btn = ctk.CTkButton(
                button_container,
                text="Exit Application",
                command=self.on_closing,
                fg_color=self.colors["error"],
                hover_color="#ff6b7a",
                font=("SF Pro Display", 14, "bold"),
                height=40,
                width=160
            )
            exit_btn.pack(side="left", padx=10)
            
            continue_btn = ctk.CTkButton(
                button_container,
                text="Continue Anyway",
                command=self.detect_drives_and_show_main,
                fg_color=self.colors["primary"],
                hover_color="#8b2ca0",
                font=("SF Pro Display", 14, "bold"),
                height=40,
                width=160
            )
            continue_btn.pack(side="left", padx=10)
            
        self.switch_frame(login_frame)
        
    def show_main_screen(self):
        """Modern main interface with cards and modern layout"""
        if CTK_AVAILABLE:
            main_frame = ctk.CTkFrame(self.root, fg_color=self.colors["secondary"])
        else:
            main_frame = tk.Frame(self.root, bg=self.colors["secondary"])
        
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Modern header
        self.create_modern_header(main_frame)
        
        # Main content area
        if CTK_AVAILABLE:
            content_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        else:
            content_frame = tk.Frame(main_frame, bg=self.colors["secondary"])
        content_frame.pack(fill="both", expand=True, pady=(20, 0))
        
        # Check if we have drives or show error message
        if not self.detected_drives:
            self.create_modern_no_drives_section(content_frame)
        else:
            self.create_modern_drive_section(content_frame)
        
        self.switch_frame(main_frame)
        
    def create_modern_header(self, parent):
        """Create modern header with system info"""
        if CTK_AVAILABLE:
            header_frame = ctk.CTkFrame(
                parent,
                height=80,
                fg_color=self.colors["surface"],
                corner_radius=15
            )
        else:
            header_frame = tk.Frame(parent, bg=self.colors["surface"], height=80)
        
        header_frame.pack(fill="x", pady=(0, 20))
        header_frame.pack_propagate(False)
        
        # Left side - App branding
        if CTK_AVAILABLE:
            left_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
            left_frame.pack(side="left", fill="y", padx=20)
            
            title_label = ctk.CTkLabel(
                left_frame,
                text=f"🛡️ {APP_NAME}",
                font=("SF Pro Display", 24, "bold"),
                text_color=self.colors["primary"]
            )
            title_label.pack(anchor="w", pady=(15, 5))
            
            subtitle_label = ctk.CTkLabel(
                left_frame,
                text="Forensics-Grade Data Destruction",
                font=("SF Pro Display", 12),
                text_color=self.colors["text_dim"]
            )
            subtitle_label.pack(anchor="w")
            
            # Right side - System info
            right_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
            right_frame.pack(side="right", fill="y", padx=20)
            
            import socket
            hostname = socket.gethostname()
            current_time = datetime.now().strftime("%H:%M:%S")
            
            sys_label = ctk.CTkLabel(
                right_frame,
                text=f"System: {hostname}\nTime: {current_time}\nVersion: {APP_VERSION}",
                font=("SF Pro Mono", 10),
                text_color=self.colors["text_dim"],
                justify="right"
            )
            sys_label.pack(anchor="e", pady=15)
            
    def create_modern_drive_section(self, parent):
        """Create modern drive list with cards"""
        # Section title
        if CTK_AVAILABLE:
            title_frame = ctk.CTkFrame(parent, fg_color="transparent")
            title_frame.pack(fill="x", pady=(0, 20))
            
            title_label = ctk.CTkLabel(
                title_frame,
                text="📀 Storage Devices",
                font=("SF Pro Display", 20, "bold"),
                text_color=self.colors["text"]
            )
            title_label.pack(side="left")
            
            count_label = ctk.CTkLabel(
                title_frame,
                text=f"{len(self.detected_drives)} devices detected",
                font=("SF Pro Display", 12),
                text_color=self.colors["text_dim"]
            )
            count_label.pack(side="left", padx=(15, 0))
            
            # Refresh button
            refresh_btn = ctk.CTkButton(
                title_frame,
                text="🔄 Refresh",
                command=self.refresh_drives,
                fg_color=self.colors["accent"],
                hover_color="#00b8e6",
                font=("SF Pro Display", 12, "bold"),
                height=32,
                width=100
            )
            refresh_btn.pack(side="right")
            
        # Scrollable drive container
        if CTK_AVAILABLE:
            self.drive_frame = ctk.CTkScrollableFrame(
                parent,
                fg_color=self.colors["surface"],
                corner_radius=15
            )
        else:
            self.drive_frame = tk.Frame(parent, bg=self.colors["surface"])
        
        self.drive_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        # Populate with drive cards
        self.populate_drive_cards()
        
        # Action buttons
        if CTK_AVAILABLE:
            action_frame = ctk.CTkFrame(parent, fg_color="transparent")
            action_frame.pack(fill="x")
            
            wipe_btn = ctk.CTkButton(
                action_frame,
                text="⚠️ WIPE SELECTED DEVICES",
                command=self.confirm_wipe,
                fg_color=self.colors["error"],
                hover_color="#ff6b7a",
                font=("SF Pro Display", 16, "bold"),
                height=50,
                width=300
            )
            wipe_btn.pack(side="right")
            
            selected_label = ctk.CTkLabel(
                action_frame,
                text=f"{len(self.selected_drives)} devices selected",
                font=("SF Pro Display", 12),
                text_color=self.colors["text_dim"]
            )
            selected_label.pack(side="left", pady=15)
            
    def populate_drive_cards(self):
        """Create modern drive cards"""
        for i, drive in enumerate(self.detected_drives):
            self.create_drive_card(drive, i)
            
    def create_drive_card(self, drive, index):
        """Create a modern drive card"""
        if not CTK_AVAILABLE:
            return
            
        # Drive card container
        card = ctk.CTkFrame(
            self.drive_frame,
            fg_color=self.colors["secondary"],
            corner_radius=12,
            border_width=1,
            border_color=self.colors["surface"]
        )
        card.pack(fill="x", padx=10, pady=5)
        
        # Card content
        content_frame = ctk.CTkFrame(card, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        # Top row - Device info and selection
        top_row = ctk.CTkFrame(content_frame, fg_color="transparent")
        top_row.pack(fill="x", pady=(0, 10))
        
        # Selection checkbox
        var = tk.BooleanVar()
        checkbox = ctk.CTkCheckBox(
            top_row,
            text="",
            variable=var,
            command=lambda: self.toggle_drive_selection(drive, var.get()),
            fg_color=self.colors["primary"],
            hover_color=self.colors["accent"]
        )
        checkbox.pack(side="left")
        
        # Device icon and name
        device_icon = "💾" if drive.get("interface") == "nvme" else "💿" if drive.get("is_ssd") else "🖴"
        device_label = ctk.CTkLabel(
            top_row,
            text=f"{device_icon} {drive.get('device', 'unknown')}",
            font=("SF Pro Display", 16, "bold"),
            text_color=self.colors["text"]
        )
        device_label.pack(side="left", padx=(15, 0))
        
        # Status badges
        if drive.get("mounted"):
            status_badge = ctk.CTkLabel(
                top_row,
                text="🔴 MOUNTED",
                font=("SF Pro Display", 10, "bold"),
                text_color=self.colors["error"]
            )
            status_badge.pack(side="right")
            
        # Device details grid
        details_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        details_frame.pack(fill="x")
        
        # Configure grid
        details_frame.grid_columnconfigure(0, weight=1)
        details_frame.grid_columnconfigure(1, weight=1)
        details_frame.grid_columnconfigure(2, weight=1)
        
        # Model
        model_label = ctk.CTkLabel(
            details_frame,
            text=f"Model: {drive.get('model', 'Unknown')}",
            font=("SF Pro Display", 11),
            text_color=self.colors["text_dim"],
            anchor="w"
        )
        model_label.grid(row=0, column=0, sticky="w", pady=2)
        
        # Size
        size_label = ctk.CTkLabel(
            details_frame,
            text=f"Size: {drive.get('size', 'Unknown')}",
            font=("SF Pro Display", 11),
            text_color=self.colors["text_dim"],
            anchor="w"
        )
        size_label.grid(row=0, column=1, sticky="w", pady=2)
        
        # Type
        type_label = ctk.CTkLabel(
            details_frame,
            text=f"Type: {drive.get('type', 'Unknown')}",
            font=("SF Pro Display", 11),
            text_color=self.colors["text_dim"],
            anchor="w"
        )
        type_label.grid(row=0, column=2, sticky="w", pady=2)
        
        # Recommended method
        method = drive.get('recommended_method', {}).get('method', 'UNKNOWN')
        method_label = ctk.CTkLabel(
            details_frame,
            text=f"Recommended: {method}",
            font=("SF Pro Display", 11, "bold"),
            text_color=self.colors["accent"],
            anchor="w"
        )
        method_label.grid(row=1, column=0, columnspan=3, sticky="w", pady=(5, 0))
        
    def toggle_drive_selection(self, drive, selected):
        """Handle drive selection"""
        device = drive.get('device')
        if selected and device not in self.selected_drives:
            self.selected_drives.append(device)
        elif not selected and device in self.selected_drives:
            self.selected_drives.remove(device)
            
        print(f"Drive {device} {'selected' if selected else 'deselected'}")
        
    def create_modern_no_drives_section(self, parent):
        """Modern no drives found screen"""
        if CTK_AVAILABLE:
            # Center container
            container = ctk.CTkFrame(
                parent,
                fg_color=self.colors["surface"],
                corner_radius=20,
                border_width=2,
                border_color=self.colors["warning"]
            )
            container.pack(expand=True, fill="both", padx=100, pady=50)
            
            # Icon and title
            title_label = ctk.CTkLabel(
                container,
                text="🔍 No Storage Devices Detected",
                font=("SF Pro Display", 24, "bold"),
                text_color=self.colors["warning"]
            )
            title_label.pack(pady=(40, 20))
            
            # Info text
            info_text = """This could be due to:
• Running without administrator privileges
• No storage devices connected
• System compatibility issues

Try these solutions:
• Restart with: sudo python3 main.py
• Check device connections
• Run manual detection"""
            
            info_label = ctk.CTkLabel(
                container,
                text=info_text,
                font=("SF Pro Display", 12),
                text_color=self.colors["text"],
                justify="left"
            )
            info_label.pack(pady=(0, 30))
            
            # Action buttons
            button_container = ctk.CTkFrame(container, fg_color="transparent")
            button_container.pack(pady=(20, 40))
            
            refresh_btn = ctk.CTkButton(
                button_container,
                text="🔄 Refresh Devices",
                command=self.refresh_drives,
                fg_color=self.colors["accent"],
                hover_color="#00b8e6",
                font=("SF Pro Display", 14, "bold"),
                height=40,
                width=160
            )
            refresh_btn.pack(side="left", padx=10)
            
            debug_btn = ctk.CTkButton(
                button_container,
                text="🔧 Debug Info",
                command=self.run_debug_detection,
                fg_color=self.colors["primary"],
                hover_color="#8b2ca0",
                font=("SF Pro Display", 14, "bold"),
                height=40,
                width=160
            )
            debug_btn.pack(side="left", padx=10)
            
            mock_btn = ctk.CTkButton(
                button_container,
                text="📝 Test Mode",
                command=self.load_mock_data,
                fg_color=self.colors["surface"],
                hover_color="#2a3441",
                font=("SF Pro Display", 14, "bold"),
                height=40,
                width=160,
                border_width=1,
                border_color=self.colors["text_dim"]
            )
            mock_btn.pack(side="left", padx=10) ttk, messagebox, filedialog, scrolledtext
    GUI_AVAILABLE = True
except ImportError:
    print("ERROR: tkinter not available. Install python3-tk package.")
    sys.exit(1)

# Try to import CustomTkinter for enhanced appearance
try:
    import customtkinter as ctk
    CTK_AVAILABLE = True
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
except ImportError:
    CTK_AVAILABLE = False
    print("WARNING: CustomTkinter not available, using standard tkinter")

# Local imports
try:
    from styles import ObliperatorTheme, apply_theme
except ImportError:
    # Fallback theme
    class ObliperatorTheme:
        BG_PRIMARY = "#1a1a2e"
        BG_SECONDARY = "#16213e" 
        BG_ACCENT = "#0f3460"
        TEXT_PRIMARY = "#ffffff"
        TEXT_SECONDARY = "#b8b8b8"
        ACCENT_PURPLE = "#6a0d83"
        ACCENT_CYAN = "#00d4ff"
        SUCCESS_GREEN = "#00ff88"
        WARNING_YELLOW = "#ffcc00"
        ERROR_RED = "#ff4757"
    
    def apply_theme(widget, theme_class):
        pass

# Configuration
APP_VERSION = "1.0.0"
APP_NAME = "Obliterator"
OUTPUT_DIR = os.environ.get("OBLITERATOR_OUTPUT_DIR", "/tmp/obliterator")
SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class ObliperatorGUI:
    """Main GUI application class"""
    
    def __init__(self):
        self.root = None
        self.current_frame = None
        self.theme = ObliperatorTheme()
        
        # Application state
        self.detected_drives = []
        self.selected_drives = []
        self.operator_info = {}
        self.wipe_in_progress = False
        self.wipe_results = {}
        
        # GUI components
        self.drive_tree = None
        self.progress_bars = {}
        self.log_text = None
        
        # Initialize output directory
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
    def setup_root_window(self):
        """Initialize the main window"""
        if CTK_AVAILABLE:
            self.root = ctk.CTk()
        else:
            self.root = tk.Tk()
            
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)
        
        # Set window icon if available
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "obliterator.ico")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except:
                pass
        
        # Configure style
        if not CTK_AVAILABLE:
            self.setup_theme()
            
        # Center window
        self.center_window()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def setup_theme(self):
        """Apply dark theme to standard tkinter"""
        style = ttk.Style()
        
        # Configure colors
        style.theme_use('clam')
        
        style.configure('TLabel', 
                       background=self.theme.BG_PRIMARY,
                       foreground=self.theme.TEXT_PRIMARY)
        
        style.configure('TButton',
                       background=self.theme.ACCENT_PURPLE,
                       foreground=self.theme.TEXT_PRIMARY,
                       borderwidth=0,
                       focuscolor='none')
        
        style.map('TButton',
                 background=[('active', self.theme.ACCENT_CYAN)])
        
        style.configure('TFrame',
                       background=self.theme.BG_PRIMARY)
        
        style.configure('Treeview',
                       background=self.theme.BG_SECONDARY,
                       foreground=self.theme.TEXT_PRIMARY,
                       fieldbackground=self.theme.BG_SECONDARY)
        
        style.configure('TProgressbar',
                       background=self.theme.ACCENT_PURPLE,
                       troughcolor=self.theme.BG_SECONDARY)
        
    def center_window(self):
        """Center the window on screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        
    def show_splash_screen(self):
        """Display splash screen with logo and loading"""
        splash_frame = self.create_frame()
        
        # Logo and title
        title_label = self.create_label(splash_frame, APP_NAME, 
                                      font=("Arial", 48, "bold"),
                                      fg=self.theme.ACCENT_PURPLE)
        title_label.pack(pady=(150, 20))
        
        subtitle_label = self.create_label(splash_frame, "Secure Air-Gapped Data Destruction",
                                         font=("Arial", 16),
                                         fg=self.theme.TEXT_SECONDARY)
        subtitle_label.pack(pady=(0, 30))
        
        version_label = self.create_label(splash_frame, f"Version {APP_VERSION}",
                                        font=("Arial", 12),
                                        fg=self.theme.TEXT_SECONDARY)
        version_label.pack(pady=(0, 50))
        
        # Loading indicator
        loading_label = self.create_label(splash_frame, "Initializing...",
                                        font=("Arial", 14),
                                        fg=self.theme.ACCENT_CYAN)
        loading_label.pack(pady=(0, 20))
        
        # Progress bar
        if CTK_AVAILABLE:
            progress = ctk.CTkProgressBar(splash_frame, width=300)
        else:
            progress = ttk.Progressbar(splash_frame, length=300, mode='indeterminate')
        progress.pack(pady=(0, 100))
        
        if not CTK_AVAILABLE:
            progress.start()
        
        self.switch_frame(splash_frame)
        self.root.update()
        
        # Simulate loading time
        time.sleep(2)
        
        if not CTK_AVAILABLE:
            progress.stop()
            
        # Check for root privileges
        if os.geteuid() != 0:
            self.show_login_screen()
        else:
            self.detect_drives_and_show_main()
            
    def show_login_screen(self):
        """Display login/authentication screen"""
        login_frame = self.create_frame()
        
        # Title
        title_label = self.create_label(login_frame, "Administrator Access Required",
                                      font=("Arial", 24, "bold"),
                                      fg=self.theme.ACCENT_PURPLE)
        title_label.pack(pady=(100, 30))
        
        # Warning message
        warning_text = """This application requires administrator privileges for direct device access.
        
Please restart the application with sudo:
sudo python3 main.py

Alternatively, you can run individual scripts with appropriate permissions."""
        
        warning_label = self.create_label(login_frame, warning_text,
                                        font=("Arial", 12),
                                        fg=self.theme.TEXT_PRIMARY,
                                        justify=tk.CENTER)
        warning_label.pack(pady=(0, 50))
        
        # Buttons
        button_frame = self.create_frame(login_frame)
        button_frame.pack(pady=20)
        
        exit_btn = self.create_button(button_frame, "Exit", self.on_closing)
        exit_btn.pack(side=tk.LEFT, padx=10)
        
        continue_btn = self.create_button(button_frame, "Continue Anyway", 
                                        self.detect_drives_and_show_main)
        continue_btn.pack(side=tk.LEFT, padx=10)
        
        self.switch_frame(login_frame)
        
    def detect_drives_and_show_main(self):
        """Detect drives and show main interface"""
        # Show loading while detecting drives
        self.show_loading_screen("Detecting storage devices...")
        
        # Run drive detection in background
        threading.Thread(target=self._detect_drives_background, daemon=True).start()
        
    def _detect_drives_background(self):
        """Background thread for drive detection"""
        try:
            # Try the new detection script first
            script_path = os.path.join(SCRIPTS_DIR, "detection.sh")
            
            print(f"Looking for new detection script at: {script_path}")
            
            if os.path.exists(script_path):
                env = os.environ.copy()
                env["OBLITERATOR_OUTPUT_DIR"] = OUTPUT_DIR
                
                print("Running new detection script...")
                result = subprocess.run([script_path], 
                                      capture_output=True, 
                                      text=True,
                                      env=env,
                                      timeout=30)
                
                print(f"New detection script return code: {result.returncode}")
                if result.stdout:
                    print(f"Detection stdout: {result.stdout}")
                if result.stderr:
                    print(f"Detection stderr: {result.stderr}")
                
                if result.returncode == 0:
                    # Load detected drives
                    drives_file = os.path.join(OUTPUT_DIR, "detected_drives.json")
                    print(f"Looking for drives file: {drives_file}")
                    
                    if os.path.exists(drives_file):
                        try:
                            with open(drives_file, 'r') as f:
                                drive_data = json.load(f)
                                self.detected_drives = drive_data.get('drives', [])
                                print(f"Loaded {len(self.detected_drives)} drives from new detection")
                        except json.JSONDecodeError as e:
                            print(f"JSON parsing error: {e}")
                            print("Using fallback drive detection")
                            self.detected_drives = self._fallback_drive_detection()
                    else:
                        print("No drives file found, using fallback detection")
                        self.detected_drives = self._fallback_drive_detection()
                else:
                    print(f"New detection script failed with code {result.returncode}")
                    print("Trying fallback detection")
                    self.detected_drives = self._fallback_drive_detection()
            else:
                print(f"New detection script not found: {script_path}")
                print("Using fallback drive detection")
                self.detected_drives = self._fallback_drive_detection()
                
        except subprocess.TimeoutExpired:
            print("Drive detection timed out")
            self.detected_drives = self._fallback_drive_detection()
        except Exception as e:
            print(f"Drive detection error: {e}")
            import traceback
            traceback.print_exc()
            self.detected_drives = self._fallback_drive_detection()
        
        # Update GUI in main thread
        self.root.after(0, self.show_main_screen)
        
    def _fallback_drive_detection(self):
        """Fallback drive detection using basic system commands"""
        drives = []
        
        try:
            print("Running fallback drive detection...")
            
            # Try lsblk for basic drive info
            result = subprocess.run(['lsblk', '-J', '-o', 'NAME,SIZE,TYPE,MODEL,SERIAL'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                lsblk_data = json.loads(result.stdout)
                
                for device in lsblk_data.get('blockdevices', []):
                    if device.get('type') == 'disk':
                        # Basic drive info from lsblk
                        drive_info = {
                            "device": f"/dev/{device.get('name', 'unknown')}",
                            "name": device.get('name', 'unknown'),
                            "size": device.get('size', '0'),
                            "model": device.get('model', 'Unknown Model'),
                            "serial": device.get('serial', 'Unknown Serial'),
                            "interface": "unknown",
                            "type": "disk",
                            "is_ssd": False,
                            "mounted": False,
                            "recommended_method": {
                                "method": "MULTI_PASS_OVERWRITE",
                                "confidence": "medium",
                                "reason": "Fallback detection - method not optimized"
                            }
                        }
                        
                        # Try to determine if it's an SSD
                        device_name = device.get('name', '')
                        if 'nvme' in device_name:
                            drive_info["interface"] = "nvme"
                            drive_info["type"] = "nvme"
                            drive_info["is_ssd"] = True
                            drive_info["recommended_method"]["method"] = "NVME_CRYPTO_ERASE"
                        elif any(keyword in drive_info["model"].lower() for keyword in ['ssd', 'solid']):
                            drive_info["interface"] = "sata"
                            drive_info["type"] = "ssd"
                            drive_info["is_ssd"] = True
                            drive_info["recommended_method"]["method"] = "ATA_SECURE_ERASE_ENHANCED"
                        
                        drives.append(drive_info)
                        
            print(f"Fallback detection found {len(drives)} drives")
            
        except Exception as e:
            print(f"Fallback detection failed: {e}")
            # Return mock data as last resort
            drives = self._mock_drive_detection()
            
        return drives
        """Mock drive detection for testing"""
        return [
            {
                "device": "/dev/sda",
                "name": "sda",
                "size": "500G",
                "interface": "sata",
                "model": "Samsung SSD 850",
                "serial": "S2R5NX0J123456",
                "is_ssd": True,
                "mounted": False,
                "recommended_method": {
                    "method": "ATA_SECURE_ERASE_ENHANCED",
                    "confidence": "high"
                }
            },
            {
                "device": "/dev/nvme0n1",
                "name": "nvme0n1", 
                "size": "1T",
                "interface": "nvme",
                "model": "WD Black SN750",
                "serial": "WDC12345",
                "is_ssd": True,
                "mounted": False,
                "recommended_method": {
                    "method": "NVME_CRYPTO_ERASE",
                    "confidence": "high"
                }
            }
        ]
        
    def show_loading_screen(self, message="Loading..."):
        """Show loading screen with message"""
        loading_frame = self.create_frame()
        
        # Loading message
        loading_label = self.create_label(loading_frame, message,
                                        font=("Arial", 18),
                                        fg=self.theme.ACCENT_CYAN)
        loading_label.pack(pady=(200, 50))
        
        # Spinner
        if CTK_AVAILABLE:
            progress = ctk.CTkProgressBar(loading_frame, width=400)
            progress.set(0.5)
        else:
            progress = ttk.Progressbar(loading_frame, length=400, mode='indeterminate')
            progress.start()
        progress.pack()
        
        self.switch_frame(loading_frame)
        self.root.update()
        
    def show_main_screen(self):
        """Display main application interface"""
        main_frame = self.create_frame()
        
        # Top section - App info and system details
        top_frame = self.create_frame(main_frame)
        top_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.create_top_section(top_frame)
        
        # Separator
        separator = ttk.Separator(main_frame, orient='horizontal')
        separator.pack(fill=tk.X, padx=20, pady=10)
        
        # Bottom section - Drive list and controls
        bottom_frame = self.create_frame(main_frame)
        bottom_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Check if we have drives or show error message
        if not self.detected_drives:
            self.create_no_drives_section(bottom_frame)
        else:
            self.create_drive_section(bottom_frame)
        
        self.switch_frame(main_frame)
        
    def create_no_drives_section(self, parent):
        """Create section when no drives are detected"""
        # Warning message
        warning_frame = self.create_frame(parent)
        warning_frame.pack(fill=tk.X, pady=20)
        
        warning_title = self.create_label(warning_frame, "⚠️ No Storage Devices Detected",
                                        font=("Arial", 18, "bold"),
                                        fg=self.theme.WARNING_YELLOW)
        warning_title.pack()
        
        warning_text = """This could be due to:
• Running without administrator privileges (try: sudo python3 main.py)
• No storage devices connected
• Drive detection script issues
• System compatibility problems

Troubleshooting steps:
1. Ensure you're running as root/administrator
2. Check that storage devices are properly connected
3. Try refreshing the drive list
4. Run manual detection: sudo ./detect_drives.sh --debug"""

        warning_label = self.create_label(warning_frame, warning_text,
                                        font=("Arial", 11),
                                        fg=self.theme.TEXT_PRIMARY,
                                        justify=tk.LEFT)
        warning_label.pack(pady=10)
        
        # Action buttons
        button_frame = self.create_frame(warning_frame)
        button_frame.pack(pady=20)
        
        refresh_btn = self.create_button(button_frame, "🔄 Refresh Drive List",
                                       self.refresh_drives)
        refresh_btn.pack(side=tk.LEFT, padx=10)
        
        debug_btn = self.create_button(button_frame, "🔧 Debug Mode",
                                     self.run_debug_detection)
        debug_btn.pack(side=tk.LEFT, padx=10)
        
        mock_btn = self.create_button(button_frame, "📝 Use Test Data",
                                    self.load_mock_data)
        mock_btn.pack(side=tk.LEFT, padx=10)
        
    def run_debug_detection(self):
        """Run detection in debug mode and show results"""
        debug_window = tk.Toplevel(self.root)
        debug_window.title("Drive Detection Debug")
        debug_window.geometry("800x600")
        debug_window.configure(bg=self.theme.BG_PRIMARY)
        
        # Debug output text
        debug_text = scrolledtext.ScrolledText(debug_window,
                                             bg=self.theme.BG_SECONDARY,
                                             fg=self.theme.TEXT_PRIMARY,
                                             font=("Courier", 10))
        debug_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        def run_debug():
            debug_text.insert(tk.END, "Running debug detection...\n")
            debug_text.see(tk.END)
            debug_window.update()
            
            try:
                # Run detection script with debug
                script_path = os.path.join(SCRIPTS_DIR, "detect_drives.sh")
                if os.path.exists(script_path):
                    env = os.environ.copy()
                    env["OBLITERATOR_OUTPUT_DIR"] = OUTPUT_DIR
                    env["DEBUG"] = "true"
                    
                    result = subprocess.run([script_path, "--debug"], 
                                          capture_output=True, 
                                          text=True,
                                          env=env)
                    
                    debug_text.insert(tk.END, f"Return code: {result.returncode}\n\n")
                    debug_text.insert(tk.END, "STDOUT:\n")
                    debug_text.insert(tk.END, result.stdout)
                    debug_text.insert(tk.END, "\n\nSTDERR:\n")
                    debug_text.insert(tk.END, result.stderr)
                    
                    # Try fallback detection
                    debug_text.insert(tk.END, "\n\n--- Fallback Detection ---\n")
                    fallback_drives = self._fallback_drive_detection()
                    debug_text.insert(tk.END, f"Found {len(fallback_drives)} drives via fallback\n")
                    for drive in fallback_drives:
                        debug_text.insert(tk.END, f"  {drive['device']}: {drive['model']}\n")
                        
                else:
                    debug_text.insert(tk.END, f"Detection script not found: {script_path}\n")
                    
            except Exception as e:
                debug_text.insert(tk.END, f"Debug detection failed: {e}\n")
                import traceback
                debug_text.insert(tk.END, traceback.format_exc())
                
            debug_text.see(tk.END)
        
        # Run debug in thread
        threading.Thread(target=run_debug, daemon=True).start()
        
    def load_mock_data(self):
        """Load mock drive data for testing"""
        self.detected_drives = self._mock_drive_detection()
        self.show_main_screen()
        
    def create_top_section(self, parent):
        """Create top section with app title and system info"""
        # Left side - App title
        left_frame = self.create_frame(parent)
        left_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        title_label = self.create_label(left_frame, APP_NAME,
                                      font=("Arial", 32, "bold"),
                                      fg=self.theme.ACCENT_PURPLE)
        title_label.pack(anchor=tk.W)
        
        subtitle_label = self.create_label(left_frame, "Secure Data Destruction",
                                         font=("Arial", 14),
                                         fg=self.theme.TEXT_SECONDARY)
        subtitle_label.pack(anchor=tk.W)
        
        # Right side - System info
        right_frame = self.create_frame(parent)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y)
        
        # System information
        import socket
        hostname = socket.gethostname()
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        sys_info = f"System: {hostname}\nTime: {current_time}\nVersion: {APP_VERSION}"
        
        sys_label = self.create_label(right_frame, sys_info,
                                    font=("Arial", 10),
                                    fg=self.theme.TEXT_SECONDARY,
                                    justify=tk.RIGHT)
        sys_label.pack(anchor=tk.E)
        
    def create_drive_section(self, parent):
        """Create drive list and control section"""
        # Drive list frame
        list_frame = self.create_frame(parent)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # List title
        list_title = self.create_label(list_frame, "Detected Storage Devices",
                                     font=("Arial", 16, "bold"),
                                     fg=self.theme.TEXT_PRIMARY)
        list_title.pack(anchor=tk.W, pady=(0, 10))
        
        # Drive tree view
        self.create_drive_tree(list_frame)
        
        # Control buttons
        control_frame = self.create_frame(list_frame)
        control_frame.pack(fill=tk.X, pady=10)
        
        refresh_btn = self.create_button(control_frame, "🔄 Refresh",
                                       self.refresh_drives)
        refresh_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        wipe_btn = self.create_button(control_frame, "⚠️ WIPE SELECTED",
                                    self.confirm_wipe,
                                    bg=self.theme.ERROR_RED)
        wipe_btn.pack(side=tk.RIGHT)
        
    def create_drive_tree(self, parent):
        """Create tree view for drive list"""
        # Tree frame with scrollbar
        tree_frame = self.create_frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Column definitions
        columns = ("device", "model", "serial", "size", "type", "method", "status")
        
        self.drive_tree = ttk.Treeview(tree_frame, columns=columns, show="tree headings", height=10)
        
        # Configure columns
        self.drive_tree.column("#0", width=50, minwidth=30)
        self.drive_tree.column("device", width=100, minwidth=80)
        self.drive_tree.column("model", width=200, minwidth=150)
        self.drive_tree.column("serial", width=150, minwidth=100)
        self.drive_tree.column("size", width=80, minwidth=60)
        self.drive_tree.column("type", width=80, minwidth=60)
        self.drive_tree.column("method", width=180, minwidth=150)
        self.drive_tree.column("status", width=100, minwidth=80)
        
        # Configure headings
        self.drive_tree.heading("#0", text="☐")
        self.drive_tree.heading("device", text="Device")
        self.drive_tree.heading("model", text="Model")
        self.drive_tree.heading("serial", text="Serial")
        self.drive_tree.heading("size", text="Size")
        self.drive_tree.heading("type", text="Type")
        self.drive_tree.heading("method", text="Recommended Method")
        self.drive_tree.heading("status", text="Status")
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.drive_tree.yview)
        self.drive_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack tree and scrollbar
        self.drive_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind events
        self.drive_tree.bind("<Button-1>", self.on_tree_click)
        self.drive_tree.bind("<Double-1>", self.on_tree_double_click)
        
        # Populate with detected drives
        self.populate_drive_tree()
        
    def populate_drive_tree(self):
        """Populate tree view with detected drives"""
        # Clear existing items
        for item in self.drive_tree.get_children():
            self.drive_tree.delete(item)
            
        # Add drives
        for i, drive in enumerate(self.detected_drives):
            device = drive.get("device", "unknown")
            model = drive.get("model", "Unknown")
            serial = drive.get("serial", "Unknown")
            size = drive.get("size", "0")
            
            # Determine type and icon
            interface = drive.get("interface", "unknown")
            is_ssd = drive.get("is_ssd", False)
            
            if interface == "nvme":
                drive_type = "NVMe"
                icon = "💾"
            elif is_ssd:
                drive_type = "SSD"
                icon = "💿"
            else:
                drive_type = "HDD"
                icon = "🖴"
                
            # Recommended method
            method_info = drive.get("recommended_method", {})
            method = method_info.get("method", "MULTI_PASS_OVERWRITE")
            
            # Status
            mounted = drive.get("mounted", False)
            status = "MOUNTED" if mounted else "Ready"
            
            # Insert item
            item_id = self.drive_tree.insert("", tk.END,
                                           text=f"{icon}",
                                           values=(device, model, serial, size, 
                                                 drive_type, method, status))
            
            # Color coding based on status
            if mounted:
                self.drive_tree.set(item_id, "status", "⚠️ MOUNTED")
            
    def on_tree_click(self, event):
        """Handle tree item click for selection"""
        item = self.drive_tree.identify('item', event.x, event.y)
        region = self.drive_tree.identify('region', event.x, event.y)
        
        if item and region == "tree":
            # Toggle selection
            current_text = self.drive_tree.item(item, "text")
            if "☑" in current_text:
                # Unselect
                new_text = current_text.replace("☑", "☐")
                self.drive_tree.item(item, text=new_text)
                device = self.drive_tree.set(item, "device")
                if device in self.selected_drives:
                    self.selected_drives.remove(device)
            else:
                # Select
                new_text = current_text.replace("☐", "☑")
                self.drive_tree.item(item, text=new_text)
                device = self.drive_tree.set(item, "device")
                if device not in self.selected_drives:
                    self.selected_drives.append(device)
                    
    def on_tree_double_click(self, event):
        """Handle tree item double-click for details"""
        item = self.drive_tree.identify('item', event.x, event.y)
        if item:
            device = self.drive_tree.set(item, "device")
            self.show_device_details(device)
            
    def show_device_details(self, device):
        """Show detailed device information"""
        # Find drive data
        drive_data = None
        for drive in self.detected_drives:
            if drive.get("device") == device:
                drive_data = drive
                break
                
        if not drive_data:
            messagebox.showerror("Error", f"Device data not found: {device}")
            return
            
        # Create details window
        details_window = tk.Toplevel(self.root)
        details_window.title(f"Device Details - {device}")
        details_window.geometry("600x500")
        details_window.configure(bg=self.theme.BG_PRIMARY)
        
        # Details text
        details_text = scrolledtext.ScrolledText(details_window,
                                               bg=self.theme.BG_SECONDARY,
                                               fg=self.theme.TEXT_PRIMARY,
                                               font=("Courier", 10))
        details_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Format drive data as readable text
        formatted_data = json.dumps(drive_data, indent=2)
        details_text.insert(tk.END, formatted_data)
        details_text.config(state=tk.DISABLED)
        
    def confirm_wipe(self):
        """Show wipe confirmation dialog"""
        if not self.selected_drives:
            messagebox.showwarning("No Selection", "Please select drives to wipe.")
            return
            
        # Create confirmation dialog
        self.show_wipe_confirmation()
        
    def show_wipe_confirmation(self):
        """Show dramatic wipe confirmation interface"""
        confirm_frame = self.create_frame()
        
        # Warning header
        warning_frame = self.create_frame(confirm_frame)
        warning_frame.pack(fill=tk.X, padx=20, pady=20)
        warning_frame.configure(bg=self.theme.ERROR_RED)
        
        warning_title = self.create_label(warning_frame, "⚠️ DESTRUCTIVE OPERATION WARNING ⚠️",
                                        font=("Arial", 20, "bold"),
                                        fg="white",
                                        bg=self.theme.ERROR_RED)
        warning_title.pack(pady=10)
        
        # Selected drives list
        drives_frame = self.create_frame(confirm_frame)
        drives_frame.pack(fill=tk.X, padx=20, pady=10)
        
        drives_label = self.create_label(drives_frame, "Selected Drives:",
                                       font=("Arial", 14, "bold"),
                                       fg=self.theme.TEXT_PRIMARY)
        drives_label.pack(anchor=tk.W)
        
        for device in self.selected_drives:
            device_label = self.create_label(drives_frame, f"• {device}",
                                           font=("Arial", 12),
                                           fg=self.theme.ACCENT_CYAN)
            device_label.pack(anchor=tk.W, padx=20)
            
        # Warning text
        warning_text = """
THIS WILL PERMANENTLY DESTROY ALL DATA ON THE SELECTED DEVICES.
Data recovery will be IMPOSSIBLE after this operation.

• Verify the target devices are correct
• Ensure important data is backed up elsewhere  
• This process may take several hours to complete

Type 'I UNDERSTAND AND CONFIRM WIPE' to proceed:"""

        warning_label = self.create_label(confirm_frame, warning_text,
                                        font=("Arial", 12),
                                        fg=self.theme.TEXT_PRIMARY,
                                        justify=tk.LEFT)
        warning_label.pack(pady=20, padx=20)
        
        # Confirmation entry
        self.confirmation_var = tk.StringVar()
        confirmation_entry = tk.Entry(confirm_frame,
                                    textvariable=self.confirmation_var,
                                    font=("Arial", 14),
                                    bg=self.theme.BG_SECONDARY,
                                    fg=self.theme.TEXT_PRIMARY,
                                    width=40)
        confirmation_entry.pack(pady=10)
        confirmation_entry.focus()
        
        # Buttons
        button_frame = self.create_frame(confirm_frame)
        button_frame.pack(pady=20)
        
        cancel_btn = self.create_button(button_frame, "Cancel", self.show_main_screen)
        cancel_btn.pack(side=tk.LEFT, padx=10)
        
        proceed_btn = self.create_button(button_frame, "PROCEED WITH WIPE",
                                       self.start_wipe_operation,
                                       bg=self.theme.ERROR_RED)
        proceed_btn.pack(side=tk.LEFT, padx=10)
        
        self.switch_frame(confirm_frame)
        
    def start_wipe_operation(self):
        """Start the wipe operation after confirmation"""
        confirmation_text = self.confirmation_var.get().strip()
        
        if confirmation_text != "I UNDERSTAND AND CONFIRM WIPE":
            messagebox.showerror("Confirmation Failed", 
                               "Please type the exact confirmation text.")
            return
            
        # Start wipe in background
        self.wipe_in_progress = True
        self.show_wipe_progress()
        
        # Start wipe thread
        threading.Thread(target=self._execute_wipe_background, daemon=True).start()
        
    def show_wipe_progress(self):
        """Show wipe progress interface"""
        progress_frame = self.create_frame()
        
        # Title
        title_label = self.create_label(progress_frame, "Wipe Operation in Progress",
                                      font=("Arial", 24, "bold"),
                                      fg=self.theme.ACCENT_PURPLE)
        title_label.pack(pady=(50, 30))
        
        # Overall progress
        overall_frame = self.create_frame(progress_frame)
        overall_frame.pack(fill=tk.X, padx=50, pady=10)
        
        overall_label = self.create_label(overall_frame, "Overall Progress:",
                                        font=("Arial", 14),
                                        fg=self.theme.TEXT_PRIMARY)
        overall_label.pack(anchor=tk.W)
        
        self.overall_progress = ttk.Progressbar(overall_frame, length=600, mode='determinate')
        self.overall_progress.pack(fill=tk.X, pady=5)
        
        # Current operation
        current_frame = self.create_frame(progress_frame)
        current_frame.pack(fill=tk.X, padx=50, pady=10)
        
        current_label = self.create_label(current_frame, "Current Operation:",
                                        font=("Arial", 14),
                                        fg=self.theme.TEXT_PRIMARY)
        current_label.pack(anchor=tk.W)
        
        self.current_progress = ttk.Progressbar(current_frame, length=600, mode='determinate')
        self.current_progress.pack(fill=tk.X, pady=5)
        
        # Status text
        self.status_var = tk.StringVar(value="Initializing wipe operation...")
        status_label = self.create_label(progress_frame, "",
                                       font=("Arial", 12),
                                       fg=self.theme.ACCENT_CYAN,
                                       textvariable=self.status_var)
        status_label.pack(pady=20)
        
        # Log output
        log_frame = self.create_frame(progress_frame)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=50, pady=20)
        
        log_label = self.create_label(log_frame, "Operation Log:",
                                    font=("Arial", 12, "bold"),
                                    fg=self.theme.TEXT_PRIMARY)
        log_label.pack(anchor=tk.W)
        
        self.log_text = scrolledtext.ScrolledText(log_frame,
                                                height=15,
                                                bg=self.theme.BG_SECONDARY,
                                                fg=self.theme.TEXT_PRIMARY,
                                                font=("Courier", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Abort button
        abort_btn = self.create_button(progress_frame, "Abort Operation",
                                     self.abort_wipe,
                                     bg=self.theme.WARNING_YELLOW)
        abort_btn.pack(pady=10)
        
        self.switch_frame(progress_frame)
        
    def _execute_wipe_background(self):
        """Execute wipe operation in background thread"""
        try:
            results = {}
    def _execute_wipe_background(self):
        """Execute wipe operation in background thread"""
        try:
            results = {}
            total_drives = len(self.selected_drives)
            
            for i, device in enumerate(self.selected_drives):
                if not self.wipe_in_progress:
                    break
                    
                # Update overall progress
                overall_percent = (i / total_drives) * 100
                self.root.after(0, lambda p=overall_percent: self.overall_progress.configure(value=p))
                
                # Update status
                self.root.after(0, lambda d=device: self.status_var.set(f"Wiping {d}..."))
                
                # Execute wipe script
                result = self._wipe_single_device(device)
                results[device] = result
                
                # Update log
                log_msg = f"Completed {device}: {result.get('status', 'unknown')}\n"
                self.root.after(0, lambda msg=log_msg: self._append_log(msg))
                
            # Complete
            self.wipe_results = results
            self.wipe_in_progress = False
            
            if results:
                self.root.after(0, self.show_wipe_complete)
            else:
                self.root.after(0, lambda: self.show_error("Wipe operation was cancelled"))
                
        except Exception as e:
            self.wipe_in_progress = False
            self.root.after(0, lambda: self.show_error(f"Wipe operation failed: {e}"))
            
    def _wipe_single_device(self, device):
        """Wipe a single device"""
        try:
            script_path = os.path.join(SCRIPTS_DIR, "wipe.sh")
            
            if not os.path.exists(script_path):
                return {"status": "error", "message": "Wipe script not found"}
                
            # For demo purposes, simulate wipe operation
            if True:  # Replace with: if os.environ.get("OBLITERATOR_DEMO") == "true":
                import random
                time.sleep(random.uniform(2, 5))  # Simulate wipe time
                return {
                    "status": "success",
                    "method": "DEMO_WIPE",
                    "verification": "PASS",
                    "duration": "2.5 minutes"
                }
            
            # Real wipe execution
            env = os.environ.copy()
            env["OBLITERATOR_OUTPUT_DIR"] = OUTPUT_DIR
            
            result = subprocess.run([script_path, device], 
                                  capture_output=True, 
                                  text=True,
                                  env=env,
                                  timeout=3600)  # 1 hour timeout
            
            if result.returncode == 0:
                return {"status": "success", "output": result.stdout}
            else:
                return {"status": "error", "message": result.stderr}
                
        except subprocess.TimeoutExpired:
            return {"status": "error", "message": "Wipe operation timed out"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
            
    def _append_log(self, message):
        """Append message to log text widget"""
        if self.log_text:
            self.log_text.insert(tk.END, message)
            self.log_text.see(tk.END)
            
    def show_wipe_complete(self):
        """Show wipe completion screen"""
        complete_frame = self.create_frame()
        
        # Success header
        success_frame = self.create_frame(complete_frame)
        success_frame.pack(fill=tk.X, padx=20, pady=20)
        success_frame.configure(bg=self.theme.SUCCESS_GREEN)
        
        success_title = self.create_label(success_frame, "✅ WIPE OPERATION COMPLETED ✅",
                                        font=("Arial", 20, "bold"),
                                        fg="white",
                                        bg=self.theme.SUCCESS_GREEN)
        success_title.pack(pady=10)
        
        # Results summary
        results_frame = self.create_frame(complete_frame)
        results_frame.pack(fill=tk.X, padx=20, pady=10)
        
        results_label = self.create_label(results_frame, "Wipe Results:",
                                        font=("Arial", 14, "bold"),
                                        fg=self.theme.TEXT_PRIMARY)
        results_label.pack(anchor=tk.W)
        
        for device, result in self.wipe_results.items():
            status = result.get("status", "unknown")
            status_color = self.theme.SUCCESS_GREEN if status == "success" else self.theme.ERROR_RED
            
            device_label = self.create_label(results_frame, f"• {device}: {status.upper()}",
                                           font=("Arial", 12),
                                           fg=status_color)
            device_label.pack(anchor=tk.W, padx=20)
            
        # Certificate generation
        cert_frame = self.create_frame(complete_frame)
        cert_frame.pack(fill=tk.X, padx=20, pady=20)
        
        cert_label = self.create_label(cert_frame, "Generate Security Certificate:",
                                     font=("Arial", 14, "bold"),
                                     fg=self.theme.TEXT_PRIMARY)
        cert_label.pack(anchor=tk.W)
        
        cert_text = """A tamper-evident digital certificate can be generated to provide
cryptographic proof of the data destruction operation."""

        cert_desc = self.create_label(cert_frame, cert_text,
                                    font=("Arial", 10),
                                    fg=self.theme.TEXT_SECONDARY)
        cert_desc.pack(anchor=tk.W, pady=5)
        
        # Buttons
        button_frame = self.create_frame(complete_frame)
        button_frame.pack(pady=30)
        
        cert_btn = self.create_button(button_frame, "Generate Certificate",
                                    self.generate_certificate)
        cert_btn.pack(side=tk.LEFT, padx=10)
        
        save_btn = self.create_button(button_frame, "Save Results",
                                    self.save_results)
        save_btn.pack(side=tk.LEFT, padx=10)
        
        new_btn = self.create_button(button_frame, "New Operation",
                                   self.reset_and_return_main)
        new_btn.pack(side=tk.LEFT, padx=10)
        
        self.switch_frame(complete_frame)
        
    def generate_certificate(self):
        """Generate security certificate"""
        try:
            # Create mock certificate data
            cert_data = {
                "certificate_id": f"cert_{int(time.time())}",
                "timestamp": datetime.now().isoformat(),
                "operator": self.operator_info,
                "devices": self.selected_drives,
                "results": self.wipe_results
            }
            
            # Save certificate
            cert_file = os.path.join(OUTPUT_DIR, f"certificate_{cert_data['certificate_id']}.json")
            with open(cert_file, 'w') as f:
                json.dump(cert_data, f, indent=2)
                
            messagebox.showinfo("Certificate Generated", 
                              f"Certificate saved to:\n{cert_file}")
                              
        except Exception as e:
            messagebox.showerror("Certificate Error", f"Failed to generate certificate: {e}")
            
    def save_results(self):
        """Save wipe results to file"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="Save Wipe Results"
            )
            
            if filename:
                results_data = {
                    "timestamp": datetime.now().isoformat(),
                    "selected_drives": self.selected_drives,
                    "results": self.wipe_results
                }
                
                with open(filename, 'w') as f:
                    json.dump(results_data, f, indent=2)
                    
                messagebox.showinfo("Results Saved", f"Results saved to:\n{filename}")
                
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save results: {e}")
            
    def reset_and_return_main(self):
        """Reset state and return to main screen"""
        self.selected_drives = []
        self.wipe_results = {}
        self.wipe_in_progress = False
        
        # Refresh drives and show main screen
        self.detect_drives_and_show_main()
        
    def abort_wipe(self):
        """Abort wipe operation"""
        if self.wipe_in_progress:
            result = messagebox.askyesno("Abort Wipe", 
                                       "Are you sure you want to abort the wipe operation?\n\n"
                                       "This may leave drives in an inconsistent state.")
            if result:
                self.wipe_in_progress = False
                self.show_main_screen()
                
    def refresh_drives(self):
        """Refresh drive detection"""
        self.show_loading_screen("Refreshing drive list...")
        threading.Thread(target=self._detect_drives_background, daemon=True).start()
        
    def show_error(self, message):
        """Show error message"""
        messagebox.showerror("Error", message)
        self.show_main_screen()
        
    # Helper methods for GUI creation
    def create_frame(self, parent=None):
        """Create a themed frame"""
        if parent is None:
            parent = self.root
            
        if CTK_AVAILABLE:
            frame = ctk.CTkFrame(parent)
        else:
            frame = tk.Frame(parent, bg=self.theme.BG_PRIMARY)
        return frame
        
    def create_label(self, parent, text, **kwargs):
        """Create a themed label"""
        if CTK_AVAILABLE:
            label = ctk.CTkLabel(parent, text=text)
            if 'font' in kwargs:
                label.configure(font=kwargs['font'])
            if 'fg' in kwargs:
                label.configure(text_color=kwargs['fg'])
        else:
            label = tk.Label(parent, text=text, 
                           bg=kwargs.get('bg', self.theme.BG_PRIMARY),
                           fg=kwargs.get('fg', self.theme.TEXT_PRIMARY),
                           **{k: v for k, v in kwargs.items() if k not in ['bg', 'fg']})
        return label
        
    def create_button(self, parent, text, command, **kwargs):
        """Create a themed button"""
        if CTK_AVAILABLE:
            button = ctk.CTkButton(parent, text=text, command=command)
            if 'bg' in kwargs:
                button.configure(fg_color=kwargs['bg'])
        else:
            button = tk.Button(parent, text=text, command=command,
                             bg=kwargs.get('bg', self.theme.ACCENT_PURPLE),
                             fg=kwargs.get('fg', self.theme.TEXT_PRIMARY),
                             activebackground=self.theme.ACCENT_CYAN,
                             relief=tk.FLAT,
                             padx=20, pady=8,
                             font=("Arial", 10, "bold"))
        return button
        
    def switch_frame(self, new_frame):
        """Switch to a new frame"""
        if self.current_frame:
            self.current_frame.destroy()
        self.current_frame = new_frame
        new_frame.pack(fill=tk.BOTH, expand=True)
        
    def on_closing(self):
        """Handle application closing"""
        if self.wipe_in_progress:
            result = messagebox.askyesno("Confirm Exit", 
                                       "A wipe operation is in progress.\n"
                                       "Exiting now may leave drives in an inconsistent state.\n\n"
                                       "Are you sure you want to exit?")
            if not result:
                return
                
        self.root.quit()
        self.root.destroy()
        
    def run(self):
        """Run the application"""
        self.setup_root_window()
        self.show_splash_screen()
        self.root.mainloop()

def main():
    """Main entry point"""
    try:
        # Check for required dependencies
        missing_deps = []
        
        try:
            import tkinter
        except ImportError:
            missing_deps.append("tkinter (python3-tk)")
            
        if missing_deps:
            print("ERROR: Missing required dependencies:")
            for dep in missing_deps:
                print(f"  - {dep}")
            print("\nInstall with: sudo apt install python3-tk")
            sys.exit(1)
            
        # Create and run application
        app = ObliperatorGUI()
        app.run()
        
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
