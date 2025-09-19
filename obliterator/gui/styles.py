#!/usr/bin/env python3
"""
Obliterator GUI Styles and Theming
Dark purple theme for secure appearance
Version: 1.0.0
"""

import tkinter as tk
from tkinter import ttk

class ObliperatorTheme:
    """Dark purple theme for Obliterator GUI"""

    # Primary colors
    BG_PRIMARY = "#1a1a2e"        # Dark navy background
    BG_SECONDARY = "#16213e"      # Slightly lighter navy
    BG_ACCENT = "#0f3460"         # Blue accent background

    # Text colors
    TEXT_PRIMARY = "#ffffff"      # White text
    TEXT_SECONDARY = "#b8b8b8"    # Light gray text
    TEXT_MUTED = "#7d8590"       # Muted gray text

    # Accent colors
    ACCENT_PURPLE = "#6a0d83"     # Primary purple
    ACCENT_CYAN = "#00d4ff"       # Cyan highlights
    ACCENT_BLUE = "#0066cc"       # Blue accents

    # Status colors
    SUCCESS_GREEN = "#00ff88"     # Success/safe
    WARNING_YELLOW = "#ffcc00"    # Warning/caution
    ERROR_RED = "#ff4757"         # Error/danger
    INFO_BLUE = "#3498db"         # Information

    # UI element colors
    BORDER_COLOR = "#30363d"      # Border color
    HOVER_COLOR = "#21262d"       # Hover state
    SELECTED_COLOR = "#238636"    # Selected state

    # Gradients (for advanced theming)
    GRADIENT_START = "#1a1a2e"
    GRADIENT_END = "#16213e"

    # Font configurations
    FONT_FAMILY = "Segoe UI"
    FONT_SIZE_LARGE = 24
    FONT_SIZE_NORMAL = 12
    FONT_SIZE_SMALL = 10

    # Spacing
    PADDING_LARGE = 20
    PADDING_MEDIUM = 10
    PADDING_SMALL = 5

    # Window dimensions
    WINDOW_MIN_WIDTH = 1000
    WINDOW_MIN_HEIGHT = 700
    WINDOW_DEFAULT_WIDTH = 1200
    WINDOW_DEFAULT_HEIGHT = 800

def apply_theme(widget, theme=None):
    """Apply Obliterator theme to a widget"""
    if theme is None:
        theme = ObliperatorTheme()

    if isinstance(widget, tk.Tk) or isinstance(widget, tk.Toplevel):
        # Main window theming
        widget.configure(bg=theme.BG_PRIMARY)

        # Configure ttk style
        style = ttk.Style(widget)
        configure_ttk_theme(style, theme)

    elif isinstance(widget, tk.Frame):
        widget.configure(bg=theme.BG_PRIMARY)

    elif isinstance(widget, tk.Label):
        widget.configure(
            bg=theme.BG_PRIMARY,
            fg=theme.TEXT_PRIMARY,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE_NORMAL)
        )

    elif isinstance(widget, tk.Button):
        widget.configure(
            bg=theme.ACCENT_PURPLE,
            fg=theme.TEXT_PRIMARY,
            activebackground=theme.ACCENT_CYAN,
            activeforeground=theme.TEXT_PRIMARY,
            relief=tk.FLAT,
            borderwidth=0,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE_NORMAL, "bold"),
            cursor="hand2"
        )

    elif isinstance(widget, tk.Entry):
        widget.configure(
            bg=theme.BG_SECONDARY,
            fg=theme.TEXT_PRIMARY,
            insertbackground=theme.TEXT_PRIMARY,
            selectbackground=theme.ACCENT_PURPLE,
            selectforeground=theme.TEXT_PRIMARY,
            relief=tk.FLAT,
            borderwidth=1,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE_NORMAL)
        )

    elif isinstance(widget, tk.Text):
        widget.configure(
            bg=theme.BG_SECONDARY,
            fg=theme.TEXT_PRIMARY,
            insertbackground=theme.TEXT_PRIMARY,
            selectbackground=theme.ACCENT_PURPLE,
            selectforeground=theme.TEXT_PRIMARY,
            relief=tk.FLAT,
            borderwidth=1,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE_SMALL)
        )

