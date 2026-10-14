"""
History Page — Posture OS
Aggregated trends, session list, and score comparisons across all loaded data.
"""
import customtkinter as ctk
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from theme import ThemeManager
from data_loader import calculate_stats, aggregate_stats


class OverallPage(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.tm = ThemeManager()
        self._canvas_widget = None
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_empty()

    def _build_empty(self):
        for w in self.winfo_children():
            w.destroy()
        c = self.tm.colors
        ctk.CTkLabel(self, text="◉  HISTORY",
                     font=ctk.CTkFont(family="Consolas", size=26, weight="bold"),
                     text_color=c["accent"]).grid(row=0, column=0, pady=(28, 5), sticky="w", padx=35)
        ctk.CTkLabel(self, text="Load multiple sessions to view posture trends and comparisons.",
                     font=ctk.CTkFont(family="Consolas", size=13),
                     text_color=c["text_secondary"]).grid(row=1, column=0, sticky="n", pady=50)

    def refresh(self):
        if not self.app.sessions:
            self._build_empty()
            return
        self._build_overview()

    def _build_overview(self):
        for w in self.winfo_children():
            w.destroy()
        c = self.tm.colors
        self.tm.apply_matplotlib_style()

        sessions = self.app.sessions
        agg = aggregate_stats(sessions)

        # Header
        ctk.CTkLabel(self, text="◉  HISTORY",
                     font=ctk.CTkFont(family="Consolas", size=26, weight="bold"),
                     text_color=c["accent"]).grid(row=0, column=0, columnspan=2,
                                                   pady=(28, 5), sticky="w", padx=35)

        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=1)

        # --- Summary cards row ---
        cards_frame = ctk.CTkFrame(self, fg_color="transparent")
        cards_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=30, pady=10)
        for i in range(4):
            cards_frame.grid_columnconfigure(i, weight=1)

        wear_h = int(agg.total_wear_seconds // 3600)
        wear_m = int((agg.total_wear_seconds % 3600) // 60)
        wear_str = f"{wear_h}h {wear_m}m" if wear_h > 0 else f"{wear_m}m"

        summary_items = [
            ("SESSIONS",        str(agg.total_sessions),           c["accent"]),
            ("TOTAL WEAR TIME", wear_str,                          c["accent_secondary"]),
            ("OVERALL SCORE",   f"{agg.overall_good_pct}%",
             c["success"] if agg.overall_good_pct >= 70 else c["warning"]),
            ("TOTAL VIOLATIONS", str(agg.total_violations),
             c["danger"] if agg.total_violations > 0 else c["success"]),
        ]
        for i, (label, value, color) in enumerate(summary_items):
            card = ctk.CTkFrame(cards_frame, fg_color=c["card_bg"], corner_radius=10,
                                border_width=1, border_color=c["card_border"])
            card.grid(row=0, column=i, padx=5, pady=5, sticky="nsew")
            ctk.CTkLabel(card, text=value,
                         font=ctk.CTkFont(family="Consolas", size=24, weight="bold"),
                         text_color=color).pack(pady=(12, 2))
            ctk.CTkLabel(card, text=label,
                         font=ctk.CTkFont(family="Consolas", size=10),
                         text_color=c["text_secondary"]).pack(pady=(0, 12))

        # --- Charts ---
        chart_frame = ctk.CTkFrame(self, fg_color=c["card_bg"], corner_radius=12,
                                    border_width=1, border_color=c["card_border"])
        chart_frame.grid(row=2, column=0, padx=(30, 10), pady=(5, 20), sticky="nsew")

        fig = Figure(figsize=(7, 4.5), dpi=100)
        fig.patch.set_facecolor(c["plot_face"])

        # Trend chart (top)
        ax1 = fig.add_subplot(211)
        ax1.set_facecolor(c["plot_bg"])
        scores = agg.session_scores
        if len(scores) > 1:
            x_labels = [f"S{i+1}" for i in range(len(scores))]
            y_vals = [s[1] for s in scores]
            ax1.plot(x_labels, y_vals, color=c["accent"], linewidth=2, marker="o", markersize=6)
            ax1.fill_between(x_labels, y_vals, alpha=0.15, color=c["accent"])
            ax1.axhline(70, color=c["success"], linestyle="--", alpha=0.5, label="Good (70%)")
        elif len(scores) == 1:
            ax1.bar(["Session 1"], [scores[0][1]], color=c["accent"], width=0.4)
        ax1.set_ylabel("Score %", color=c["text"], fontsize=10)
        ax1.set_title("Posture Score Trend", color=c["text"], fontsize=12, pad=8)
        ax1.set_ylim(0, 105)
        ax1.grid(True, color=c["grid"], linestyle=":", alpha=0.5)
        ax1.tick_params(colors=c["text_secondary"], labelsize=9)

        # Violations by direction (bottom)
        ax2 = fig.add_subplot(212)
        ax2.set_facecolor(c["plot_bg"])
        # Detect device type from first session
        is_back = any(s.device_name == "Back Posture Corrector" for s in sessions)
        if is_back:
            dirs   = ["Slouch", "Tilt L", "Tilt R"]
            counts = [agg.violations_down, agg.violations_left, agg.violations_right]
        else:
            dirs   = ["Up", "Down", "Left", "Right"]
            counts = [agg.violations_up, agg.violations_down, agg.violations_left, agg.violations_right]
        bar_colors = [c["danger"] if v > 0 else c["grid"] for v in counts]
        ax2.barh(dirs, counts, color=bar_colors, height=0.5)
        ax2.set_xlabel("Violations", color=c["text"], fontsize=10)
        ax2.set_title("Problem Directions  (All Sessions)", color=c["text"], fontsize=12, pad=8)
        ax2.grid(True, axis="x", color=c["grid"], linestyle=":", alpha=0.5)
        ax2.tick_params(colors=c["text_secondary"], labelsize=9)

        fig.tight_layout(pad=2.0)

        canvas = FigureCanvasTkAgg(fig, master=chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

        # --- Session list (right panel) ---
        list_frame = ctk.CTkFrame(self, fg_color=c["card_bg"], corner_radius=12,
                                   border_width=1, border_color=c["card_border"])
        list_frame.grid(row=2, column=1, padx=(10, 30), pady=(5, 20), sticky="nsew")

        ctk.CTkLabel(list_frame, text="SESSION  LIST",
                     font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
                     text_color=c["text_secondary"]).pack(pady=(12, 5), padx=12, anchor="w")

        scroll = ctk.CTkScrollableFrame(list_frame, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=5, pady=(0, 10))

        for i, session in enumerate(sessions):
            stats = calculate_stats(session)
            score_color = c["success"] if stats.good_posture_pct >= 70 else \
                          c["warning"] if stats.good_posture_pct >= 40 else c["danger"]

            row = ctk.CTkFrame(scroll, fg_color=c["bg_secondary"], corner_radius=8, height=50)
            row.pack(fill="x", pady=2, padx=3)
            row.pack_propagate(False)

            # Score badge
            ctk.CTkLabel(row, text=f"{stats.good_posture_pct:.0f}%",
                         font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
                         text_color=score_color, width=52).pack(side="left", padx=(10, 5))

            # Session info
            info_frame = ctk.CTkFrame(row, fg_color="transparent")
            info_frame.pack(side="left", fill="x", expand=True, padx=5)
            ctk.CTkLabel(info_frame, text=session.display_name,
                         font=ctk.CTkFont(family="Consolas", size=10),
                         text_color=c["text"]).pack(anchor="w")

            dur_m = int(stats.duration_seconds // 60)
            dur_s = int(stats.duration_seconds % 60)
            ctk.CTkLabel(info_frame,
                         text=f"{dur_m}m {dur_s}s  |  {stats.violation_count} violations  |  {session.device_name}",
                         font=ctk.CTkFont(family="Consolas", size=9),
                         text_color=c["text_secondary"]).pack(anchor="w")

            # View button
            ctk.CTkButton(row, text="▷", width=36, height=26,
                          font=ctk.CTkFont(family="Consolas", size=11), corner_radius=6,
                          fg_color=c["accent"],
                          command=lambda idx=i: self._view_session(idx),
                          ).pack(side="right", padx=10)

    def _view_session(self, idx: int):
        self.app._select_session(idx)
        self.app.switch_page("analysis")
