"""
JARVIS Scan Page — Posture OS
Multi-panel diagnostic layout: stat cards, charts, index gauges, and findings grid.
"""
import tkinter as tk
from typing import List, Tuple
import customtkinter as ctk
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np

from theme import ThemeManager
from data_loader import SessionData, calculate_stats, SessionStats

SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "WARNING": 2, "CAUTION": 3, "NOMINAL": 4}


def _sev_color(severity: str, c: dict) -> str:
    return {"CRITICAL": c["danger"], "HIGH": "#ff7722",
            "WARNING": c["warning"], "CAUTION": c["accent"],
            "NOMINAL": c["success"]}.get(severity, c["text"])


# ---------------------------------------------------------------------------
# FindingRow — compact collapsible card
# ---------------------------------------------------------------------------
class FindingRow(ctk.CTkFrame):
    def __init__(self, parent, severity, title, value_str, detail, colors):
        super().__init__(parent, fg_color=colors["card_bg"], corner_radius=6,
                         border_width=1, border_color=colors["card_border"])
        self._expanded = False
        c = colors
        sc = _sev_color(severity, c)

        header = ctk.CTkFrame(self, fg_color="transparent", cursor="hand2")
        header.pack(fill="x", padx=6, pady=4)

        ctk.CTkLabel(header, text="⬤", font=ctk.CTkFont(size=7),
                     text_color=sc, width=12).pack(side="left", padx=(2, 3))
        ctk.CTkLabel(header, text=title,
                     font=ctk.CTkFont(family="Consolas", size=9, weight="bold"),
                     text_color=c["text"], anchor="w").pack(side="left", expand=True)
        self._arrow = ctk.CTkLabel(header, text="▸", font=ctk.CTkFont(size=10),
                                    text_color=c["text_secondary"], width=14)
        self._arrow.pack(side="right", padx=(2, 0))
        ctk.CTkLabel(header, text=value_str,
                     font=ctk.CTkFont(family="Consolas", size=9, weight="bold"),
                     text_color=sc, anchor="e", width=130).pack(side="right")

        self._detail = ctk.CTkFrame(self, fg_color=c["bg_secondary"], corner_radius=4)
        ctk.CTkFrame(self._detail, height=1, fg_color=sc).pack(fill="x", padx=6, pady=(4, 2))
        ctk.CTkLabel(self._detail, text=detail,
                     font=ctk.CTkFont(family="Consolas", size=9),
                     text_color=c["text"], wraplength=340, justify="left"
                     ).pack(anchor="w", padx=10, pady=(0, 8))

        for w in [header, self._arrow] + list(header.winfo_children()):
            w.bind("<Button-1>", lambda e: self.toggle())

    def toggle(self):
        self._expanded = not self._expanded
        if self._expanded:
            self._detail.pack(fill="x", padx=6, pady=(0, 6))
            self._arrow.configure(text="▾")
        else:
            self._detail.pack_forget()
            self._arrow.configure(text="▸")


