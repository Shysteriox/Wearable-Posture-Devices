"""
Posture OS v2 — Main application entry point.
JARVIS-themed HUD interface. Three nav sections: Monitor, Analysis, History + Settings.
"""
import os
import sys

# Redirect stdout/stderr to log file in PyInstaller builds
if getattr(sys, 'frozen', False):
    try:
        log_dir = os.path.dirname(sys.executable)
        log_path = os.path.join(log_dir, "posture_os_debug.log")
        log_file = open(log_path, "w", encoding="utf-8")
        class Logger:
            def __init__(self, f): self.file = f
            def write(self, d): self.file.write(d); self.file.flush()
            def flush(self): self.file.flush()
            def isatty(self): return False
        sys.stdout = Logger(log_file)
        sys.stderr = Logger(log_file)
    except Exception:
        pass

import threading
from tkinter import filedialog, messagebox
from typing import List, Optional

import customtkinter as ctk

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

try:
    import customtkinter as ctk
    import pandas
    import matplotlib
    import serial

    from theme import ThemeManager, draw_decorative_swirls, PRESETS, CUSTOMIZABLE_KEYS
    from data_loader import (
        SessionData, load_csv, load_multiple_csvs, scan_for_csv_files,
        calculate_stats, aggregate_stats,
    )
    from serial_comm import get_device, HAS_SERIAL

    from pages.dashboard import DashboardPage
    from pages.overall import OverallPage
    from pages.timeline import TimelinePage
    from pages.hand_replay import HandReplayPage
    from pages.raw_data import RawDataPage
    from pages.jarvis_scan import JarvisScanPage
except ImportError as e:
    import tkinter as tk
    from tkinter import messagebox
    root = tk.Tk(); root.withdraw()
    messagebox.showerror(
        "Missing Libraries",
        f"Posture OS could not start — missing library:\n\n{e}\n\n"
        "Fix with:\n  pip install customtkinter pandas matplotlib pyserial"
    )
    sys.exit(1)

CACHE_DIR = os.path.join(BASE_DIR, "downloaded_logs")


# ---------------------------------------------------------------------------
# Sidebar nav button
# ---------------------------------------------------------------------------
class NavButton(ctk.CTkButton):
    def __init__(self, parent, text, icon, command, **kw):
        self._icon = icon
        self._label = text
        super().__init__(
            parent,
            text=f"  {icon}  {text}",
            anchor="w",
            font=ctk.CTkFont(family="Consolas", size=13),
            fg_color="transparent",
            hover_color="#0a2040",
            height=40,
            corner_radius=6,
            command=command,
            **kw,
        )

    def set_active(self, active: bool, colors: dict):
        if active:
            self.configure(
                fg_color=colors["accent"],
                text_color="#ffffff",
            )
        else:
            self.configure(
                fg_color="transparent",
                text_color=colors["sidebar_text"],
            )