def configure_ttk_theme(style, theme):
    """Configure ttk widget styling"""

    # Configure ttk.Frame
    style.configure("TFrame",
                   background=theme.BG_PRIMARY,
                   relief="flat",
                   borderwidth=0)

    # Configure ttk.Label
    style.configure("TLabel",
                   background=theme.BG_PRIMARY,
                   foreground=theme.TEXT_PRIMARY,
                   font=(theme.FONT_FAMILY, theme.FONT_SIZE_NORMAL))

    style.configure("Title.TLabel",
                   background=theme.BG_PRIMARY,
                   foreground=theme.ACCENT_PURPLE,
                   font=(theme.FONT_FAMILY, theme.FONT_SIZE_LARGE, "bold"))

    style.configure("Subtitle.TLabel",
                   background=theme.BG_PRIMARY,
                   foreground=theme.TEXT_SECONDARY,
                   font=(theme.FONT_FAMILY, theme.FONT_SIZE_NORMAL))

    # Configure ttk.Button
    style.configure("TButton",
                   background=theme.ACCENT_PURPLE,
                   foreground=theme.TEXT_PRIMARY,
                   borderwidth=0,
                   focuscolor="none",
                   font=(theme.FONT_FAMILY, theme.FONT_SIZE_NORMAL, "bold"))

    style.map("TButton",
             background=[
                 ("active", theme.ACCENT_CYAN),
                 ("pressed", theme.ACCENT_BLUE),
                 ("disabled", theme.BG_ACCENT)
             ],
             foreground=[
                 ("disabled", theme.TEXT_MUTED)
             ])

    # Danger button style
    style.configure("Danger.TButton",
                   background=theme.ERROR_RED,
                   foreground=theme.TEXT_PRIMARY,
                   font=(theme.FONT_FAMILY, theme.FONT_SIZE_NORMAL, "bold"))

    style.map("Danger.TButton",
             background=[
                 ("active", "#ff6b7a"),
                 ("pressed", "#ff3742")
             ])

    # Success button style
    style.configure("Success.TButton",
                   background=theme.SUCCESS_GREEN,
                   foreground=theme.BG_PRIMARY,
                   font=(theme.FONT_FAMILY, theme.FONT_SIZE_NORMAL, "bold"))

    # Configure ttk.Entry
    style.configure("TEntry",
                   fieldbackground=theme.BG_SECONDARY,
                   background=theme.BG_SECONDARY,
                   foreground=theme.TEXT_PRIMARY,
                   borderwidth=1,
                   insertcolor=theme.TEXT_PRIMARY,
                   selectbackground=theme.ACCENT_PURPLE,
                   selectforeground=theme.TEXT_PRIMARY)

    style.map("TEntry",
             focuscolor=[
                 ("!focus", theme.BORDER_COLOR),
                 ("focus", theme.ACCENT_PURPLE)
             ])

    # Configure ttk.Treeview
    style.configure("Treeview",
                   background=theme.BG_SECONDARY,
                   foreground=theme.TEXT_PRIMARY,
                   fieldbackground=theme.BG_SECONDARY,
                   borderwidth=1,
                   relief="flat")

    style.configure("Treeview.Heading",
                   background=theme.BG_ACCENT,
                   foreground=theme.TEXT_PRIMARY,
                   relief="flat",
                   font=(theme.FONT_FAMILY, theme.FONT_SIZE_NORMAL, "bold"))

    style.map("Treeview",
             background=[
                 ("selected", theme.ACCENT_PURPLE),
                 ("focus", theme.ACCENT_PURPLE)
             ],
             foreground=[
                 ("selected", theme.TEXT_PRIMARY),
                 ("focus", theme.TEXT_PRIMARY)
             ])

    style.map("Treeview.Heading",
             background=[
                 ("active", theme.ACCENT_PURPLE)
             ])

    # Configure ttk.Progressbar
    style.configure("TProgressbar",
                   background=theme.ACCENT_PURPLE,
                   troughcolor=theme.BG_SECONDARY,
                   borderwidth=0,
                   lightcolor=theme.ACCENT_PURPLE,
                   darkcolor=theme.ACCENT_PURPLE)

    # Custom progressbar styles
    style.configure("Success.Horizontal.TProgressbar",
                   background=theme.SUCCESS_GREEN,
                   troughcolor=theme.BG_SECONDARY)

    style.configure("Warning.Horizontal.TProgressbar",
                   background=theme.WARNING_YELLOW,
                   troughcolor=theme.BG_SECONDARY)

    style.configure("Error.Horizontal.TProgressbar",
                   background=theme.ERROR_RED,
                   troughcolor=theme.BG_SECONDARY)

    # Configure ttk.Separator
    style.configure("TSeparator",
                   background=theme.BORDER_COLOR)

    # Configure ttk.Scrollbar
    style.configure("Vertical.TScrollbar",
                   background=theme.BG_ACCENT,
                   troughcolor=theme.BG_SECONDARY,
                   borderwidth=0,
                   arrowcolor=theme.TEXT_SECONDARY,
                   darkcolor=theme.BG_ACCENT,
                   lightcolor=theme.BG_ACCENT)

    style.map("Vertical.TScrollbar",
             background=[
                 ("active", theme.ACCENT_PURPLE),
                 ("pressed", theme.ACCENT_BLUE)
             ])

