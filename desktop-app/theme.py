"""
Theme Manager for Posture OS
JARVIS-inspired HUD aesthetic: clean whites, silvers, and electric cyan accents.
Supports full per-color customization saved to disk.
"""
import json
import math
import os
import random
from dataclasses import dataclass, field
from typing import Dict, Optional

# ---------------------------------------------------------------------------
# Built-in Theme Presets
# ---------------------------------------------------------------------------

JARVIS_LIGHT = {
    "name": "JARVIS Light",
    # Core backgrounds
    "bg":               "#f0f4f8",
    "bg_secondary":     "#e4eaf2",
    "card_bg":          "#ffffff",
    "card_border":      "#00c8ff",
    # Sidebar
    "sidebar_bg":       "#0d1117",
    "sidebar_text":     "#7aafcc",
    "sidebar_active":   "#00c8ff",
    # Accent
    "accent":           "#00c8ff",
    "accent_secondary": "#00e5ff",
    # Text
    "text":             "#0d1117",
    "text_secondary":   "#4a6070",
    "text_heading":     "#0090bb",
    # Semantic
    "danger":           "#e63950",
    "danger_bg":        "#ffe8ec",
    "success":          "#00b894",
    "warning":          "#f39c12",
    # Plots
    "pitch_line":       "#0090ff",
    "yaw_line":         "#00c8a0",
    "threshold_line":   "#e63950",
    "threshold_lr":     "#f39c12",
    "violation_shade":  "#e6395025",
    "grid":             "#c0d0e0",
    "plot_bg":          "#f8fbff",
    "plot_face":        "#f0f4f8",
    # Hand / misc
    "hand_fill":        "#e8f4ff",
    "hand_outline":     "#00c8ff",
    "hand_danger":      "#e63950",
    "hand_safe":        "#00b894",
    "scrollbar":        "#b0c8e0",
    "button_hover":     "#e0f4ff",
    "swirl_colors":     ["#00c8ff", "#00e5ff", "#0090bb", "#00a0cc"],
}

JARVIS_DARK = {
    "name": "JARVIS Dark",
    # Core backgrounds
    "bg":               "#060c14",
    "bg_secondary":     "#0a1420",
    "card_bg":          "#0e1c2e",
    "card_border":      "#00c8ff",
    # Sidebar
    "sidebar_bg":       "#060c14",
    "sidebar_text":     "#4a7a99",
    "sidebar_active":   "#00c8ff",
    # Accent
    "accent":           "#00c8ff",
    "accent_secondary": "#00e5ff",
    # Text
    "text":             "#c8e8ff",
    "text_secondary":   "#4a7a99",
    "text_heading":     "#00c8ff",
    # Semantic
    "danger":           "#ff3355",
    "danger_bg":        "#2a0818",
    "success":          "#00e5b0",
    "warning":          "#ffaa00",
    # Plots
    "pitch_line":       "#00aaff",
    "yaw_line":         "#00e5b0",
    "threshold_line":   "#ff3355",
    "threshold_lr":     "#ffaa00",
    "violation_shade":  "#ff335530",
    "grid":             "#0a2030",
    "plot_bg":          "#080e18",
    "plot_face":        "#060c14",
    # Hand / misc
    "hand_fill":        "#0e1c2e",
    "hand_outline":     "#00c8ff",
    "hand_danger":      "#ff3355",
    "hand_safe":        "#00e5b0",
    "scrollbar":        "#0a3050",
    "button_hover":     "#0a2040",
    "swirl_colors":     ["#00c8ff", "#00e5ff", "#0060aa", "#00c0a0"],
}

MONO_GRAY = {
    "name": "Mono Gray",
    # Core backgrounds
    "bg":               "#f5f5f5",
    "bg_secondary":     "#ebebeb",
    "card_bg":          "#ffffff",
    "card_border":      "#888888",
    # Sidebar
    "sidebar_bg":       "#222222",
    "sidebar_text":     "#999999",
    "sidebar_active":   "#ffffff",
    # Accent
    "accent":           "#555555",
    "accent_secondary": "#777777",
    # Text
    "text":             "#111111",
    "text_secondary":   "#666666",
    "text_heading":     "#333333",
    # Semantic
    "danger":           "#cc2222",
    "danger_bg":        "#ffe8e8",
    "success":          "#229944",
    "warning":          "#cc7700",
    # Plots
    "pitch_line":       "#444444",
    "yaw_line":         "#888888",
    "threshold_line":   "#cc2222",
    "threshold_lr":     "#cc7700",
    "violation_shade":  "#cc222225",
    "grid":             "#cccccc",
    "plot_bg":          "#fafafa",
    "plot_face":        "#f5f5f5",
    # misc
    "hand_fill":        "#f0f0f0",
    "hand_outline":     "#555555",
    "hand_danger":      "#cc2222",
    "hand_safe":        "#229944",
    "scrollbar":        "#aaaaaa",
    "button_hover":     "#e8e8e8",
    "swirl_colors":     ["#888888", "#aaaaaa", "#666666", "#999999"],
}

PRESETS = {
    "JARVIS Light": JARVIS_LIGHT,
    "JARVIS Dark":  JARVIS_DARK,
    "Mono Gray":    MONO_GRAY,
}