# ---------------------------------------------------------------------------
# Settings Page (customization)
# ---------------------------------------------------------------------------
class SettingsPage(ctk.CTkFrame):
    """Full theme customization panel — color pickers per element + presets."""

    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.tm = ThemeManager()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build()

    def _build(self):
        for w in self.winfo_children():
            w.destroy()
        c = self.tm.colors

        # Header
        ctk.CTkLabel(self, text="⚙  SYSTEM SETTINGS",
                     font=ctk.CTkFont(family="Consolas", size=22, weight="bold"),
                     text_color=c["accent"]).grid(row=0, column=0, pady=(25, 5), sticky="w", padx=35)

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.grid(row=1, column=0, sticky="nsew", padx=25, pady=(0, 20))
        scroll.grid_columnconfigure(0, weight=1)
        scroll.grid_columnconfigure(1, weight=1)

        # --- Preset section ---
        preset_card = ctk.CTkFrame(scroll, fg_color=c["card_bg"], corner_radius=12,
                                   border_width=1, border_color=c["card_border"])
        preset_card.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 15), padx=5)

        ctk.CTkLabel(preset_card, text="THEME PRESETS",
                     font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
                     text_color=c["text_secondary"]).pack(anchor="w", padx=18, pady=(14, 8))

        preset_row = ctk.CTkFrame(preset_card, fg_color="transparent")
        preset_row.pack(fill="x", padx=15, pady=(0, 14))

        for name in PRESETS:
            ctk.CTkButton(
                preset_row, text=name,
                font=ctk.CTkFont(family="Consolas", size=12),
                height=34, corner_radius=8,
                fg_color=c["accent"] if PRESETS[name].get("name") == c.get("name") else c["bg_secondary"],
                text_color="#ffffff" if PRESETS[name].get("name") == c.get("name") else c["text"],
                hover_color=c["button_hover"],
                command=lambda n=name: self._apply_preset(n),
            ).pack(side="left", padx=4)

        # --- Color customization section ---
        color_card = ctk.CTkFrame(scroll, fg_color=c["card_bg"], corner_radius=12,
                                  border_width=1, border_color=c["card_border"])
        color_card.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 15), padx=5)

        ctk.CTkLabel(color_card, text="CUSTOM COLORS",
                     font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
                     text_color=c["text_secondary"]).pack(anchor="w", padx=18, pady=(14, 8))

        ctk.CTkLabel(color_card, text="Click a color swatch to change it (enter hex like #00c8ff)",
                     font=ctk.CTkFont(size=11), text_color=c["text_secondary"]).pack(
                     anchor="w", padx=18, pady=(0, 10))

        grid_frame = ctk.CTkFrame(color_card, fg_color="transparent")
        grid_frame.pack(fill="x", padx=15, pady=(0, 14))

        for i, (key, label) in enumerate(CUSTOMIZABLE_KEYS):
            row_f = ctk.CTkFrame(grid_frame, fg_color="transparent")
            row_f.grid(row=i // 2, column=i % 2, sticky="ew", padx=5, pady=3)
            grid_frame.grid_columnconfigure(i % 2, weight=1)

            ctk.CTkLabel(row_f, text=label, font=ctk.CTkFont(size=11),
                         text_color=c["text_secondary"], width=160, anchor="w").pack(side="left")

            swatch = ctk.CTkButton(
                row_f, text="", width=30, height=22, corner_radius=4,
                fg_color=c.get(key, "#888888"),
                hover_color=c.get(key, "#888888"),
                command=lambda k=key, lbl=label: self._pick_color(k, lbl),
            )
            swatch.pack(side="left", padx=5)

            val_lbl = ctk.CTkLabel(row_f, text=c.get(key, ""), font=ctk.CTkFont(family="Consolas", size=10),
                                   text_color=c["text_secondary"])
            val_lbl.pack(side="left")

        # --- Device section ---
        dev_card = ctk.CTkFrame(scroll, fg_color=c["card_bg"], corner_radius=12,
                                border_width=1, border_color=c["card_border"])
        dev_card.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 15), padx=5)

        ctk.CTkLabel(dev_card, text="CONNECTED DEVICE",
                     font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
                     text_color=c["text_secondary"]).pack(anchor="w", padx=18, pady=(14, 4))

        self._dev_label = ctk.CTkLabel(
            dev_card,
            text=self._get_device_info(),
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color=c["text"],
        )
        self._dev_label.pack(anchor="w", padx=18, pady=(0, 4))

        dev_btn_row = ctk.CTkFrame(dev_card, fg_color="transparent")
        dev_btn_row.pack(fill="x", padx=15, pady=(4, 14))

        for btn_text, cmd in [
            ("🔌  Connect Device", self.app._connect_device),
            ("💾  Scan SD Card",   self.app._scan_sd),
            ("📂  Browse Files",   self.app._browse_files),
        ]:
            ctk.CTkButton(dev_btn_row, text=btn_text,
                          font=ctk.CTkFont(family="Consolas", size=12),
                          height=32, corner_radius=8,
                          fg_color=c["bg_secondary"], hover_color=c["button_hover"],
                          text_color=c["text"],
                          command=cmd).pack(side="left", padx=4)

    def _get_device_info(self):
        session = self.app.get_active_session()
        if session:
            return f"Active: {session.device_name}  •  {len(self.app.sessions)} session(s) loaded"
        return "No device data loaded"

    def _apply_preset(self, name: str):
        self.tm.apply_preset(name)
        import customtkinter as ctk
        ctk.set_appearance_mode("Dark" if "dark" in name.lower() else "Light")
        self.tm.save_to_file()  # persist immediately
        self.app._rebuild_ui()

    def _pick_color(self, key: str, label: str):
        """Simple dialog to enter a hex color."""
        import tkinter.simpledialog as sd
        current = self.tm.colors.get(key, "#888888")
        new_val = sd.askstring(
            "Set Color",
            f"Enter hex color for '{label}':\n(e.g. #00c8ff)",
            initialvalue=current,
            parent=self,
        )
        if new_val and new_val.startswith("#") and len(new_val) in (4, 7):
            self.tm.set_color(key, new_val)
            self.tm.save_to_file()  # persist immediately
            self.app._rebuild_ui()

    def refresh(self):
        self._build()


