"""
Monitor Page — Posture OS
HUD-style dashboard: score gauge, violation breakdown, session stats, recommendations.
"""
import math
import tkinter as tk
from typing import Optional

import customtkinter as ctk

from theme import ThemeManager
from data_loader import SessionData, calculate_stats, aggregate_stats, SessionStats


class DashboardPage(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.tm = ThemeManager()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_empty_state()

    def _build_empty_state(self):
        for w in self.winfo_children():
            w.destroy()
        c = self.tm.colors
        ctk.CTkLabel(self, text="▣  MONITOR",
                     font=ctk.CTkFont(family="Consolas", size=26, weight="bold"),
                     text_color=c["accent"]).grid(row=0, column=0, pady=(28, 5), sticky="w", padx=35)
        ctk.CTkLabel(self,
                     text="Load a session CSV to view posture analysis.",
                     font=ctk.CTkFont(family="Consolas", size=13),
                     text_color=c["text_secondary"]).grid(row=1, column=0, sticky="n", pady=50)

    def refresh(self):
        session = self.app.get_active_session()
        if session is None:
            self._build_empty_state()
            return
        self._build_dashboard(session)

    def _build_dashboard(self, session: SessionData):
        for w in self.winfo_children():
            w.destroy()
        c = self.tm.colors
        stats = calculate_stats(session)

        # ── Header ──────────────────────────────────────────────
        ctk.CTkLabel(self, text="▣  MONITOR",
                     font=ctk.CTkFont(family="Consolas", size=26, weight="bold"),
                     text_color=c["accent"]).grid(row=0, column=0, columnspan=4,
                                                   pady=(28, 2), sticky="w", padx=35)
        info_text = (
            f"{session.display_name}  |  Device: {session.device_name}  |  "
            f"Duration: {self._fmt_duration(stats.duration_seconds)}"
        )
        ctk.CTkLabel(self, text=info_text,
                     font=ctk.CTkFont(family="Consolas", size=11),
                     text_color=c["text_secondary"]).grid(row=1, column=0, columnspan=4,
                                                           sticky="w", padx=35, pady=(0, 16))

        # 4-column layout: 3 left content cols + 1 right diagnostic col
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)
        self.grid_columnconfigure(3, weight=0, minsize=230)
        self.grid_rowconfigure(2, weight=0)
        self.grid_rowconfigure(3, weight=1)

        # ── Top Row: Gauge | Violations | Stats ──────────────────
        score_card = ctk.CTkFrame(self, fg_color=c["card_bg"], corner_radius=12,
                                   border_width=1, border_color=c["card_border"])
        score_card.grid(row=2, column=0, padx=(35, 6), pady=8, sticky="nsew")
        self._draw_score_gauge(score_card, stats.good_posture_pct)

        dir_card = ctk.CTkFrame(self, fg_color=c["card_bg"], corner_radius=12,
                                 border_width=1, border_color=c["card_border"])
        dir_card.grid(row=2, column=1, padx=6, pady=8, sticky="nsew")
        self._draw_direction_heatmap(dir_card, stats)

        stat_card = ctk.CTkFrame(self, fg_color=c["card_bg"], corner_radius=12,
                                  border_width=1, border_color=c["card_border"])
        stat_card.grid(row=2, column=2, padx=(6, 6), pady=8, sticky="nsew")
        self._draw_quick_stats(stat_card, stats, session)

        # ── Bottom: Recommendations ──────────────────────────────
        rec_card = ctk.CTkFrame(self, fg_color=c["card_bg"], corner_radius=12,
                                 border_width=1, border_color=c["card_border"])
        rec_card.grid(row=3, column=0, columnspan=3, padx=(35, 6), pady=(4, 28), sticky="nsew")
        self._draw_recommendations(rec_card, stats, session)

        # ── Right: Diagnostic Readout (spans both rows) ───────────
        diag_card = ctk.CTkFrame(self, fg_color=c["card_bg"], corner_radius=12,
                                  border_width=1, border_color=c["card_border"])
        diag_card.grid(row=2, column=3, rowspan=2, padx=(0, 35), pady=(8, 28), sticky="nsew")
        self._draw_diagnostic_readout(diag_card, stats, session)

    # ── Score Gauge ─────────────────────────────────────────────
    def _draw_score_gauge(self, parent, score: float):
        c = self.tm.colors
        ctk.CTkLabel(parent, text="POSTURE SCORE",
                     font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
                     text_color=c["text_secondary"]).pack(pady=(16, 4))

        canvas = tk.Canvas(parent, width=190, height=185,
                           bg=c["card_bg"], highlightthickness=0)
        canvas.pack(pady=4)

        cx, cy, r = 95, 105, 75
        score_color = (c["success"] if score >= 70
                       else c["warning"] if score >= 40
                       else c["danger"])

        # Background ring
        canvas.create_arc(cx - r, cy - r, cx + r, cy + r,
                          start=0, extent=180, style="arc",
                          outline=c["grid"], width=14)
        # Score arc
        extent = (score / 100) * 180
        canvas.create_arc(cx - r, cy - r, cx + r, cy + r,
                          start=180, extent=-extent, style="arc",
                          outline=score_color, width=14)

        # Inner concentric ring (HUD feel)
        r2 = r - 20
        canvas.create_arc(cx - r2, cy - r2, cx + r2, cy + r2,
                          start=180, extent=180, style="arc",
                          outline=c["card_border"], width=1)

        canvas.create_text(cx, cy - 18, text=f"{score:.0f}%",
                           font=("Consolas", 30, "bold"), fill=score_color)
        canvas.create_text(cx, cy + 12, text="GOOD POSTURE",
                           font=("Consolas", 9), fill=c["text_secondary"])

        # Grade
        if score >= 90:   grade, note = "A+", "EXCELLENT"
        elif score >= 80: grade, note = "A",  "GREAT"
        elif score >= 70: grade, note = "B",  "GOOD"
        elif score >= 50: grade, note = "C",  "NEEDS WORK"
        else:             grade, note = "D",  "POOR"

        ctk.CTkLabel(parent,
                     text=f"GRADE  {grade}  —  {note}",
                     font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
                     text_color=score_color).pack(pady=(0, 16))

    # ── Violation Breakdown ─────────────────────────────────────
    def _draw_direction_heatmap(self, parent, stats: SessionStats):
        c = self.tm.colors
        ctk.CTkLabel(parent, text="VIOLATION BREAKDOWN",
                     font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
                     text_color=c["text_secondary"]).pack(pady=(16, 8))

        canvas = tk.Canvas(parent, width=190, height=165,
                           bg=c["card_bg"], highlightthickness=0)
        canvas.pack(pady=2)

        cx, cy = 95, 82
        total_v = max(stats.violation_count, 1)

        is_back = (getattr(self.app.get_active_session(), "device_name", "") == "Back Posture Corrector")

        if is_back:
            directions = [
                ("SLOUCH",       stats.violations_down,  cx, cy + 52),
                ("TILT  LEFT",   stats.violations_left,  cx - 62, cy),
                ("TILT  RIGHT",  stats.violations_right, cx + 62, cy),
            ]
            # Check for neck violations
            session = self.app.get_active_session()
            if session and "nck" in session.df.columns:
                v_neck = int(session.df["nck"].sum())
                if v_neck > 0:
                    directions.append(("NECK", v_neck, cx, cy - 52))
        else:
            directions = [
                ("UP",    stats.violations_up,    cx, cy - 50),
                ("DOWN",  stats.violations_down,  cx, cy + 50),
                ("LEFT",  stats.violations_left,  cx - 58, cy),
                ("RIGHT", stats.violations_right, cx + 58, cy),
            ]

        # Center dot
        canvas.create_oval(cx - 6, cy - 6, cx + 6, cy + 6,
                           fill=c["success"], outline="")

        for label, count, x, y in directions:
            pct = (count / total_v) * 100 if total_v > 0 else 0
            if pct > 30:
                color, size = c["danger"], 12
            elif pct > 10:
                color, size = c["warning"], 11
            else:
                color, size = c["text_secondary"], 10

            canvas.create_text(x, y, text=label,
                               font=("Consolas", size, "bold"), fill=color)
            if count > 0:
                canvas.create_text(x, y + 14, text=f"{count}  ({pct:.0f}%)",
                                   font=("Consolas", 8), fill=color)

        worst_color = c["danger"] if stats.worst_direction != "None" else c["success"]
        ctk.CTkLabel(parent,
                     text=f"WORST:  {stats.worst_direction.upper()}",
                     font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
                     text_color=worst_color).pack(pady=(4, 16))

    # ── Quick Stats ─────────────────────────────────────────────
    def _draw_quick_stats(self, parent, stats: SessionStats, session: SessionData):
        c = self.tm.colors
        ctk.CTkLabel(parent, text="SESSION  STATS",
                     font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
                     text_color=c["text_secondary"]).pack(pady=(16, 10))

        is_back = (session.device_name == "Back Posture Corrector")
        has_neck = is_back and "nck" in session.df.columns

        if is_back:
            items = [
                ("Samples",        str(stats.total_samples)),
                ("Violations",     str(stats.violation_count)),
                ("Score",          f"{stats.good_posture_pct}%"),
                ("Peak Slouch",    f"{stats.min_pitch}°"),
                ("Peak Tilt L",    f"{stats.max_yaw}°"),
                ("Peak Tilt R",    f"{stats.min_yaw}°"),
                ("Avg Slouch",     f"{stats.avg_pitch}°"),
            ]
            if has_neck:
                v_neck = int(session.df["nck"].sum())
                items.append(("Neck Violations", str(v_neck)))
        else:
            items = [
                ("Samples",        str(stats.total_samples)),
                ("Violations",     str(stats.violation_count)),
                ("Score",          f"{stats.good_posture_pct}%"),
                ("Peak Up",        f"{stats.max_pitch}°"),
                ("Peak Down",      f"{stats.min_pitch}°"),
                ("Peak Right",     f"{stats.max_yaw}°"),
                ("Peak Left",      f"{stats.min_yaw}°"),
                ("Avg Vertical",   f"{stats.avg_pitch}°"),
                ("Avg Lateral",    f"{stats.avg_yaw}°"),
            ]

        for label, value in items:
            row = ctk.CTkFrame(parent, fg_color=c["bg_secondary"], corner_radius=6, height=26)
            row.pack(fill="x", padx=12, pady=2)
            row.pack_propagate(False)
            ctk.CTkLabel(row, text=label,
                         font=ctk.CTkFont(family="Consolas", size=10),
                         text_color=c["text_secondary"]).pack(side="left", padx=8)
            ctk.CTkLabel(row, text=value,
                         font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
                         text_color=c["accent"]).pack(side="right", padx=8)

        ctk.CTkLabel(parent, text="").pack(pady=6)

    # ── Recommendations ─────────────────────────────────────────
    def _draw_recommendations(self, parent, stats: SessionStats, session: SessionData):
        c = self.tm.colors
        ctk.CTkLabel(parent, text="⌇  DIAGNOSTICS  &  RECOMMENDATIONS",
                     font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
                     text_color=c["accent"]).pack(pady=(16, 8), padx=20, anchor="w")

        is_back = (session.device_name == "Back Posture Corrector")
        recs = []

        if stats.good_posture_pct >= 90:
            recs.append(("✓", c["success"], "Excellent session. Posture is well within safe range."))
        elif stats.good_posture_pct >= 70:
            recs.append(("◈", c["accent"],  "Good overall. Minor improvements can further reduce strain."))

        if is_back:
            if stats.violations_down > 5:
                recs.append(("⚠", c["danger"],
                             "High slouch count — raise your monitor to eye level and roll shoulders back."))
            if stats.violations_left > 5:
                recs.append(("⚠", c["warning"],
                             "Frequent left tilt — check if you're resting on your left elbow."))
            if stats.violations_right > 5:
                recs.append(("⚠", c["warning"],
                             "Frequent right tilt — your mouse may be too far from your body."))
            if session and "nck" in session.df.columns:
                v_neck = int(session.df["nck"].sum())
                if v_neck > 5:
                    recs.append(("⚠", c["danger"],
                                 "Neck bent forward frequently — raise screen or reduce screen time."))
        else:
            if stats.violations_down > stats.violations_up:
                recs.append(("⚠", c["warning"],
                             "Wrist bends downward often — raise keyboard or lower chair."))
            if stats.violations_up > stats.violations_down:
                recs.append(("⚠", c["warning"],
                             "Wrist over-extended upward — consider a wrist rest."))
            if stats.violations_right > 5:
                recs.append(("⚠", c["warning"], "Right tilt frequent — mouse may be placed too far."))
            if stats.violations_left > 5:
                recs.append(("⚠", c["warning"], "Left tilt frequent — keyboard may be off-center."))

        if stats.violation_count == 0:
            recs.append(("✓", c["success"], "Zero violations recorded. Perfect form this session."))

        if not recs:
            recs.append(("◉", c["text_secondary"],
                         "Continue monitoring. Consistency builds long-term posture health."))

        for icon, color, text in recs:
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=2)
            ctk.CTkLabel(row, text=icon, font=ctk.CTkFont(family="Consolas", size=12),
                         text_color=color, width=20).pack(side="left")
            ctk.CTkLabel(row, text=text, font=ctk.CTkFont(family="Consolas", size=11),
                         text_color=c["text"], wraplength=700, justify="left").pack(
                         side="left", padx=8)

        ctk.CTkLabel(parent, text="").pack(pady=6)

    # ── Diagnostic Readout ──────────────────────────────────────
    def _draw_diagnostic_readout(self, parent, stats: SessionStats, session: SessionData):
        """JARVIS-style terminal readout with computed postural metrics."""
        import numpy as np
        c = self.tm.colors
        is_back = (session.device_name == "Back Posture Corrector")
        df = session.df
        total = max(stats.total_samples, 1)
        dur_min = max(stats.duration_seconds / 60, 0.01)

        # ── Header ─────────────────────────────────────────────
        ctk.CTkLabel(parent, text="◈  DIAGNOSTIC READOUT",
                     font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
                     text_color=c["accent"]).pack(anchor="w", padx=14, pady=(14, 2))
        ctk.CTkFrame(parent, height=1, fg_color=c["accent"]).pack(fill="x", padx=14, pady=(0, 8))

        def metric_row(label, value, color=None, bar_pct=None):
            """Helper to draw one stat row with optional mini bar."""
            color = color or c["text"]
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=2)
            ctk.CTkLabel(row, text=label,
                         font=ctk.CTkFont(family="Consolas", size=9),
                         text_color=c["text_secondary"], anchor="w", width=138).pack(side="left")
            ctk.CTkLabel(row, text=value,
                         font=ctk.CTkFont(family="Consolas", size=9, weight="bold"),
                         text_color=color, anchor="e").pack(side="right")
            if bar_pct is not None:
                bar_frame = ctk.CTkFrame(parent, fg_color=c["bg_secondary"], corner_radius=2, height=3)
                bar_frame.pack(fill="x", padx=12, pady=(0, 1))
                bar_frame.pack_propagate(False)
                fill_w = max(int(bar_pct * 180), 2)
                ctk.CTkFrame(bar_frame, fg_color=color, corner_radius=2,
                             width=fill_w, height=3).place(x=0, y=0)

        def section(title):
            ctk.CTkLabel(parent, text=f"── {title} ──",
                         font=ctk.CTkFont(family="Consolas", size=8, weight="bold"),
                         text_color=c["text_secondary"]).pack(anchor="w", padx=12, pady=(10, 2))

        # ── POSTURAL COMPLIANCE ─────────────────────────────────
        section("COMPLIANCE")
        good_pct  = stats.good_posture_pct / 100
        bad_pct   = 1 - good_pct
        metric_row("COMPLIANT TIME",   f"{stats.good_posture_pct:.1f}%",
                   c["success"] if good_pct >= 0.7 else c["warning"], good_pct)
        metric_row("VIOLATION TIME",   f"{bad_pct*100:.1f}%",
                   c["danger"] if bad_pct > 0.3 else c["text_secondary"], bad_pct)

        # ── LATERAL BIAS ────────────────────────────────────────
        section("LATERAL BIAS")
        vl = stats.violations_left
        vr = stats.violations_right
        total_lat = max(vl + vr, 1)
        l_frac = vl / total_lat
        r_frac = vr / total_lat

        if vl == 0 and vr == 0:
            bias_str, bias_color = "NEUTRAL  —  BALANCED", c["success"]
        elif l_frac > 0.6:
            bias_str = f"LEFT  ({l_frac*100:.0f}% of tilts)"
            bias_color = c["warning"]
        elif r_frac > 0.6:
            bias_str = f"RIGHT  ({r_frac*100:.0f}% of tilts)"
            bias_color = c["warning"]
        else:
            bias_str = f"MIXED  L:{l_frac*100:.0f}%  R:{r_frac*100:.0f}%"
            bias_color = c["accent"]

        metric_row("DOMINANT LEAN",  bias_str, bias_color)

        # Bilateral symmetry score (0=perfectly asymmetric, 1=perfectly symmetric)
        symmetry = 1.0 - abs(l_frac - r_frac)
        sym_color = c["success"] if symmetry > 0.7 else c["warning"] if symmetry > 0.4 else c["danger"]
        metric_row("BILATERAL SYMM.", f"{symmetry*100:.0f} / 100", sym_color, symmetry)

        # ── TEMPORAL ANALYSIS ───────────────────────────────────
        section("TEMPORAL ANALYSIS")
        alert_density = stats.violation_count / dur_min
        metric_row("ALERT DENSITY",   f"{alert_density:.1f}  /min",
                   c["danger"] if alert_density > 2 else c["warning"] if alert_density > 0.5 else c["success"])

        if is_back:
            slouch_events = stats.violations_down
            metric_row("SLOUCH EVENTS",  str(slouch_events),
                       c["danger"] if slouch_events > 20 else c["warning"] if slouch_events > 5 else c["success"])

        # ── DEVIATION STATS ─────────────────────────────────────
        section("DEVIATION STATS")
        if not df.empty and "pitch_diff" in df.columns:
            pitch_vals = df["pitch_diff"].dropna()
            if len(pitch_vals) > 1:
                std_p = float(pitch_vals.std())
                mean_p = float(pitch_vals.mean())
                metric_row("MEAN FLEX. DEV.",  f"{mean_p:+.1f}°", c["text"])
                metric_row("FLEX. STD. DEV.",  f"{std_p:.1f}°",
                           c["warning"] if std_p > 8 else c["text"])

        if not df.empty and "yaw_diff" in df.columns:
            yaw_vals = df["yaw_diff"].dropna()
            if len(yaw_vals) > 1:
                std_y = float(yaw_vals.std())
                metric_row("LAT. STD. DEV.",   f"{std_y:.1f}°",
                           c["warning"] if std_y > 6 else c["text"])

        # Postural Stability Index — lower std = more stable (inverted, 0-100)
        if not df.empty and "pitch_diff" in df.columns and len(df) > 1:
            combined_std = float(df["pitch_diff"].std())
            if "yaw_diff" in df.columns:
                combined_std = (combined_std + float(df["yaw_diff"].std())) / 2
            psi = max(0, min(100, 100 - combined_std * 5))
            psi_color = c["success"] if psi > 70 else c["warning"] if psi > 40 else c["danger"]
            metric_row("STABILITY INDEX",  f"{psi:.0f} / 100", psi_color, psi / 100)

        # ── NECK (v4.1 only) ────────────────────────────────────
        if is_back and "head" in df.columns and "nck" in df.columns:
            section("NECK TELEMETRY")
            neck_vals = df["head"].dropna()
            v_nck = int(df["nck"].sum())
            nck_density = v_nck / dur_min
            metric_row("NECK ALERTS",     str(v_nck),
                       c["danger"] if v_nck > 10 else c["warning"] if v_nck > 3 else c["success"])
            metric_row("NECK ALERT RATE", f"{nck_density:.1f}  /min",
                       c["danger"] if nck_density > 1 else c["text"])
            if len(neck_vals) > 1:
                metric_row("MEAN NECK DEV.", f"{float(neck_vals.mean()):+.1f}°", c["text"])

        # ── ASSESSMENT NOTE ─────────────────────────────────────
        ctk.CTkFrame(parent, height=1, fg_color=c["card_border"]).pack(fill="x", padx=14, pady=(12, 6))
        ctk.CTkLabel(parent, text="ASSESSMENT",
                     font=ctk.CTkFont(family="Consolas", size=8, weight="bold"),
                     text_color=c["text_secondary"]).pack(anchor="w", padx=14)

        # Generate a one-line nerdy assessment
        score = stats.good_posture_pct
        if score >= 90:
            note = "Postural parameters within optimal range. No corrective action required."
        elif score >= 75:
            note = "Minor deviations detected. Ergonomic adjustments recommended."
        elif score >= 50:
            if vl > vr:
                note = "Significant left-lateral bias. Check workstation symmetry."
            elif vr > vl:
                note = "Significant right-lateral bias. Check mouse/keyboard positioning."
            else:
                note = "Elevated flexion burden. Raise monitor or take movement breaks."
        else:
            note = "High violation density. Immediate ergonomic review advised."

        ctk.CTkLabel(parent, text=note,
                     font=ctk.CTkFont(family="Consolas", size=9),
                     text_color=c["text_secondary"],
                     wraplength=200, justify="left").pack(anchor="w", padx=14, pady=(4, 14))

    @staticmethod
    def _fmt_duration(seconds: float) -> str:
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        return f"{h}h {m}m {s}s" if h > 0 else f"{m}m {s}s"