def create_styled_widget(widget_type, parent, style_name=None, **kwargs):
    """Create a pre-styled widget"""
    theme = ObliperatorTheme()

    if widget_type == "title_label":
        widget = tk.Label(parent,
                         font=(theme.FONT_FAMILY, theme.FONT_SIZE_LARGE, "bold"),
                         bg=theme.BG_PRIMARY,
                         fg=theme.ACCENT_PURPLE,
                         **kwargs)

    elif widget_type == "subtitle_label":
        widget = tk.Label(parent,
                         font=(theme.FONT_FAMILY, theme.FONT_SIZE_NORMAL),
                         bg=theme.BG_PRIMARY,
                         fg=theme.TEXT_SECONDARY,
                         **kwargs)

    elif widget_type == "body_label":
        widget = tk.Label(parent,
                         font=(theme.FONT_FAMILY, theme.FONT_SIZE_NORMAL),
                         bg=theme.BG_PRIMARY,
                         fg=theme.TEXT_PRIMARY,
                         **kwargs)

    elif widget_type == "primary_button":
        widget = tk.Button(parent,
                          bg=theme.ACCENT_PURPLE,
                          fg=theme.TEXT_PRIMARY,
                          activebackground=theme.ACCENT_CYAN,
                          relief=tk.FLAT,
                          borderwidth=0,
                          font=(theme.FONT_FAMILY, theme.FONT_SIZE_NORMAL, "bold"),
                          cursor="hand2",
                          padx=theme.PADDING_MEDIUM,
                          pady=theme.PADDING_SMALL,
                          **kwargs)

    elif widget_type == "danger_button":
        widget = tk.Button(parent,
                          bg=theme.ERROR_RED,
                          fg=theme.TEXT_PRIMARY,
                          activebackground="#ff6b7a",
                          relief=tk.FLAT,
                          borderwidth=0,
                          font=(theme.FONT_FAMILY, theme.FONT_SIZE_NORMAL, "bold"),
                          cursor="hand2",
                          padx=theme.PADDING_MEDIUM,
                          pady=theme.PADDING_SMALL,
                          **kwargs)

    elif widget_type == "success_button":
        widget = tk.Button(parent,
                          bg=theme.SUCCESS_GREEN,
                          fg=theme.BG_PRIMARY,
                          activebackground="#33ff99",
                          relief=tk.FLAT,
                          borderwidth=0,
                          font=(theme.FONT_FAMILY, theme.FONT_SIZE_NORMAL, "bold"),
                          cursor="hand2",
                          padx=theme.PADDING_MEDIUM,
                          pady=theme.PADDING_SMALL,
                          **kwargs)

    elif widget_type == "text_entry":
        widget = tk.Entry(parent,
                         bg=theme.BG_SECONDARY,
                         fg=theme.TEXT_PRIMARY,
                         insertbackground=theme.TEXT_PRIMARY,
                         selectbackground=theme.ACCENT_PURPLE,
                         relief=tk.FLAT,
                         borderwidth=1,
                         font=(theme.FONT_FAMILY, theme.FONT_SIZE_NORMAL),
                         **kwargs)

    elif widget_type == "panel_frame":
        widget = tk.Frame(parent,
                         bg=theme.BG_SECONDARY,
                         relief=tk.FLAT,
                         borderwidth=1,
                         **kwargs)

    elif widget_type == "content_frame":
        widget = tk.Frame(parent,
                         bg=theme.BG_PRIMARY,
                         **kwargs)

    else:
        raise ValueError(f"Unknown widget type: {widget_type}")

    return widget

