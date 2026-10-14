"""
Timeline Page — Spine Slouch, Shoulder Tilt, and (optionally) Neck Flexion
graphs for a single session with user-friendly labels.
"""
import customtkinter as ctk
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import numpy as np

from theme import ThemeManager
from data_loader import SessionData, calculate_stats


class TimelinePage(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.tm = ThemeManager()
        self._canvas_widget = None
        self._toolbar = None
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_empty()

    def _build_empty(self):
        for w in self.winfo_children():
            w.destroy()
        c = self.tm.colors
        ctk.CTkLabel(self, text="⏇  ANALYSIS",
                     font=ctk.CTkFont(family="Consolas", size=26, weight="bold"),
                     text_color=c["accent"]).grid(row=0, column=0, pady=(28, 5), sticky="w", padx=35)
        ctk.CTkLabel(self, text="Load a session CSV to see posture movement over time.",
                     font=ctk.CTkFont(family="Consolas", size=13),
                     text_color=c["text_secondary"]).grid(row=1, column=0, sticky="n", pady=50)

    def refresh(self):
        session = self.app.get_active_session()
        if session is None:
            self._build_empty()
            return
        self._build_timeline(session)

    def _build_timeline(self, session: SessionData):
        for w in self.winfo_children():
            w.destroy()
        c = self.tm.colors
        self.tm.apply_matplotlib_style()
        stats = calculate_stats(session)

        # Header
        ctk.CTkLabel(self, text="⏇  ANALYSIS",
                     font=ctk.CTkFont(family="Consolas", size=26, weight="bold"),
                     text_color=c["accent"]).grid(row=0, column=0,
                                                   pady=(28, 0), sticky="w", padx=35)
        info = f"{session.display_name}  |  Score: {stats.good_posture_pct}%"
        ctk.CTkLabel(self, text=info,
                     font=ctk.CTkFont(family="Consolas", size=11),
                     text_color=c["text_secondary"]).grid(row=1, column=0,
                                                           sticky="w", padx=35, pady=(0, 10))

        # Chart container
        chart_frame = ctk.CTkFrame(self, fg_color=c["card_bg"], corner_radius=12,
                                    border_width=1, border_color=c["card_border"])
        chart_frame.grid(row=2, column=0, padx=30, pady=(0, 20), sticky="nsew")
        self.grid_rowconfigure(2, weight=1)

        df = session.df
        x = df["elapsed_sec"].values
        pitch = df["pitch_diff"].values
        yaw = df["yaw_diff"].values
        vibe = df["vibra_active"].values

        is_back = (session.device_name == "Back Posture Corrector")
        # v4.1 logs have head (neck-relative angle) and nck (neck motor active)
        has_neck = is_back and "head" in df.columns and "nck" in df.columns
        pc = self.tm.get_plot_colors()

        # Number of subplots: 3 if neck data present, else 2
        n_plots = 3 if has_neck else 2
        fig = Figure(figsize=(10, 3 * n_plots), dpi=100)
        fig.patch.set_facecolor(c["plot_face"])

        # ── Graph A: Spine Slouch / Wrist Up-Down ──────────────
        ax1 = fig.add_subplot(n_plots, 1, 1)
        ax1.set_facecolor(c["plot_bg"])
        label_a = "Spine Slouch (Middle IMU)" if is_back else "Wrist bend"
        thresh_val_a = 18.0 if is_back else 30.0
        ax1.plot(x, pitch, color=pc["pitch_line"], linewidth=1.5, label=label_a)
        ax1.axhline(0, color=c["text_secondary"], linewidth=0.5, alpha=0.5)
        ax1.axhline(thresh_val_a, color=pc["threshold_line"], linestyle="--", linewidth=1.2,
                    alpha=0.7, label=f"Alert zone (\u00b1{thresh_val_a}\u00b0)")
        ax1.axhline(-thresh_val_a, color=pc["threshold_line"], linestyle="--", linewidth=1.2, alpha=0.7)
        self._shade_violations(ax1, x, pitch, vibe, thresh_val_a, -thresh_val_a, pc)

        ax1.set_ylabel("Angle (\u00b0)", color=c["text"], fontsize=11)
        title_a = "Spine Slouch" if is_back else "Bending Up \u2191  and  Down \u2193"
        ax1.set_title(title_a, color=c["text"], fontsize=13, pad=8)
        ax1.legend(loc="upper right", fontsize=9, framealpha=0.6)
        ax1.grid(True, color=c["grid"], linestyle=":", alpha=0.5)
        ax1.tick_params(colors=c["text_secondary"], labelsize=9)
        y_max = max(abs(pitch.max()), abs(pitch.min()), thresh_val_a + 5)
        ax1.set_ylim(-y_max - 5, y_max + 5)
        if is_back:
            ax1.text(x[0] - (x[-1] - x[0]) * 0.02, y_max * 0.7, "Upright",
                    fontsize=9, color=pc["pitch_line"], ha="right", alpha=0.7)
            ax1.text(x[0] - (x[-1] - x[0]) * 0.02, -y_max * 0.7, "Slouch \u2193",
                    fontsize=9, color=pc["pitch_line"], ha="right", alpha=0.7)
        else:
            ax1.text(x[0] - (x[-1] - x[0]) * 0.02, y_max * 0.7, "Up \u2191",
                    fontsize=9, color=pc["pitch_line"], ha="right", alpha=0.7)
            ax1.text(x[0] - (x[-1] - x[0]) * 0.02, -y_max * 0.7, "Down \u2193",
                    fontsize=9, color=pc["pitch_line"], ha="right", alpha=0.7)

        # ── Graph B: Shoulder Tilt / Wrist Left-Right ──────────
        ax2 = fig.add_subplot(n_plots, 1, 2, sharex=ax1)
        ax2.set_facecolor(c["plot_bg"])
        label_b = "Shoulder Tilt" if is_back else "Wrist tilt"
        thresh_val_b = 18.0 if is_back else 13.0
        ax2.plot(x, yaw, color=pc["yaw_line"], linewidth=1.5, label=label_b)
        ax2.axhline(0, color=c["text_secondary"], linewidth=0.5, alpha=0.5)
        ax2.axhline(thresh_val_b, color=pc["threshold_lr"], linestyle="--", linewidth=1.2,
                    alpha=0.7, label=f"Alert zone (\u00b1{thresh_val_b}\u00b0)")
        ax2.axhline(-thresh_val_b, color=pc["threshold_lr"], linestyle="--", linewidth=1.2, alpha=0.7)
        self._shade_violations(ax2, x, yaw, vibe, thresh_val_b, -thresh_val_b, pc)

        if not has_neck:
            ax2.set_xlabel("Time (seconds)", color=c["text"], fontsize=11)
        ax2.set_ylabel("Angle (\u00b0)", color=c["text"], fontsize=11)
        title_b = "Sideways Shoulder Tilt" if is_back else "Tilting Left \u2190  and  Right \u2192"
        ax2.set_title(title_b, color=c["text"], fontsize=13, pad=8)
        ax2.legend(loc="upper right", fontsize=9, framealpha=0.6)
        ax2.grid(True, color=c["grid"], linestyle=":", alpha=0.5)
        ax2.tick_params(colors=c["text_secondary"], labelsize=9)
        y_max_yaw = max(abs(yaw.max()), abs(yaw.min()), thresh_val_b + 5)
        ax2.set_ylim(-y_max_yaw - 3, y_max_yaw + 3)
        if is_back:
            ax2.text(x[0] - (x[-1] - x[0]) * 0.02, y_max_yaw * 0.7, "Tilt Left \u2190",
                    fontsize=9, color=pc["yaw_line"], ha="right", alpha=0.7)
            ax2.text(x[0] - (x[-1] - x[0]) * 0.02, -y_max_yaw * 0.7, "\u2192 Tilt Right",
                    fontsize=9, color=pc["yaw_line"], ha="right", alpha=0.7)
        else:
            ax2.text(x[0] - (x[-1] - x[0]) * 0.02, y_max_yaw * 0.7, "Right \u2192",
                    fontsize=9, color=pc["yaw_line"], ha="right", alpha=0.7)
            ax2.text(x[0] - (x[-1] - x[0]) * 0.02, -y_max_yaw * 0.7, "\u2190 Left",
                    fontsize=9, color=pc["yaw_line"], ha="right", alpha=0.7)

        # ── Graph C: Neck Flexion — only for v4.1 back files ───
        if has_neck:
            neck_data = df["head"].values
            nck_active = df["nck"].values
            thresh_neck = 18.0
            NECK_COLOR = "#00e5ff"       # cyan — distinct from back sensors
            NECK_THRESH_CLR = "#00838f"
            ax3 = fig.add_subplot(n_plots, 1, 3, sharex=ax1)
            ax3.set_facecolor(c["plot_bg"])
            ax3.plot(x, neck_data, color=NECK_COLOR, linewidth=1.5,
                     label="Neck Bend (Head relative to Spine)")
            ax3.axhline(0, color=c["text_secondary"], linewidth=0.5, alpha=0.5)
            ax3.axhline(thresh_neck,  color=NECK_THRESH_CLR, linestyle="--", linewidth=1.2,
                        alpha=0.7, label=f"Alert zone (\u00b1{thresh_neck}\u00b0)")
            ax3.axhline(-thresh_neck, color=NECK_THRESH_CLR, linestyle="--", linewidth=1.2, alpha=0.7)
            self._shade_violations(ax3, x, neck_data, nck_active, thresh_neck, -thresh_neck,
                                   {**pc, "threshold_line": NECK_THRESH_CLR})
            ax3.set_xlabel("Time (seconds)", color=c["text"], fontsize=11)
            ax3.set_ylabel("Angle (\u00b0)", color=c["text"], fontsize=11)
            ax3.set_title("Neck Flexion / Extension", color=c["text"], fontsize=13, pad=8)
            ax3.legend(loc="upper right", fontsize=9, framealpha=0.6)
            ax3.grid(True, color=c["grid"], linestyle=":", alpha=0.5)
            ax3.tick_params(colors=c["text_secondary"], labelsize=9)
            y_max_n = max(abs(neck_data.max()), abs(neck_data.min()), thresh_neck + 5)
            ax3.set_ylim(-y_max_n - 5, y_max_n + 5)
            ax3.text(x[0] - (x[-1] - x[0]) * 0.02,  y_max_n * 0.7, "Head Up",
                    fontsize=9, color=NECK_COLOR, ha="right", alpha=0.7)
            ax3.text(x[0] - (x[-1] - x[0]) * 0.02, -y_max_n * 0.7, "Head Down \u2193",
                    fontsize=9, color=NECK_COLOR, ha="right", alpha=0.7)

        fig.tight_layout(pad=2.0)

        # Embed in tkinter
        canvas = FigureCanvasTkAgg(fig, master=chart_frame)
        canvas.draw()

        toolbar_frame = ctk.CTkFrame(chart_frame, fg_color="transparent", height=30)
        toolbar_frame.pack(fill="x", padx=5)
        toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)
        toolbar.update()

        canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=(0, 5))

    def _shade_violations(self, ax, x, data, vibe, upper, lower, pc):
        """Shade regions where the vibration motor was active."""
        in_violation = False
        start_x = None
        for i in range(len(x)):
            if vibe[i] == 1 and not in_violation:
                in_violation = True
                start_x = x[i]
            elif vibe[i] == 0 and in_violation:
                in_violation = False
                ax.axvspan(start_x, x[i], alpha=0.15, color=pc["threshold_line"], linewidth=0)
        if in_violation and start_x is not None:
            ax.axvspan(start_x, x[-1], alpha=0.15, color=pc["threshold_line"], linewidth=0)