# Color keys that are user-customizable (shown in settings panel)
CUSTOMIZABLE_KEYS = [
    ("accent",          "Accent / Highlight"),
    ("accent_secondary","Accent Secondary"),
    ("bg",              "Background"),
    ("card_bg",         "Card Background"),
    ("card_border",     "Card Border"),
    ("sidebar_bg",      "Sidebar Background"),
    ("sidebar_text",    "Sidebar Text"),
    ("text",            "Main Text"),
    ("text_secondary",  "Secondary Text"),
    ("text_heading",    "Heading Text"),
    ("danger",          "Danger / Alert"),
    ("success",         "Success / Good"),
    ("warning",         "Warning"),
    ("pitch_line",      "Plot: Pitch Line"),
    ("yaw_line",        "Plot: Yaw Line"),
    ("grid",            "Plot: Grid"),
]


# ---------------------------------------------------------------------------
# Theme Manager
# ---------------------------------------------------------------------------

class ThemeManager:
    """Singleton theme manager — holds the active color palette."""
    _instance: Optional["ThemeManager"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._colors: Dict[str, str] = dict(JARVIS_LIGHT)
            cls._instance._mode = "light"
            cls._instance.config_path: Optional[str] = None  # set by App on startup
        return cls._instance

    @property
    def mode(self) -> str:
        return self._mode

    @mode.setter
    def mode(self, value: str):
        self._mode = value
        if value == "dark":
            self._colors = dict(JARVIS_DARK)
        else:
            self._colors = dict(JARVIS_LIGHT)

    @property
    def colors(self) -> Dict[str, str]:
        return self._colors

    def apply_preset(self, name: str):
        if name in PRESETS:
            self._colors = dict(PRESETS[name])
            self._mode = "dark" if "dark" in name.lower() else "light"

    def set_color(self, key: str, value: str):
        """Override a single color in the active palette."""
        self._colors[key] = value

    def save_to_file(self):
        """Persist the current color palette to config_path as JSON."""
        if not self.config_path:
            return
        try:
            data = {"mode": self._mode, "colors": self._colors}
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def load_from_file(self):
        """Load a previously saved palette from config_path. Returns True if loaded."""
        if not self.config_path:
            return False
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "colors" in data:
                self._colors = data["colors"]
                self._mode = data.get("mode", "light")
                return True
        except Exception:
            pass
        return False

    def get_matplotlib_style(self) -> dict:
        c = self._colors
        return {
            "figure.facecolor":    c["plot_face"],
            "axes.facecolor":      c["plot_bg"],
            "axes.edgecolor":      c["grid"],
            "axes.labelcolor":     c["text"],
            "axes.grid":           True,
            "grid.color":          c["grid"],
            "grid.linestyle":      ":",
            "grid.alpha":          0.5,
            "text.color":          c["text"],
            "xtick.color":         c["text_secondary"],
            "ytick.color":         c["text_secondary"],
            "legend.facecolor":    c["card_bg"],
            "legend.edgecolor":    c["card_border"],
            "legend.labelcolor":   c["text"],
        }

    def apply_matplotlib_style(self):
        import matplotlib as mpl
        for k, v in self.get_matplotlib_style().items():
            mpl.rcParams[k] = v

    def get_plot_colors(self) -> dict:
        c = self._colors
        return {
            "pitch_line":      c["pitch_line"],
            "yaw_line":        c["yaw_line"],
            "threshold_line":  c["threshold_line"],
            "threshold_lr":    c["threshold_lr"],
            "violation_shade": c["violation_shade"],
        }

    def __getitem__(self, key: str) -> str:
        return self._colors[key]


# ---------------------------------------------------------------------------
# Decorative HUD grid lines (replaces swirls)
# ---------------------------------------------------------------------------

def draw_decorative_swirls(canvas, width: int, height: int, tag: str = "swirl"):
    """Draw subtle HUD-style grid accents on a tkinter Canvas."""
    canvas.delete(tag)
    tm = ThemeManager()
    accent = tm.colors.get("accent", "#00c8ff")
    grid_c = tm.colors.get("grid", "#c0d0e0")

    # Draw faint corner bracket accents
    size = 40
    pad = 20
    corners = [
        (pad, pad, pad + size, pad + size),
        (width - pad - size, pad, width - pad, pad + size),
        (pad, height - pad - size, pad + size, height - pad),
        (width - pad - size, height - pad - size, width - pad, height - pad),
    ]
    for x1, y1, x2, y2 in corners:
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        # Top-left corner of each bracket
        bx, by = x1, y1
        canvas.create_line(bx, by, bx + 18, by, fill=accent, width=2,
                           stipple="gray50", tags=tag)
        canvas.create_line(bx, by, bx, by + 18, fill=accent, width=2,
                           stipple="gray50", tags=tag)
        canvas.create_line(x2, y2, x2 - 18, y2, fill=accent, width=2,
                           stipple="gray50", tags=tag)
        canvas.create_line(x2, y2, x2, y2 - 18, fill=accent, width=2,
                           stipple="gray50", tags=tag)