# ---------------------------------------------------------------------------
# Main App
# ---------------------------------------------------------------------------
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.tm = ThemeManager()
        # Point ThemeManager at the config file next to the exe
        self.tm.config_path = os.path.join(BASE_DIR, "posture_os_theme.json")
        # Load saved theme; fall back to JARVIS Light if none exists
        if not self.tm.load_from_file():
            self.tm.mode = "light"
        ctk.set_appearance_mode("Dark" if self.tm.mode == "dark" else "Light")

        self.title("Posture OS")
        self.geometry("1280x820")
        self.minsize(1024, 680)

        self.sessions: List[SessionData] = []
        self.active_session_idx: int = 0
        self.pages = {}
        self.active_page_name = ""
        self.nav_buttons = {}

        self._build_layout()
        self._create_pages()
        self.switch_page("monitor")
        self.after(100, self._fix_titlebar)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build_layout(self):
        c = self.tm.colors

        self.grid_columnconfigure(0, weight=0, minsize=230)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ── Sidebar ──────────────────────────────────────────────
        self.sidebar = ctk.CTkFrame(self, width=230, corner_radius=0,
                                     fg_color=c["sidebar_bg"])
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_rowconfigure(5, weight=1)  # files list expands

        # Logo / title
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.pack(fill="x", padx=18, pady=(22, 4))

        ctk.CTkLabel(logo_frame,
                     text="◈  POSTURE OS",
                     font=ctk.CTkFont(family="Consolas", size=18, weight="bold"),
                     text_color=c["accent"]).pack(anchor="w")

        self.lbl_device_type = ctk.CTkLabel(
            logo_frame, text="No data loaded",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=c["sidebar_text"],
        )
        self.lbl_device_type.pack(anchor="w", pady=(2, 0))

        # Thin accent divider
        ctk.CTkFrame(self.sidebar, height=1, fg_color=c["accent"]).pack(
            fill="x", padx=18, pady=(10, 14))

        # ── Navigation ───────────────────────────────────────────
        ctk.CTkLabel(self.sidebar, text="NAVIGATION",
                     font=ctk.CTkFont(family="Consolas", size=9, weight="bold"),
                     text_color=c["sidebar_text"]).pack(anchor="w", padx=20, pady=(0, 4))

        nav_items = [
            ("monitor",   "▣", "MONITOR"),
            ("analysis",  "⌇", "ANALYSIS"),
            ("history",   "◉", "HISTORY"),
            ("jarvis",    "◆", "JARVIS SCAN"),
        ]
        for page_name, icon, label in nav_items:
            btn = NavButton(
                self.sidebar, text=label, icon=icon,
                text_color=c["sidebar_text"],
                command=lambda pn=page_name: self.switch_page(pn),
            )
            btn.pack(fill="x", padx=10, pady=2)
            self.nav_buttons[page_name] = btn

        ctk.CTkFrame(self.sidebar, height=1, fg_color=c["card_border"]).pack(
            fill="x", padx=18, pady=12)

        # ── Files section ─────────────────────────────────────────
        ctk.CTkLabel(self.sidebar, text="DATA FILES",
                     font=ctk.CTkFont(family="Consolas", size=9, weight="bold"),
                     text_color=c["sidebar_text"]).pack(anchor="w", padx=20, pady=(0, 4))

        self.lbl_status = ctk.CTkLabel(self.sidebar, text="⚪  Not connected",
                                        font=ctk.CTkFont(family="Consolas", size=10),
                                        text_color=c["text_secondary"])
        self.lbl_status.pack(anchor="w", padx=20, pady=(0, 6))

        for btn_text, cmd in [
            ("▷  Browse Files...",  self._browse_files),
            ("◈  Scan SD Card",     self._scan_sd),
            ("⌁  Connect Device",   self._connect_device),
        ]:
            ctk.CTkButton(
                self.sidebar, text=btn_text,
                font=ctk.CTkFont(family="Consolas", size=11),
                height=30, corner_radius=6, anchor="w",
                fg_color="transparent",
                text_color=c["sidebar_text"],
                hover_color=c["button_hover"],
                command=cmd,
            ).pack(fill="x", padx=10, pady=1)

        ctk.CTkFrame(self.sidebar, height=1, fg_color=c["card_border"]).pack(
            fill="x", padx=18, pady=10)

        ctk.CTkLabel(self.sidebar, text="LOADED SESSIONS",
                     font=ctk.CTkFont(family="Consolas", size=9, weight="bold"),
                     text_color=c["sidebar_text"]).pack(anchor="w", padx=20, pady=(0, 4))

        self.files_frame = ctk.CTkScrollableFrame(
            self.sidebar, fg_color="transparent",
        )
        self.files_frame.pack(fill="both", expand=True, padx=10, pady=(0, 5))

        self.lbl_no_files = ctk.CTkLabel(
            self.files_frame, text="No sessions loaded",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=c["sidebar_text"],
        )
        self.lbl_no_files.pack(pady=10)

        # ── Settings button at very bottom ───────────────────────
        ctk.CTkFrame(self.sidebar, height=1, fg_color=c["card_border"]).pack(
            fill="x", padx=18, pady=6)

        settings_btn = NavButton(
            self.sidebar, text="SETTINGS", icon="◌",
            text_color=c["sidebar_text"],
            command=lambda: self.switch_page("settings"),
        )
        settings_btn.pack(fill="x", padx=10, pady=(0, 14))
        self.nav_buttons["settings"] = settings_btn

        # ── Content area ─────────────────────────────────────────
        self.content = ctk.CTkFrame(self, fg_color=c["bg"], corner_radius=0)
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

    # ------------------------------------------------------------------
    # Pages
    # ------------------------------------------------------------------
    def _create_pages(self):
        page_classes = {
            "monitor":  DashboardPage,
            "analysis": TimelinePage,
            "history":  OverallPage,
            "jarvis":   JarvisScanPage,
            "settings": SettingsPage,
        }
        for name, cls in page_classes.items():
            frame = cls(self.content, self)
            frame.grid(row=0, column=0, sticky="nsew")
            self.pages[name] = frame

    def switch_page(self, page_name: str):
        if page_name not in self.pages:
            return
        c = self.tm.colors
        for name, btn in self.nav_buttons.items():
            btn.set_active(name == page_name, c)

        self.pages[page_name].tkraise()
        self.active_page_name = page_name
        if hasattr(self.pages[page_name], "refresh"):
            self.pages[page_name].refresh()

    # ------------------------------------------------------------------
    # File Loading
    # ------------------------------------------------------------------
    def _connect_device(self):
        if not HAS_SERIAL:
            messagebox.showinfo("PySerial Not Found",
                "The 'pyserial' package is needed for USB device connection.\n"
                "Use 'Browse Files' or 'Scan SD Card' instead.")
            return
        device = get_device()
        c = self.tm.colors
        self.lbl_status.configure(text="◉  Scanning...", text_color=c["accent"])
        self.update_idletasks()

        def do_connect():
            status = device.connect()
            if status == "CONNECTED":
                self.after(0, lambda: self._on_device_connected(device))
            else:
                self.after(0, lambda s=status: self._on_device_failed(s))

        threading.Thread(target=do_connect, daemon=True).start()

    def _on_device_connected(self, device):
        c = self.tm.colors
        self.lbl_status.configure(text=f"◉  Connected ({device.port_name})",
                                   text_color=c["success"])
        self.update_idletasks()

        def do_download():
            def progress_callback(filename, idx, total):
                self.after(0, lambda: self.lbl_status.configure(
                    text=f"⌁  Syncing: {idx}/{total}",
                    text_color=c["accent"],
                ))
            paths = device.download_all_files(CACHE_DIR, progress_callback=progress_callback)
            self.after(0, lambda: self._on_download_complete(device, paths))

        threading.Thread(target=do_download, daemon=True).start()

    def _on_download_complete(self, device, paths):
        c = self.tm.colors
        self.lbl_status.configure(
            text=f"◉  Synced ({device.port_name})",
            text_color=c["success"],
        )
        self._load_file_paths(paths, show_warning=False)

    def _on_device_failed(self, status: str):
        c = self.tm.colors
        msgs = {
            "PORT_BUSY":        "◉  Port busy (Serial Monitor open?)",
            "HANDSHAKE_FAILED": "◉  Handshake failed",
        }
        self.lbl_status.configure(
            text=msgs.get(status, "◉  Device not found"),
            text_color=c["danger"],
        )

    def _scan_sd(self):
        found = scan_for_csv_files()
        if found:
            self._load_file_paths(found)
        else:
            messagebox.showinfo("No Files Found",
                "No posture device CSV files found on removable drives.\n\n"
                "Try inserting your SD card or connecting via USB.")

    def _browse_files(self):
        paths = filedialog.askopenfilenames(
            title="Select Posture Device CSV Files",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
        )
        if paths:
            self._load_file_paths(list(paths))

    def _load_file_paths(self, paths: List[str], show_warning: bool = True):
        new_sessions = load_multiple_csvs(paths)
        if not new_sessions:
            if show_warning:
                messagebox.showwarning("No Valid Files",
                    "None of the selected files could be parsed as posture device logs.")
            return

        existing_names = {s.filename for s in self.sessions}
        for s in new_sessions:
            if s.filename not in existing_names:
                self.sessions.append(s)
                existing_names.add(s.filename)

        self.sessions.sort(key=lambda s: s.session_start or __import__("datetime").datetime.max)
        self._update_file_list()
        self._refresh_all_pages()

    def _update_file_list(self):
        c = self.tm.colors
        for child in self.files_frame.winfo_children():
            child.destroy()

        if not self.sessions:
            ctk.CTkLabel(self.files_frame, text="No sessions loaded",
                         font=ctk.CTkFont(family="Consolas", size=10),
                         text_color=c["sidebar_text"]).pack(pady=10)
            self.lbl_device_type.configure(text="No data loaded")
            return

        session = self.get_active_session()
        if session:
            self.lbl_device_type.configure(text=session.device_name)

        for i, s in enumerate(self.sessions):
            is_active = (i == self.active_session_idx)
            dev_label = "Back" if "Back" in s.device_name else "Wrist"
            prefix = "▶  " if is_active else "   "
            btn = ctk.CTkButton(
                self.files_frame,
                text=f"{prefix}{s.display_name}\n   [{dev_label}]",
                font=ctk.CTkFont(family="Consolas", size=9),
                anchor="w", height=34, corner_radius=6,
                fg_color=c["accent"] if is_active else "transparent",
                text_color="#ffffff" if is_active else c["sidebar_text"],
                hover_color=c["button_hover"],
                command=lambda idx=i: self._select_session(idx),
            )
            btn.pack(fill="x", pady=1)

    def _select_session(self, idx: int):
        self.active_session_idx = idx
        self._update_file_list()
        session = self.get_active_session()
        if session:
            self.lbl_device_type.configure(text=session.device_name)
        self._refresh_all_pages()

    def _refresh_all_pages(self):
        if self.active_page_name and self.active_page_name in self.pages:
            page = self.pages[self.active_page_name]
            if hasattr(page, "refresh"):
                page.refresh()

    def get_active_session(self) -> Optional[SessionData]:
        if 0 <= self.active_session_idx < len(self.sessions):
            return self.sessions[self.active_session_idx]
        return None

    # ------------------------------------------------------------------
    # Full UI rebuild (called after theme change)
    # ------------------------------------------------------------------
    def _rebuild_ui(self):
        for widget in self.winfo_children():
            widget.destroy()
        self.pages = {}
        self.nav_buttons = {}
        self._build_layout()
        self._create_pages()
        self._update_file_list()
        self.switch_page(self.active_page_name or "monitor")
        self.after(100, self._fix_titlebar)

    def _fix_titlebar(self):
        """Set Windows title bar color to match the sidebar via DWM API."""
        try:
            import ctypes
            hwnd = self.winfo_id()
            # DWMWA_USE_IMMERSIVE_DARK_MODE (attr 20): 1 = dark title bar text/buttons
            is_dark = ctypes.c_int(1)  # always dark title bar to match dark sidebar
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 20, ctypes.byref(is_dark), ctypes.sizeof(is_dark)
            )
            # DWMWA_CAPTION_COLOR (attr 35, Windows 11+): exact COLORREF (0x00BBGGRR)
            # Sidebar color is #0d1117 → R=0x0d G=0x11 B=0x17
            sidebar_hex = self.tm.colors.get("sidebar_bg", "#0d1117").lstrip("#")
            r = int(sidebar_hex[0:2], 16)
            g = int(sidebar_hex[2:4], 16)
            b = int(sidebar_hex[4:6], 16)
            colorref = ctypes.c_int(r | (g << 8) | (b << 16))
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 35, ctypes.byref(colorref), ctypes.sizeof(colorref)
            )
        except Exception:
            pass  # silently ignore on older Windows or non-Windows


if __name__ == "__main__":
    app = App()
    app.mainloop()
