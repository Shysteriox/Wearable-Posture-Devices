"""
Raw Data Page — Scrollable table of CSV data with filters and export.
"""
import os
from tkinter import filedialog

import customtkinter as ctk

from theme import ThemeManager
from data_loader import SessionData


class RawDataPage(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.tm = ThemeManager()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._show_violations_only = False
        self._build_empty()

    def _build_empty(self):
        for w in self.winfo_children():
            w.destroy()
        c = self.tm.colors
        ctk.CTkLabel(self, text="📋 Raw Data",
                     font=ctk.CTkFont(size=28, weight="bold"),
                     text_color=c["text_heading"]).grid(row=0, column=0, pady=(20, 5), sticky="w", padx=30)
        ctk.CTkLabel(self, text="Load a CSV file to view the raw sensor data.",
                     font=ctk.CTkFont(size=15),
                     text_color=c["text_secondary"]).grid(row=1, column=0, sticky="n", pady=40)

    def refresh(self):
        session = self.app.get_active_session()
        if session is None:
            self._build_empty()
            return
        self._build_table(session)

    def _build_table(self, session: SessionData):
        for w in self.winfo_children():
            w.destroy()
        c = self.tm.colors

        # Header row
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=30, pady=(20, 5))

        ctk.CTkLabel(header, text="📋 Raw Data",
                     font=ctk.CTkFont(size=28, weight="bold"),
                     text_color=c["text_heading"]).pack(side="left")

        # Export button
        ctk.CTkButton(header, text="💾 Export CSV", width=120, height=30,
                      corner_radius=8, font=ctk.CTkFont(size=12),
                      fg_color=c["accent"],
                      command=lambda: self._export(session)
                      ).pack(side="right", padx=5)

        # Filter toggle
        filter_text = "Show All" if self._show_violations_only else "Violations Only"
        ctk.CTkButton(header, text=f"🔍 {filter_text}", width=130, height=30,
                      corner_radius=8, font=ctk.CTkFont(size=12),
                      fg_color=c["card_bg"], text_color=c["text"],
                      command=lambda: self._toggle_filter(session)
                      ).pack(side="right", padx=5)

        # Info
        df = session.df
        if self._show_violations_only:
            df = df[df["vibra_active"] == 1]

        ctk.CTkLabel(header, text=f"  {len(df)} rows",
                     font=ctk.CTkFont(size=12),
                     text_color=c["text_secondary"]).pack(side="right", padx=10)

        # Table container
        table_frame = ctk.CTkFrame(self, fg_color=c["card_bg"], corner_radius=12,
                                    border_width=1, border_color=c["card_border"])
        table_frame.grid(row=1, column=0, padx=30, pady=(5, 20), sticky="nsew")

        # Column headers
        col_header = ctk.CTkFrame(table_frame, fg_color=c["bg_secondary"], corner_radius=0, height=35)
        col_header.pack(fill="x", padx=2, pady=(2, 0))
        col_header.pack_propagate(False)

        columns = [
            ("Time (s)", 100),
            ("Up/Down (°)", 120),
            ("Left/Right (°)", 130),
            ("Motor Active", 110),
            ("Status", 100),
        ]
        for col_name, width in columns:
            ctk.CTkLabel(col_header, text=col_name, width=width,
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color=c["text"]).pack(side="left", padx=8)

        # Scrollable data rows
        scroll = ctk.CTkScrollableFrame(table_frame, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=2, pady=2)

        # Limit rows to prevent UI lag
        max_rows = 500
        display_df = df.head(max_rows)

        for _, row in display_df.iterrows():
            elapsed = float(row["elapsed_sec"])
            pitch = float(row["pitch_diff"])
            yaw = float(row["yaw_diff"])
            vibe = int(row["vibra_active"])

            is_violation = vibe == 1
            row_bg = c["danger_bg"] if is_violation else "transparent"

            row_frame = ctk.CTkFrame(scroll, fg_color=row_bg, corner_radius=4, height=28)
            row_frame.pack(fill="x", pady=1)
            row_frame.pack_propagate(False)

            text_color = c["danger"] if is_violation else c["text"]

            vals = [
                (f"{elapsed:.1f}", 100),
                (f"{pitch:+.1f}", 120),
                (f"{yaw:+.1f}", 130),
                ("YES" if vibe else "no", 110),
                ("⚠️ VIOLATION" if is_violation else "✅ OK", 100),
            ]
            for val, width in vals:
                ctk.CTkLabel(row_frame, text=val, width=width,
                             font=ctk.CTkFont(size=11),
                             text_color=text_color).pack(side="left", padx=8)

        if len(df) > max_rows:
            ctk.CTkLabel(scroll, text=f"... showing {max_rows} of {len(df)} rows ...",
                         font=ctk.CTkFont(size=11),
                         text_color=c["text_secondary"]).pack(pady=10)

    def _toggle_filter(self, session):
        self._show_violations_only = not self._show_violations_only
        self._build_table(session)

    def _export(self, session: SessionData):
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")],
            initialfile=f"export_{session.filename}",
        )
        if path:
            df = session.df.copy()
            df.columns = ["Time (s)", "Up/Down Angle", "Left/Right Angle", "Motor Active"]
            df.to_csv(path, index=False)