# ---------------------------------------------------------------------------
# JARVIS Scan Page
# ---------------------------------------------------------------------------
class JarvisScanPage(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.tm = ThemeManager()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        self._build_empty()

    def _build_empty(self):
        for w in self.winfo_children():
            w.destroy()
        c = self.tm.colors
        ctk.CTkLabel(self, text="◆  JARVIS SCAN",
                     font=ctk.CTkFont(family="Consolas", size=26, weight="bold"),
                     text_color=c["accent"]).grid(row=0, column=0, pady=(28, 5), sticky="w", padx=35)
        ctk.CTkLabel(self, text="Load a session to run the automated diagnostic scan.",
                     font=ctk.CTkFont(family="Consolas", size=13),
                     text_color=c["text_secondary"]).grid(row=1, column=0, sticky="n", pady=50)

    def refresh(self):
        session = self.app.get_active_session()
        if session is None:
            self._build_empty()
            return
        self._run_and_display(session)

    # ---------------------------------------------------------------
    def _run_and_display(self, session: SessionData):
        for w in self.winfo_children():
            w.destroy()
        c = self.tm.colors
        stats = calculate_stats(session)
        is_back = (session.device_name == "Back Posture Corrector")
        df = session.df
        findings = self._run_scan(session, stats)

        counts = {}
        for sev, *_ in findings:
            counts[sev] = counts.get(sev, 0) + 1

        dur_min = max(stats.duration_seconds / 60, 0.01)
        sample_rate = max(stats.total_samples / max(stats.duration_seconds, 1), 1)

        # ── Row 0: Header ─────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=30, pady=(20, 0))
        hdr.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(hdr, text="◆  JARVIS SCAN",
                     font=ctk.CTkFont(family="Consolas", size=24, weight="bold"),
                     text_color=c["accent"]).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(hdr,
                     text=f"{session.display_name}  |  {session.device_name}  |  "
                          f"{stats.total_samples:,} samples  |  {len(findings)} findings",
                     font=ctk.CTkFont(family="Consolas", size=10),
                     text_color=c["text_secondary"]).grid(row=1, column=0, sticky="w", pady=(2, 0))

        btn_frame = ctk.CTkFrame(hdr, fg_color="transparent")
        btn_frame.grid(row=0, column=1, rowspan=2, sticky="e")
        ctk.CTkButton(btn_frame, text="↺  RE-SCAN", width=100, height=28,
                      font=ctk.CTkFont(family="Consolas", size=11), corner_radius=6,
                      fg_color=c["bg_secondary"], hover_color=c["button_hover"],
                      text_color=c["accent"],
                      command=lambda: self._run_and_display(session)).pack()

        # ── Row 1: Stat cards strip ────────────────────────────────
        strip = ctk.CTkFrame(self, fg_color="transparent")
        strip.grid(row=1, column=0, sticky="ew", padx=30, pady=(10, 6))
        for i in range(6):
            strip.grid_columnconfigure(i, weight=1)

        peak = abs(stats.min_pitch)

        # Compute longest bad streak
        longest_bad_sec = 0
        if all(col in df.columns for col in ["ctr", "lft", "rgt"]):
            try:
                viol_series = ((df["ctr"] + df["lft"] + df["rgt"]) > 0).tolist()
                cur_bad = max_bad = 0
                for v in viol_series:
                    if v:
                        cur_bad += 1; max_bad = max(max_bad, cur_bad)
                    else:
                        cur_bad = 0
                longest_bad_sec = max_bad / sample_rate
            except Exception:
                pass

        stat_cards = [
            ("COMPLIANCE",     f"{stats.good_posture_pct:.1f}%",
             c["success"] if stats.good_posture_pct >= 75 else c["warning"] if stats.good_posture_pct >= 50 else c["danger"]),
            ("ALERT DENSITY",  f"{stats.violation_count/dur_min:.2f}/min",
             c["success"] if stats.violation_count/dur_min < 0.5 else c["warning"] if stats.violation_count/dur_min < 2 else c["danger"]),
            ("PEAK ANGLE",     f"{peak:.1f}°",
             c["success"] if peak < 12 else c["warning"] if peak < 25 else c["danger"]),
            ("VIOLATIONS",     str(stats.violation_count),
             c["success"] if stats.violation_count < 5 else c["warning"] if stats.violation_count < 20 else c["danger"]),
            ("DURATION",
             f"{int(stats.duration_seconds//60)}m {int(stats.duration_seconds%60)}s",
             c["text"]),
            ("MAX STREAK",     f"{longest_bad_sec:.0f}s bad",
             c["success"] if longest_bad_sec < 15 else c["warning"] if longest_bad_sec < 60 else c["danger"]),
        ]
        for i, (label, value, color) in enumerate(stat_cards):
            card = ctk.CTkFrame(strip, fg_color=c["card_bg"], corner_radius=8,
                                border_width=1, border_color=c["card_border"])
            card.grid(row=0, column=i, padx=4, sticky="nsew")
            ctk.CTkLabel(card, text=value,
                         font=ctk.CTkFont(family="Consolas", size=18, weight="bold"),
                         text_color=color).pack(pady=(10, 0))
            ctk.CTkLabel(card, text=label,
                         font=ctk.CTkFont(family="Consolas", size=8),
                         text_color=c["text_secondary"]).pack(pady=(0, 8))

        # ── Row 2: Charts row ──────────────────────────────────────
        charts_row = ctk.CTkFrame(self, fg_color="transparent")
        charts_row.grid(row=2, column=0, sticky="ew", padx=30, pady=(0, 6))
        charts_row.grid_columnconfigure(0, weight=1)
        charts_row.grid_columnconfigure(1, weight=2)
        charts_row.grid_columnconfigure(2, weight=1)

        # Left chart: Violation breakdown bars
        left_chart = ctk.CTkFrame(charts_row, fg_color=c["card_bg"], corner_radius=10,
                                   border_width=1, border_color=c["card_border"])
        left_chart.grid(row=0, column=0, padx=(0, 5), sticky="nsew")
        self._draw_violation_bars(left_chart, stats, is_back, c)

        # Middle chart: Angle timeline
        mid_chart = ctk.CTkFrame(charts_row, fg_color=c["card_bg"], corner_radius=10,
                                  border_width=1, border_color=c["card_border"])
        mid_chart.grid(row=0, column=1, padx=5, sticky="nsew")
        self._draw_timeline(mid_chart, df, stats, is_back, c)

        # Right panel: Index gauges (progress bars)
        right_panel = ctk.CTkFrame(charts_row, fg_color=c["card_bg"], corner_radius=10,
                                    border_width=1, border_color=c["card_border"])
        right_panel.grid(row=0, column=2, padx=(5, 0), sticky="nsew")
        self._draw_index_panel(right_panel, stats, df, c)

        # ── Row 3: Findings grid (2 columns) ───────────────────────
        self.grid_rowconfigure(3, weight=1)
        findings_row = ctk.CTkFrame(self, fg_color="transparent")
        findings_row.grid(row=3, column=0, sticky="nsew", padx=30, pady=(0, 20))
        findings_row.grid_columnconfigure(0, weight=1)
        findings_row.grid_columnconfigure(1, weight=1)
        findings_row.grid_rowconfigure(1, weight=1)

        # Split findings: critical+high left, rest right
        left_findings  = [f for f in findings if f[0] in ("CRITICAL", "HIGH")]
        right_findings = [f for f in findings if f[0] not in ("CRITICAL", "HIGH")]

        for col_idx, (col_findings, col_label) in enumerate([
            (left_findings,  "⬤  CRITICAL  &  HIGH  PRIORITY"),
            (right_findings, "⬤  WARNING  /  CAUTION  /  NOMINAL"),
        ]):
            col_color = c["danger"] if col_idx == 0 else c["warning"]

            col_hdr = ctk.CTkLabel(findings_row, text=col_label,
                                    font=ctk.CTkFont(family="Consolas", size=9, weight="bold"),
                                    text_color=col_color)
            col_hdr.grid(row=0, column=col_idx, sticky="w",
                         padx=(0 if col_idx == 0 else 5, 5 if col_idx == 0 else 0),
                         pady=(4, 2))

            scroll = ctk.CTkScrollableFrame(findings_row, fg_color="transparent")
            scroll.grid(row=1, column=col_idx, sticky="nsew",
                        padx=(0 if col_idx == 0 else 4, 4 if col_idx == 0 else 0))
            scroll.grid_columnconfigure(0, weight=1)

            if not col_findings:
                ctk.CTkLabel(scroll,
                             text="No findings in this category.",
                             font=ctk.CTkFont(family="Consolas", size=10),
                             text_color=c["text_secondary"]).grid(row=0, column=0, pady=20)
            else:
                for i, (sev, title, value_str, detail) in enumerate(col_findings):
                    FindingRow(scroll, sev, title, value_str, detail, c
                               ).grid(row=i, column=0, sticky="ew", pady=2)

    # ── Chart helpers ────────────────────────────────────────────

    def _draw_violation_bars(self, parent, stats, is_back, c):
        ctk.CTkLabel(parent, text="VIOLATION BREAKDOWN",
                     font=ctk.CTkFont(family="Consolas", size=9, weight="bold"),
                     text_color=c["accent"]).pack(pady=(10, 4))

        if is_back:
            labels = ["SLOUCH", "TILT L", "TILT R"]
            values = [stats.violations_down, stats.violations_left, stats.violations_right]
            colors_list = [c["danger"], c["warning"], c["accent"]]
        else:
            labels = ["UP", "DOWN", "LEFT", "RIGHT"]
            values = [stats.violations_up, stats.violations_down,
                      stats.violations_left, stats.violations_right]
            colors_list = [c["danger"], c["warning"], c["accent"], c["success"]]

        fig, ax = plt.subplots(figsize=(2.8, 2.2))
        fig.patch.set_facecolor(c["card_bg"])
        ax.set_facecolor(c["plot_bg"] if "plot_bg" in c else c["bg_secondary"])

        bar_c = [col if v > 0 else c.get("grid", "#444") for col, v in zip(colors_list, values)]
        bars = ax.barh(labels, values, color=bar_c, height=0.5, edgecolor="none")

        for bar, val in zip(bars, values):
            if val > 0:
                ax.text(bar.get_width() + max(values) * 0.03,
                        bar.get_y() + bar.get_height() / 2,
                        str(val), va="center",
                        color=c["text"], fontsize=8, fontfamily="monospace")

        ax.set_xlim(0, max(max(values) * 1.25, 1))
        ax.tick_params(colors=c.get("text_secondary", "#888"), labelsize=8)
        ax.set_xlabel("Events", color=c.get("text_secondary", "#888"), fontsize=7)
        for spine in ax.spines.values():
            spine.set_color(c.get("grid", "#444"))
        ax.grid(True, axis="x", color=c.get("grid", "#444"), linestyle=":", alpha=0.4)

        plt.tight_layout(pad=0.4)
        cv = FigureCanvasTkAgg(fig, master=parent)
        cv.draw()
        cv.get_tk_widget().pack(fill="both", expand=True, padx=6, pady=(0, 8))
        plt.close(fig)

    def _draw_timeline(self, parent, df, stats, is_back, c):
        ctk.CTkLabel(parent, text="POSTURE ANGLE  ·  FULL SESSION",
                     font=ctk.CTkFont(family="Consolas", size=9, weight="bold"),
                     text_color=c["accent"]).pack(pady=(10, 4))

        pitch_col = next((col for col in ["mid", "pitch_diff"] if col in df.columns), None)

        fig, axes = plt.subplots(2 if is_back and "left" in df.columns else 1,
                                  1, figsize=(5.5, 2.8), sharex=True)
        if not isinstance(axes, np.ndarray):
            axes = [axes]
        fig.patch.set_facecolor(c["card_bg"])
        plot_bg = c.get("plot_bg", c.get("bg_secondary", "#111"))
        grid_c  = c.get("grid", "#333")
        accent  = c["accent"]
        danger  = c["danger"]
        warn    = c["warning"]
        txt     = c.get("text_secondary", "#888")

        # --- Top plot: pitch (slouch) ---
        ax0 = axes[0]
        ax0.set_facecolor(plot_bg)
        if pitch_col and len(df) > 2:
            x = np.arange(len(df))
            y = df[pitch_col].values.astype(float)
            ax0.plot(x, y, color=accent, linewidth=0.7, alpha=0.85)
            ax0.axhline(0, color=grid_c, linewidth=0.5)
            thresh = 18
            ax0.axhline(thresh, color=warn, linewidth=0.7, linestyle="--", alpha=0.7)
            ax0.axhline(-thresh, color=warn, linewidth=0.7, linestyle="--", alpha=0.7)
            # Shade violations
            if "ctr" in df.columns:
                try:
                    bad = ((df["ctr"] + df.get("lft", df["ctr"]*0) +
                            df.get("rgt", df["ctr"]*0)) > 0).values
                    ax0.fill_between(x, y.min()-2, y.max()+2,
                                     where=bad, color=danger, alpha=0.18, linewidth=0)
                except Exception:
                    pass
            ax0.set_ylabel("Slouch°", color=txt, fontsize=7)
        ax0.tick_params(colors=txt, labelsize=6)
        for sp in ax0.spines.values():
            sp.set_color(grid_c)
        ax0.grid(True, color=grid_c, linestyle=":", alpha=0.3)

        # --- Bottom plot: lateral (left/right) ---
        if len(axes) > 1:
            ax1 = axes[1]
            ax1.set_facecolor(plot_bg)
            if "left" in df.columns and "right" in df.columns:
                x = np.arange(len(df))
                lat = ((df["left"].values + df["right"].values) / 2).astype(float)
                ax1.plot(x, lat, color=warn, linewidth=0.7, alpha=0.85)
                ax1.axhline(0, color=grid_c, linewidth=0.5)
                ax1.axhline(18,  color=danger, linewidth=0.6, linestyle="--", alpha=0.6)
                ax1.axhline(-18, color=danger, linewidth=0.6, linestyle="--", alpha=0.6)
                ax1.fill_between(x, lat, 0, where=lat > 0,
                                 color=warn, alpha=0.12, linewidth=0, label="L")
                ax1.fill_between(x, lat, 0, where=lat < 0,
                                 color=accent, alpha=0.12, linewidth=0, label="R")
                ax1.set_ylabel("Lateral°", color=txt, fontsize=7)
            ax1.tick_params(colors=txt, labelsize=6)
            for sp in ax1.spines.values():
                sp.set_color(grid_c)
            ax1.grid(True, color=grid_c, linestyle=":", alpha=0.3)
            ax1.set_xlabel("Sample →", color=txt, fontsize=7)
        else:
            axes[0].set_xlabel("Sample →", color=txt, fontsize=7)

        plt.tight_layout(pad=0.4, h_pad=0.3)
        cv = FigureCanvasTkAgg(fig, master=parent)
        cv.draw()
        cv.get_tk_widget().pack(fill="both", expand=True, padx=6, pady=(0, 8))
        plt.close(fig)

    def _draw_index_panel(self, parent, stats, df, c):
        ctk.CTkLabel(parent, text="KEY INDICES",
                     font=ctk.CTkFont(family="Consolas", size=9, weight="bold"),
                     text_color=c["accent"]).pack(pady=(10, 6))

        pitch_col = next((col for col in ["mid", "pitch_diff"] if col in df.columns), None)

        # Compute indices
        stds = []
        if pitch_col and len(df) > 2:
            stds.append(float(df[pitch_col].std()))
        if "left" in df.columns and "right" in df.columns and len(df) > 2:
            stds.append(float(((df["left"] + df["right"]) / 2).std()))
        combined_std = sum(stds) / max(len(stds), 1) if stds else 0

        psi  = max(0.0, min(100.0, 100 - combined_std * 4))
        load = min(100.0, max(0.0,
                              (1 - stats.good_posture_pct / 100) * 55 +
                              (combined_std / 20) * 45))
        vl = stats.violations_left
        vr = stats.violations_right
        total_lat = max(vl + vr, 1)
        symm = (1.0 - abs(vl / total_lat - vr / total_lat)) * 100

        indices = [
            ("STABILITY  INDEX", psi,  100, c["success"] if psi > 70 else c["warning"] if psi > 40 else c["danger"]),
            ("SPINAL  LOAD",    load, 100, c["success"] if load < 20 else c["warning"] if load < 50 else c["danger"]),
            ("BILATERAL SYMM.", symm, 100, c["success"] if symm > 70 else c["warning"] if symm > 40 else c["danger"]),
        ]

        for label, value, max_val, color in indices:
            frame = ctk.CTkFrame(parent, fg_color=c.get("bg_secondary", c["card_bg"]),
                                  corner_radius=6)
            frame.pack(fill="x", padx=10, pady=4)

            top_row = ctk.CTkFrame(frame, fg_color="transparent")
            top_row.pack(fill="x", padx=8, pady=(6, 2))
            ctk.CTkLabel(top_row, text=label,
                         font=ctk.CTkFont(family="Consolas", size=9),
                         text_color=c.get("text_secondary", "#888")).pack(side="left")
            ctk.CTkLabel(top_row,
                         text=f"{value:.0f} / {max_val}",
                         font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
                         text_color=color).pack(side="right")

            bar = ctk.CTkProgressBar(frame, height=6, corner_radius=3,
                                      fg_color=c.get("card_border", "#333"),
                                      progress_color=color)
            bar.set(value / max_val)
            bar.pack(fill="x", padx=8, pady=(0, 8))

        # Severity count summary
        ctk.CTkFrame(parent, height=1, fg_color=c.get("card_border", "#333")
                     ).pack(fill="x", padx=10, pady=(6, 4))
        ctk.CTkLabel(parent, text="FINDING DISTRIBUTION",
                     font=ctk.CTkFont(family="Consolas", size=8, weight="bold"),
                     text_color=c.get("text_secondary", "#888")).pack(anchor="w", padx=10)

        # Mini bar chart of severity counts using matplotlib
        sev_order = ["CRITICAL", "HIGH", "WARNING", "CAUTION", "NOMINAL"]
        sev_colors_map = {
            "CRITICAL": c["danger"], "HIGH": "#ff7722",
            "WARNING": c["warning"], "CAUTION": c["accent"], "NOMINAL": c["success"],
        }

        fig, ax = plt.subplots(figsize=(2.4, 1.4))
        fig.patch.set_facecolor(c.get("card_bg", "#fff"))
        ax.set_facecolor(c.get("bg_secondary", "#eee"))

        # We don't have counts here — draw a placeholder pie from what we computed
        # The parent can pass counts if needed; for now show a donut of compliance
        good = stats.good_posture_pct
        bad  = 100 - good
        wedge_colors = [c["success"], c["danger"]]
        ax.pie([good, bad], colors=wedge_colors, startangle=90,
               wedgeprops=dict(width=0.45, edgecolor=c.get("card_bg", "#fff"), linewidth=1.5))
        ax.text(0, 0, f"{good:.0f}%", ha="center", va="center",
                color=c["success"] if good >= 75 else c["warning"],
                fontsize=10, fontweight="bold", fontfamily="monospace")

        plt.tight_layout(pad=0.1)
        cv = FigureCanvasTkAgg(fig, master=parent)
        cv.draw()
        cv.get_tk_widget().pack(pady=(2, 8))
        plt.close(fig)

    # ---------------------------------------------------------------
    # Scan engine
    # ---------------------------------------------------------------
    def _run_scan(self, session: SessionData, stats: SessionStats) -> List[Tuple]:
        findings = []
        df = session.df
        is_back = (session.device_name == "Back Posture Corrector")
        dur_min = max(stats.duration_seconds / 60, 0.01)
        total = max(stats.total_samples, 1)
        sample_rate = total / max(stats.duration_seconds, 1)

        def add(severity, title, value_str, detail):
            findings.append((severity, title, value_str, detail))

        pitch_col = next((c for c in ["mid", "pitch_diff"] if c in df.columns), None)
        left_col  = "left"  if "left"  in df.columns else None
        right_col = "right" if "right" in df.columns else None

        # ── COMPLIANCE ─────────────────────────────────────────────
        score = stats.good_posture_pct
        sev = ("CRITICAL" if score < 40 else "HIGH" if score < 60
               else "WARNING" if score < 75 else "CAUTION" if score < 87 else "NOMINAL")
        add(sev, "POSTURAL COMPLIANCE INDEX", f"{score:.1f}%",
            f"% of monitored time where ALL postural parameters were within safe thresholds.\n\n"
            f"  Your value : {score:.1f}%\n  Optimal    : > 87%\n\n"
            f"Below 75% indicates habitual postural strain. Lumbar intradiscal pressure "
            f"rises significantly with sustained forward flexion beyond 20°.")

        density = stats.violation_count / dur_min
        sev = ("CRITICAL" if density > 4 else "HIGH" if density > 2
               else "WARNING" if density > 1 else "CAUTION" if density > 0.3 else "NOMINAL")
        add(sev, "ALERT DENSITY INDEX", f"{density:.2f}  / min",
            f"Violation events per minute. High density = persistent bad posture (not isolated).\n\n"
            f"  Your rate : {density:.2f} / min\n  Optimal   : < 0.3 / min\n"
            f"  Total     : {stats.violation_count} events over {dur_min:.1f} minutes")

        add("NOMINAL", "SESSION DURATION",
            f"{int(stats.duration_seconds//60)}m {int(stats.duration_seconds%60)}s",
            f"Total actively-monitored recording time.\n\n"
            f"  Duration     : {stats.duration_seconds:.0f}s  ({dur_min:.1f} min)\n"
            f"  Samples      : {stats.total_samples:,}\n"
            f"  Sample rate  : {sample_rate:.1f} Hz\n\n"
            f"Aim for 20+ minutes per session for statistically robust data.")

        add("NOMINAL", "TOTAL SAMPLES LOGGED", f"{stats.total_samples:,}",
            f"Raw IMU sensor readings captured and filtered on-device.\n\n"
            f"  Samples    : {stats.total_samples:,}\n"
            f"  Duration   : {stats.duration_seconds:.0f}s\n"
            f"  Eff. rate  : {sample_rate:.1f} Hz\n\n"
            f"Each sample passes through a 5-point rolling median filter before comparison.")

        # ── BACK-SPECIFIC: FORWARD FLEXION ──────────────────────────
        if is_back:
            peak = abs(stats.min_pitch)
            sev = ("CRITICAL" if peak > 35 else "HIGH" if peak > 25
                   else "WARNING" if peak > 18 else "CAUTION" if peak > 10 else "NOMINAL")
            add(sev, "PEAK FORWARD FLEXION", f"{peak:.1f}°",
                f"Largest single forward lean angle recorded, relative to calibrated neutral.\n\n"
                f"  Your peak        : {peak:.1f}°\n  Alert threshold  : 18°\n"
                f"  Optimal peak     : < 12°\n\n"
                f"Flexion beyond 20° significantly increases lumbar intradiscal pressure. "
                f"Brief peaks are less harmful than sustained slouch.")

            mean_s = abs(stats.avg_pitch)
            sev = ("HIGH" if mean_s > 14 else "WARNING" if mean_s > 7
                   else "CAUTION" if mean_s > 3 else "NOMINAL")
            add(sev, "MEAN FORWARD DEVIATION", f"{mean_s:.1f}°",
                f"Average forward lean across the full session — reflects habitual posture.\n\n"
                f"  Your mean  : {mean_s:.1f}°\n  Optimal    : < 3°\n\n"
                f"High mean even without many violations means you're chronically near the threshold.")

            n_slouch = stats.violations_down
            sev = ("CRITICAL" if n_slouch > 60 else "HIGH" if n_slouch > 25
                   else "WARNING" if n_slouch > 10 else "CAUTION" if n_slouch > 3 else "NOMINAL")
            add(sev, "SLOUCH EVENT COUNT", f"{n_slouch}  events",
                f"Discrete instances where mid-spine flexion breached the 18° threshold.\n\n"
                f"  Slouch events : {n_slouch}\n"
                f"  Rate          : {n_slouch/dur_min:.2f} events/min\n"
                f"  As % of total : {n_slouch/max(stats.violation_count,1)*100:.0f}%")

            if pitch_col and len(df) > 2:
                std_p = float(df[pitch_col].std())
                sev = ("WARNING" if std_p > 10 else "CAUTION" if std_p > 5 else "NOMINAL")
                add(sev, "FLEXION VOLATILITY INDEX", f"σ = {std_p:.1f}°",
                    f"Standard deviation of mid-spine angle — high = erratic, unstable posture.\n\n"
                    f"  σ (std dev)  : {std_p:.1f}°\n  Optimal      : < 5°\n\n"
                    f"High volatility can indicate fidgeting, task-switching, or unstable chair.")

        # ── LATERAL ANALYSIS ─────────────────────────────────────────
        vl = stats.violations_left;  vr = stats.violations_right
        total_lat = max(vl + vr, 1)
        l_frac = vl / total_lat;  r_frac = vr / total_lat

        sev_l = ("HIGH" if vl > 30 else "WARNING" if vl > 10
                 else "CAUTION" if vl > 3 else "NOMINAL")
        add(sev_l, "LEFT TILT FREQUENCY", f"{vl}  events  ({l_frac*100:.0f}%)",
            f"Times left tilt exceeded 18° threshold.\n\n"
            f"  Left events  : {vl}  ({l_frac*100:.0f}% of lateral events)\n"
            f"  Right events : {vr}  ({r_frac*100:.0f}%)\n\n"
            f"{'Dominant left lean — check left elbow habit and desk symmetry.' if vl > vr else 'Left tilt is less dominant than right.'}")

        sev_r = ("HIGH" if vr > 30 else "WARNING" if vr > 10
                 else "CAUTION" if vr > 3 else "NOMINAL")
        add(sev_r, "RIGHT TILT FREQUENCY", f"{vr}  events  ({r_frac*100:.0f}%)",
            f"Times right tilt exceeded 18° threshold.\n\n"
            f"  Right events : {vr}  ({r_frac*100:.0f}%)\n  Left events  : {vl}  ({l_frac*100:.0f}%)\n\n"
            f"{'Dominant right lean — check mouse position and right armrest.' if vr > vl else 'Right tilt less dominant than left.'}")

        symm = (1.0 - abs(l_frac - r_frac)) * 100
        sev = ("HIGH" if symm < 30 else "WARNING" if symm < 55
               else "CAUTION" if symm < 75 else "NOMINAL")
        add(sev, "BILATERAL SYMMETRY SCORE", f"{symm:.0f}  / 100",
            f"How evenly lateral violations are split between left and right. 100 = perfectly even.\n\n"
            f"  Score      : {symm:.0f} / 100\n"
            f"  Left share : {l_frac*100:.0f}%  |  Right share : {r_frac*100:.0f}%\n"
            f"  Optimal    : > 75\n\n"
            f"Chronic unilateral loading is a risk factor for scoliotic adaptation.")

        if vl == 0 and vr == 0:
            bias_str, bias_sev = "BALANCED  —  ZERO LATERAL EVENTS", "NOMINAL"
        elif l_frac > 0.65:
            bias_str, bias_sev = f"LEFT-DOMINANT  ({l_frac*100:.0f}%)", "WARNING"
        elif r_frac > 0.65:
            bias_str, bias_sev = f"RIGHT-DOMINANT  ({r_frac*100:.0f}%)", "WARNING"
        else:
            bias_str, bias_sev = f"MIXED  L:{l_frac*100:.0f}% / R:{r_frac*100:.0f}%", "CAUTION"
        add(bias_sev, "LATERAL BIAS COEFFICIENT", bias_str,
            f"Overall directional preference for lateral deviation across the session.\n\n"
            f"  Dominant side : {'LEFT' if l_frac > r_frac else 'RIGHT' if vr > vl else 'NONE'}\n"
            f"  Confidence    : {max(l_frac, r_frac)*100:.0f}%\n"
            f"  Left events   : {vl}  |  Right events : {vr}")

        peak_lat = max(abs(stats.min_yaw), abs(stats.max_yaw))
        sev = ("HIGH" if peak_lat > 30 else "WARNING" if peak_lat > 18
               else "CAUTION" if peak_lat > 10 else "NOMINAL")
        add(sev, "PEAK LATERAL DEVIATION", f"{peak_lat:.1f}°",
            f"Largest single lateral tilt in either direction.\n\n"
            f"  Peak left  : {abs(stats.max_yaw):.1f}°\n"
            f"  Peak right : {abs(stats.min_yaw):.1f}°\n"
            f"  Threshold  : 18°  |  Optimal peak : < 12°")

        mean_lat = abs(stats.avg_yaw)
        sev = ("WARNING" if mean_lat > 10 else "CAUTION" if mean_lat > 4 else "NOMINAL")
        add(sev, "MEAN LATERAL DEVIATION", f"{mean_lat:.1f}°",
            f"Average lateral angle — a non-zero mean = persistent lean even without alerts.\n\n"
            f"  Your mean : {stats.avg_yaw:.1f}° ({'left' if stats.avg_yaw > 0 else 'right'})\n"
            f"  Optimal   : < 2°")

        if left_col and right_col and len(df) > 2:
            lat_std = float(((df[left_col] + df[right_col]) / 2).std())
            sev = ("WARNING" if lat_std > 8 else "CAUTION" if lat_std > 4 else "NOMINAL")
            add(sev, "LATERAL VOLATILITY INDEX", f"σ = {lat_std:.1f}°",
                f"Standard deviation of lateral angle — high = unstable side-to-side control.\n\n"
                f"  σ (std dev) : {lat_std:.1f}°\n  Optimal     : < 4°")

        # ── TEMPORAL / STREAK ─────────────────────────────────────
        if all(col in df.columns for col in ["ctr", "lft", "rgt"]):
            try:
                viol_series = ((df["ctr"] + df["lft"] + df["rgt"]) > 0).tolist()
                cur_bad = max_bad = 0
                cur_good = max_good = 0
                for v in viol_series:
                    if v:
                        cur_bad += 1; max_bad = max(max_bad, cur_bad); cur_good = 0
                    else:
                        cur_good += 1; max_good = max(max_good, cur_good); cur_bad = 0
                bad_sec  = max_bad / sample_rate
                good_sec = max_good / sample_rate

                sev = ("CRITICAL" if bad_sec > 120 else "HIGH" if bad_sec > 60
                       else "WARNING" if bad_sec > 30 else "CAUTION" if bad_sec > 10 else "NOMINAL")
                add(sev, "LONGEST VIOLATION STREAK", f"{bad_sec:.0f}  seconds",
                    f"Longest uninterrupted run of bad posture without correction.\n\n"
                    f"  Longest bad streak   : {bad_sec:.0f}s\n"
                    f"  Longest clean streak : {good_sec:.0f}s\n"
                    f"  Optimal max bad      : < 10s\n\n"
                    f"Long streaks suggest the corrective feedback is being ignored or habituated.")

                sev_g = ("NOMINAL" if good_sec > 120 else "CAUTION" if good_sec > 60 else "WARNING")
                add(sev_g, "LONGEST CLEAN STREAK",
                    f"{good_sec:.0f}s  ({good_sec/60:.1f} min)",
                    f"Longest sustained good-posture window — your best performance this session.\n\n"
                    f"  Your best streak : {good_sec:.0f}s  ({good_sec/60:.1f} min)\n"
                    f"  Optimal target   : > 300s  (5 min clean windows)")
            except Exception:
                pass

        if pitch_col and len(df) > 10:
            try:
                mid_idx = len(df) // 2
                early_mean = float(df[pitch_col].iloc[:mid_idx].mean())
                late_mean  = float(df[pitch_col].iloc[mid_idx:].mean())
                delta = late_mean - early_mean
                degrading = delta < -1 if is_back else delta > 1
                improving = delta > 1 if is_back else delta < -1
                trend = "DEGRADING" if degrading else "IMPROVING" if improving else "STABLE"
                sev   = "WARNING"  if degrading else "NOMINAL"  if improving else "CAUTION"
                add(sev, "SESSION POSTURE TREND", trend,
                    f"Compares first half vs second half average angle to detect fatigue.\n\n"
                    f"  Early half mean : {early_mean:+.1f}°\n"
                    f"  Late half mean  : {late_mean:+.1f}°\n"
                    f"  Delta           : {delta:+.1f}°  "
                    f"({'fatigue pattern' if degrading else 'improving' if improving else 'consistent'})\n\n"
                    f"Degrading trend = postural fatigue. Consider a mid-session standing break.")
            except Exception:
                pass

        # ── STABILITY & COMPOSITE ─────────────────────────────────
        stds = []
        if pitch_col and len(df) > 2: stds.append(float(df[pitch_col].std()))
        if left_col and right_col and len(df) > 2:
            stds.append(float(((df[left_col] + df[right_col]) / 2).std()))
        if stds:
            combined_std = sum(stds) / len(stds)
            psi = max(0.0, min(100.0, 100 - combined_std * 4))
            sev = ("NOMINAL" if psi > 75 else "CAUTION" if psi > 55
                   else "WARNING" if psi > 35 else "HIGH")
            add(sev, "POSTURAL STABILITY INDEX", f"{psi:.0f}  / 100",
                f"Composite stability score from combined angle standard deviations. Higher = better.\n\n"
                f"  Your PSI     : {psi:.0f} / 100\n  Combined σ   : {combined_std:.1f}°\n"
                f"  Optimal PSI  : > 75")

            load = min(100.0, max(0.0,
                                  (1 - score / 100) * 55 + (combined_std / 20) * 45))
            sev = ("CRITICAL" if load > 75 else "HIGH" if load > 50
                   else "WARNING" if load > 30 else "CAUTION" if load > 15 else "NOMINAL")
            add(sev, "SPINAL LOAD ESTIMATE", f"{load:.0f}  / 100",
                f"Composite index estimating cumulative mechanical burden on the spine.\n\n"
                f"  Load index : {load:.0f} / 100\n  Optimal    : < 15\n\n"
                f"NOTE: Estimation model — use as a relative comparator, not a clinical value.")

        # ── NECK ─────────────────────────────────────────────────
        if "head" in df.columns and "nck" in df.columns:
            try:
                v_nck = int(df["nck"].sum())
                nck_density = v_nck / dur_min
                neck_vals = df["head"].dropna()

                sev = ("CRITICAL" if v_nck > 50 else "HIGH" if v_nck > 20
                       else "WARNING" if v_nck > 8 else "CAUTION" if v_nck > 2 else "NOMINAL")
                add(sev, "NECK FLEXION ALERT COUNT", f"{v_nck}  events",
                    f"Times neck forward flexion (dH − dM) exceeded the neck threshold.\n\n"
                    f"  Neck alerts : {v_nck}\n  Rate        : {nck_density:.2f} / min\n\n"
                    f"Chronic neck flexion associated with cervical strain and headaches.")

                sev = ("HIGH" if nck_density > 2 else "WARNING" if nck_density > 0.5
                       else "CAUTION" if nck_density > 0.1 else "NOMINAL")
                add(sev, "NECK ALERT DENSITY", f"{nck_density:.2f}  / min",
                    f"Neck violation rate per minute.\n\n"
                    f"  Your rate : {nck_density:.2f} / min\n  Optimal   : < 0.1 / min")

                if len(neck_vals) > 2:
                    mean_nck = float(neck_vals.mean())
                    peak_nck = float(neck_vals.max())
                    sev = ("WARNING" if abs(mean_nck) > 10 else "CAUTION" if abs(mean_nck) > 5 else "NOMINAL")
                    add(sev, "MEAN NECK DEVIATION", f"{mean_nck:+.1f}°",
                        f"Average head angle deviation from calibration baseline.\n\n"
                        f"  Mean deviation : {mean_nck:+.1f}°\n"
                        f"  Peak deviation : {peak_nck:.1f}°\n  Optimal mean   : < ±5°")

                    if pitch_col and len(df) > 2:
                        diff = float((df["head"] - df[pitch_col]).mean())
                        sev = ("WARNING" if abs(diff) > 15 else "CAUTION" if abs(diff) > 8 else "NOMINAL")
                        add(sev, "NECK-SPINE DIFFERENTIAL", f"{diff:+.1f}°  avg",
                            f"Average difference between head and spine flexion — "
                            f"measures how much the neck compensates independently.\n\n"
                            f"  Differential : {diff:+.1f}°\n  Optimal      : < ±8°")
            except Exception:
                pass

        # ── WRIST-SPECIFIC ────────────────────────────────────────
        if not is_back:
            vu = stats.violations_up
            vd = stats.violations_down
            sev = ("HIGH" if vu > 20 else "WARNING" if vu > 8 else "CAUTION" if vu > 2 else "NOMINAL")
            add(sev, "DORSAL EXTENSION EVENTS", f"{vu}  events",
                f"Times wrist dorsal extension exceeded the alert threshold.\n\n"
                f"  Extension events : {vu}\n  Total violations : {stats.violation_count}\n\n"
                f"Risk factor for extensor tendinopathy and carpal tunnel syndrome.")

            sev = ("HIGH" if vd > 20 else "WARNING" if vd > 8 else "CAUTION" if vd > 2 else "NOMINAL")
            add(sev, "PALMAR FLEXION EVENTS", f"{vd}  events",
                f"Times wrist palmar flexion exceeded the alert threshold.\n\n"
                f"  Flexion events   : {vd}\n  Total violations : {stats.violation_count}\n\n"
                f"Compresses the carpal tunnel and stresses the flexor tendons.")

        return sorted(findings, key=lambda f: SEVERITY_ORDER.get(f[0], 99))