def setup_window_theme(window):
    """Setup complete window theming"""
    theme = ObliperatorTheme()

    # Window configuration
    window.configure(bg=theme.BG_PRIMARY)
    window.minsize(theme.WINDOW_MIN_WIDTH, theme.WINDOW_MIN_HEIGHT)

    # Create and configure ttk style
    style = ttk.Style(window)
    configure_ttk_theme(style, theme)

    return theme

def get_icon_font():
    """Get font configuration for icons"""
    # Unicode symbols that work well in the theme
    return {
        "font": ("Segoe UI Symbol", 16),
        "warning": "⚠️",
        "success": "✅",
        "error": "❌",
        "info": "ℹ️",
        "drive_hdd": "🖴",
        "drive_ssd": "💿",
        "drive_nvme": "💾",
        "drive_usb": "💽",
        "refresh": "🔄",
        "wipe": "🗑️",
        "cert": "📜",
        "save": "💾",
        "lock": "🔒"
    }

# Color scheme variations for different contexts
class ColorSchemes:
    """Additional color schemes for specific contexts"""

    @staticmethod
    def get_status_colors():
        return {
            "ready": ObliperatorTheme.SUCCESS_GREEN,
            "mounted": ObliperatorTheme.WARNING_YELLOW,
            "wiping": ObliperatorTheme.ACCENT_CYAN,
            "complete": ObliperatorTheme.SUCCESS_GREEN,
            "error": ObliperatorTheme.ERROR_RED,
            "unknown": ObliperatorTheme.TEXT_MUTED
        }

    @staticmethod
    def get_drive_type_colors():
        return {
            "hdd": "#8b9dc3",      # Blue-gray
            "ssd": "#dda0dd",      # Plum
            "nvme": "#98fb98",     # Pale green
            "usb": "#f0e68c",      # Khaki
            "unknown": ObliperatorTheme.TEXT_MUTED
        }

    @staticmethod
    def get_method_colors():
        return {
            "ATA_SECURE_ERASE": ObliperatorTheme.SUCCESS_GREEN,
            "ATA_SECURE_ERASE_ENHANCED": ObliperatorTheme.SUCCESS_GREEN,
            "NVME_CRYPTO_ERASE": ObliperatorTheme.SUCCESS_GREEN,
            "MULTI_PASS_OVERWRITE": ObliperatorTheme.ACCENT_CYAN,
            "BLKDISCARD": ObliperatorTheme.WARNING_YELLOW,
            "unknown": ObliperatorTheme.TEXT_MUTED
        }

# CSS-like styling for HTML generation
def get_css_styles():
    """Get CSS styles for HTML certificate generation"""
    theme = ObliperatorTheme()

    return f"""
    <style>
        body {{
            font-family: {theme.FONT_FAMILY}, sans-serif;
            background-color: {theme.BG_PRIMARY};
            color: {theme.TEXT_PRIMARY};
            margin: 0;
            padding: 20px;
            line-height: 1.6;
        }}

        .header {{
            text-align: center;
            border-bottom: 3px solid {theme.ACCENT_PURPLE};
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}

        .title {{
            color: {theme.ACCENT_PURPLE};
            font-size: 32px;
        .title {{
            color: {theme.ACCENT_PURPLE};
            font-size: 32px;
            font-weight: bold;
            margin: 0;
        }}

        .subtitle {{
            color: {theme.TEXT_SECONDARY};
            font-size: 16px;
            margin: 5px 0;
        }}

        .section {{
            margin: 25px 0;
            padding: 15px;
            border-left: 4px solid {theme.ACCENT_PURPLE};
            background: {theme.BG_SECONDARY};
        }}

        .section-title {{
            font-weight: bold;
            color: {theme.ACCENT_PURPLE};
            margin-bottom: 10px;
            font-size: 18px;
        }}

        .field {{
            margin: 8px 0;
        }}

        .field-label {{
            font-weight: bold;
            display: inline-block;
            width: 150px;
        }}

        .field-value {{
            color: {theme.TEXT_SECONDARY};
        }}

        .status-success {{
            background: {theme.SUCCESS_GREEN};
            color: {theme.BG_PRIMARY};
            padding: 5px 10px;
            border-radius: 3px;
            font-weight: bold;
        }}

        .status-warning {{
            background: {theme.WARNING_YELLOW};
            color: {theme.BG_PRIMARY};
            padding: 5px 10px;
            border-radius: 3px;
            font-weight: bold;
        }}

        .status-error {{
            background: {theme.ERROR_RED};
            color: {theme.TEXT_PRIMARY};
            padding: 5px 10px;
            border-radius: 3px;
            font-weight: bold;
        }}

        .signature {{
            font-family: monospace;
            background: {theme.BG_ACCENT};
            padding: 10px;
            border-radius: 4px;
            word-break: break-all;
            font-size: 10px;
        }}

        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid {theme.BORDER_COLOR};
            font-size: 12px;
            color: {theme.TEXT_MUTED};
            text-align: center;
        }}
    </style>
    """

# Animation configurations
class Animations:
    """Animation configurations for GUI elements"""

    FADE_DURATION = 300      # ms
    SLIDE_DURATION = 250     # ms
    BOUNCE_DURATION = 400    # ms

    @staticmethod
    def fade_in(widget, duration=None):
        """Fade in animation for widget"""
        # Note: tkinter has limited animation support
        # This would be implemented with after() calls
        pass

    @staticmethod
    def slide_left(widget, duration=None):
        """Slide left animation"""
        pass

    @staticmethod
    def bounce(widget, duration=None):
        """Bounce animation for buttons"""
        pass

# Responsive design helpers
class ResponsiveLayout:
    """Helper for responsive layout management"""

    @staticmethod
    def get_scale_factor(window_width):
        """Get UI scale factor based on window width"""
        if window_width < 1024:
            return 0.8
        elif window_width > 1600:
            return 1.2
        else:
            return 1.0

    @staticmethod
    def scale_font(base_size, scale_factor):
        """Scale font size"""
        return max(8, int(base_size * scale_factor))

    @staticmethod
    def scale_padding(base_padding, scale_factor):
        """Scale padding"""
        return max(2, int(base_padding * scale_factor))

# Theme manager for dynamic theming
class ThemeManager:
    """Manage and switch between themes"""

    def __init__(self):
        self.current_theme = ObliperatorTheme()
        self.available_themes = {
            "dark_purple": ObliperatorTheme(),
            "dark_blue": self.create_blue_theme(),
            "dark_green": self.create_green_theme()
        }

    def create_blue_theme(self):
        """Create blue variant theme"""
        theme = ObliperatorTheme()
        theme.ACCENT_PURPLE = "#0066cc"
        theme.ACCENT_CYAN = "#00aaff"
        return theme

    def create_green_theme(self):
        """Create green variant theme"""
        theme = ObliperatorTheme()
        theme.ACCENT_PURPLE = "#00aa44"
        theme.ACCENT_CYAN = "#00ff88"
        return theme

    def switch_theme(self, theme_name):
        """Switch to specified theme"""
        if theme_name in self.available_themes:
            self.current_theme = self.available_themes[theme_name]
            return True
        return False

    def get_current_theme(self):
        """Get current theme"""
        return self.current_theme

