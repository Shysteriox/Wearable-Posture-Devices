"""
Hand Replay Page — Animated 2D and 3D hand visualizations
with playback controls (play/pause, speed, scrubber).
"""
import math
import tkinter as tk
from typing import Optional

import customtkinter as ctk
import matplotlib
matplotlib.use("Agg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np

from theme import ThemeManager
from data_loader import SessionData


class HandReplayPage(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.tm = ThemeManager()

        # Playback state
        self._playing = False
        self._speed = 1
        self._frame_idx = 0
        self._timer_id = None
        self._session = None
        self._mode = "2d"  # "2d" or "3d"

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_empty()

    def _build_empty(self):
        for w in self.winfo_children():
            w.destroy()
        self._stop()
        c = self.tm.colors
        ctk.CTkLabel(self, text="✋ Hand Replay",
                     font=ctk.CTkFont(size=28, weight="bold"),
                     text_color=c["text_heading"]).grid(row=0, column=0, pady=(20, 5), sticky="w", padx=30)
        ctk.CTkLabel(self, text="Load a CSV file to replay your wrist movements.",
                     font=ctk.CTkFont(size=15),
                     text_color=c["text_secondary"]).grid(row=1, column=0, sticky="n", pady=40)

    def refresh(self):
        session = self.app.get_active_session()
        if session is None:
            self._build_empty()
            return
        self._session = session
        self._frame_idx = 0
        self._build_replay()

    def _build_replay(self):
        self._stop()
        for w in self.winfo_children():
            w.destroy()
        c = self.tm.colors

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=30, pady=(20, 5))
        ctk.CTkLabel(header, text="✋ Hand Replay",
                     font=ctk.CTkFont(size=28, weight="bold"),
                     text_color=c["text_heading"]).pack(side="left")

        # Mode toggle
        mode_frame = ctk.CTkFrame(header, fg_color="transparent")
        mode_frame.pack(side="right")
        self.btn_2d = ctk.CTkButton(mode_frame, text="2D View", width=80, height=30,
                                     corner_radius=8, font=ctk.CTkFont(size=12),
                                     fg_color=c["accent"] if self._mode == "2d" else c["card_bg"],
                                     command=lambda: self._set_mode("2d"))
        self.btn_2d.pack(side="left", padx=2)
        self.btn_3d = ctk.CTkButton(mode_frame, text="3D View", width=80, height=30,
                                     corner_radius=8, font=ctk.CTkFont(size=12),
                                     fg_color=c["accent"] if self._mode == "3d" else c["card_bg"],
                                     command=lambda: self._set_mode("3d"))
        self.btn_3d.pack(side="left", padx=2)

        # Visualization area
        self.viz_frame = ctk.CTkFrame(self, fg_color=c["card_bg"], corner_radius=12,
                                       border_width=1, border_color=c["card_border"])
        self.viz_frame.grid(row=1, column=0, padx=30, pady=10, sticky="nsew")
        self.grid_rowconfigure(1, weight=1)

        # Controls bar
        controls = ctk.CTkFrame(self, fg_color=c["card_bg"], corner_radius=12,
                                 border_width=1, border_color=c["card_border"], height=70)
        controls.grid(row=2, column=0, padx=30, pady=(0, 20), sticky="ew")
        controls.grid_propagate(False)

        # Play/Pause
        self.btn_play = ctk.CTkButton(controls, text="▶ Play", width=90, height=34,
                                       corner_radius=8, font=ctk.CTkFont(size=13, weight="bold"),
                                       fg_color=c["accent"],
                                       command=self._toggle_play)
        self.btn_play.pack(side="left", padx=(15, 10), pady=15)

        # Speed selector
        ctk.CTkLabel(controls, text="Speed:", font=ctk.CTkFont(size=11),
                     text_color=c["text_secondary"]).pack(side="left", padx=(10, 5))
        self.speed_var = ctk.StringVar(value="1x")
        speed_menu = ctk.CTkOptionMenu(controls, values=["1x", "2x", "5x", "10x"],
                                        variable=self.speed_var, width=70, height=30,
                                        command=self._on_speed_change)
        speed_menu.pack(side="left", padx=5)

        # Timeline scrubber
        total_frames = len(self._session.df) if self._session else 100
        self.scrubber = ctk.CTkSlider(controls, from_=0, to=max(total_frames - 1, 1),
                                       number_of_steps=max(total_frames - 1, 1),
                                       command=self._on_scrub)
        self.scrubber.set(0)
        self.scrubber.pack(side="left", fill="x", expand=True, padx=15)

        # Time display
        self.lbl_time = ctk.CTkLabel(controls, text="0.0s",
                                      font=ctk.CTkFont(size=12, weight="bold"),
                                      text_color=c["accent"])
        self.lbl_time.pack(side="right", padx=15)

        # Angle display
        self.lbl_angles = ctk.CTkLabel(controls, text="Up/Down: 0°  Left/Right: 0°",
                                        font=ctk.CTkFont(size=11),
                                        text_color=c["text_secondary"])
        self.lbl_angles.pack(side="right", padx=10)

        # Draw initial frame
        self._draw_frame()

    def _set_mode(self, mode):
        self._mode = mode
        self._build_replay()

    def _toggle_play(self):
        if self._playing:
            self._stop()
        else:
            self._play()

    def _play(self):
        self._playing = True
        c = self.tm.colors
        self.btn_play.configure(text="⏸ Pause", fg_color=c["warning"])
        self._tick()

    def _stop(self):
        self._playing = False
        if self._timer_id:
            self.after_cancel(self._timer_id)
            self._timer_id = None
        try:
            c = self.tm.colors
            self.btn_play.configure(text="▶ Play", fg_color=c["accent"])
        except Exception:
            pass

    def _tick(self):
        if not self._playing or not self._session:
            return
        total = len(self._session.df)
        self._frame_idx += 1
        if self._frame_idx >= total:
            self._frame_idx = 0
            self._stop()
            return
        self.scrubber.set(self._frame_idx)
        self._draw_frame()
        delay = max(10, int(100 / self._speed))
        self._timer_id = self.after(delay, self._tick)

    def _on_speed_change(self, val):
        self._speed = int(val.replace("x", ""))

    def _on_scrub(self, val):
        self._frame_idx = int(float(val))
        self._draw_frame()

    def _draw_frame(self):
        if not self._session or self._session.df.empty:
            return
        df = self._session.df
        idx = min(self._frame_idx, len(df) - 1)
        row = df.iloc[idx]
        pitch = float(row["pitch_diff"])
        yaw = float(row["yaw_diff"])
        elapsed = float(row["elapsed_sec"])
        vibe = int(row["vibra_active"])

        # Update labels
        self.lbl_time.configure(text=f"{elapsed:.0f}s")
        self.lbl_angles.configure(text=f"Up/Down: {pitch:.1f}°  Left/Right: {yaw:.1f}°")

        if self._mode == "2d":
            self._draw_2d(pitch, yaw, vibe)
        else:
            self._draw_3d(pitch, yaw, vibe)

    def _draw_2d(self, pitch: float, yaw: float, vibe: int):
        """Draw 2D side view and top view of the hand."""
        # Clear previous
        for w in self.viz_frame.winfo_children():
            w.destroy()

        c = self.tm.colors
        danger = vibe == 1

        frame = ctk.CTkFrame(self.viz_frame, fg_color="transparent")
        frame.pack(fill="both", expand=True)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        # Side view canvas
        side_frame = ctk.CTkFrame(frame, fg_color="transparent")
        side_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        ctk.CTkLabel(side_frame, text="Side View (Up/Down)",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=c["text"]).pack(pady=(5, 0))

        side_canvas = tk.Canvas(side_frame, bg=c["card_bg"], highlightthickness=0,
                                 width=350, height=350)
        side_canvas.pack(fill="both", expand=True, padx=20, pady=10)
        self._draw_side_hand(side_canvas, pitch, danger)

        # Top view canvas
        top_frame = ctk.CTkFrame(frame, fg_color="transparent")
        top_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        ctk.CTkLabel(top_frame, text="Top View (Left/Right)",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=c["text"]).pack(pady=(5, 0))

        top_canvas = tk.Canvas(top_frame, bg=c["card_bg"], highlightthickness=0,
                                width=350, height=350)
        top_canvas.pack(fill="both", expand=True, padx=20, pady=10)
        self._draw_top_hand(top_canvas, yaw, danger)

    def _draw_side_hand(self, canvas, pitch: float, danger: bool):
        """Draw a side-view hand/wrist that tilts based on pitch."""
        c = self.tm.colors
        canvas.update_idletasks()
        w = canvas.winfo_width() or 350
        h = canvas.winfo_height() or 350

        cx, cy = w // 2, h // 2 + 30
        color = c["hand_danger"] if danger else c["hand_safe"]

        # Draw reference lines
        canvas.create_line(20, cy, w - 20, cy, fill=c["grid"], dash=(4, 4))
        canvas.create_text(w - 30, cy - 10, text="0°", fill=c["text_secondary"], font=("Arial", 9))

        # Forearm (horizontal bar)
        canvas.create_rectangle(cx - 100, cy - 12, cx, cy + 12,
                                fill=c["card_bg"], outline=c["text_secondary"], width=1)

        # Hand — rotated polygon
        angle_rad = math.radians(-pitch)  # negative so up = up on screen
        hand_len = 80
        hand_w = 25

        # Hand points (relative to wrist joint at cx, cy)
        pts_raw = [
            (0, -hand_w), (hand_len, -hand_w * 0.8),
            (hand_len + 15, -hand_w * 0.3), (hand_len + 15, hand_w * 0.3),
            (hand_len, hand_w * 0.8), (0, hand_w),
        ]

        # Rotate around wrist joint
        pts = []
        for px, py in pts_raw:
            rx = px * math.cos(angle_rad) - py * math.sin(angle_rad)
            ry = px * math.sin(angle_rad) + py * math.cos(angle_rad)
            pts.extend([cx + rx, cy + ry])

        canvas.create_polygon(pts, fill=color, outline=c["hand_outline"], width=2, smooth=False)

        # Angle text
        canvas.create_text(cx, h - 30, text=f"{pitch:+.1f}°",
                          font=("Arial", 16, "bold"), fill=color)
        direction = "UP ↑" if pitch > 0 else "DOWN ↓" if pitch < 0 else "NEUTRAL"
        canvas.create_text(cx, h - 12, text=direction,
                          font=("Arial", 10), fill=c["text_secondary"])

    def _draw_top_hand(self, canvas, yaw: float, danger: bool):
        """Draw a top-view hand/wrist that tilts based on yaw."""
        c = self.tm.colors
        canvas.update_idletasks()
        w = canvas.winfo_width() or 350
        h = canvas.winfo_height() or 350

        cx, cy = w // 2, h // 2 + 30
        color = c["hand_danger"] if danger else c["hand_safe"]

        # Reference line
        canvas.create_line(cx, 20, cx, h - 20, fill=c["grid"], dash=(4, 4))
        canvas.create_text(cx + 15, 30, text="0°", fill=c["text_secondary"], font=("Arial", 9))

        # Forearm (vertical bar coming from bottom)
        canvas.create_rectangle(cx - 12, cy, cx + 12, cy + 100,
                                fill=c["card_bg"], outline=c["text_secondary"], width=1)

        # Hand — rotated polygon
        angle_rad = math.radians(yaw)
        hand_len = 80
        hand_w = 30

        # Hand points (relative to wrist, going upward)
        pts_raw = [
            (-hand_w, 0), (-hand_w * 0.8, -hand_len),
            (-hand_w * 0.3, -hand_len - 15), (hand_w * 0.3, -hand_len - 15),
            (hand_w * 0.8, -hand_len), (hand_w, 0),
        ]

        pts = []
        for px, py in pts_raw:
            rx = px * math.cos(angle_rad) - py * math.sin(angle_rad)
            ry = px * math.sin(angle_rad) + py * math.cos(angle_rad)
            pts.extend([cx + rx, cy + ry])

        canvas.create_polygon(pts, fill=color, outline=c["hand_outline"], width=2, smooth=False)

        # Fingers (small ovals at the tips)
        tip_x = cx + hand_len * math.sin(angle_rad) * 0.3
        tip_y = cy - hand_len * math.cos(angle_rad) * 0.3

        # Angle text
        canvas.create_text(cx, h - 30, text=f"{yaw:+.1f}°",
                          font=("Arial", 16, "bold"), fill=color)
        direction = "RIGHT →" if yaw > 0 else "← LEFT" if yaw < 0 else "CENTER"
        canvas.create_text(cx, h - 12, text=direction,
                          font=("Arial", 10), fill=c["text_secondary"])

    def _draw_3d(self, pitch: float, yaw: float, vibe: int):
        """Draw a 3D hand model using matplotlib."""
        for w in self.viz_frame.winfo_children():
            w.destroy()

        c = self.tm.colors
        self.tm.apply_matplotlib_style()
        danger = vibe == 1

        fig = Figure(figsize=(7, 5), dpi=100)
        fig.patch.set_facecolor(c["plot_face"])
        ax = fig.add_subplot(111, projection='3d')
        ax.set_facecolor(c["plot_bg"])

        color = c["hand_danger"] if danger else c["hand_safe"]

        # Build a simple low-poly hand shape
        pitch_rad = math.radians(-pitch)
        yaw_rad = math.radians(yaw)

        # Rotation matrices
        def rotate_pitch(pts, angle):
            cos_a, sin_a = math.cos(angle), math.sin(angle)
            return [(x, y * cos_a - z * sin_a, y * sin_a + z * cos_a) for x, y, z in pts]

        def rotate_yaw(pts, angle):
            cos_a, sin_a = math.cos(angle), math.sin(angle)
            return [(x * cos_a - y * sin_a, x * sin_a + y * cos_a, z) for x, y, z in pts]

        # Palm vertices (flat rectangle)
        palm = [
            (-1.5, 0, -0.15), (1.5, 0, -0.15),
            (1.5, 3, -0.15), (-1.5, 3, -0.15),
            (-1.5, 0, 0.15), (1.5, 0, 0.15),
            (1.5, 3, 0.15), (-1.5, 3, 0.15),
        ]

        # Finger stubs
        fingers = []
        for fx in [-1.0, -0.33, 0.33, 1.0]:
            finger = [
                (fx - 0.25, 3, -0.1), (fx + 0.25, 3, -0.1),
                (fx + 0.2, 4.2, -0.08), (fx - 0.2, 4.2, -0.08),
                (fx - 0.25, 3, 0.1), (fx + 0.25, 3, 0.1),
                (fx + 0.2, 4.2, 0.08), (fx - 0.2, 4.2, 0.08),
            ]
            fingers.extend(finger)

        # Thumb
        thumb = [
            (-1.5, 0.5, -0.1), (-1.5, 0.5, 0.1),
            (-2.5, 1.5, 0.1), (-2.5, 1.5, -0.1),
        ]

        all_pts = palm + fingers + thumb

        # Apply rotations (pitch around X, yaw around Z)
        all_pts = rotate_pitch(all_pts, pitch_rad)
        all_pts = rotate_yaw(all_pts, yaw_rad)

        # Draw palm faces
        def quad(pts, indices):
            return [[pts[i] for i in indices]]

        palm_faces = [
            [0, 1, 2, 3], [4, 5, 6, 7],  # top/bottom
            [0, 1, 5, 4], [2, 3, 7, 6],  # front/back
            [0, 3, 7, 4], [1, 2, 6, 5],  # sides
        ]
        for face_idx in palm_faces:
            verts = [[all_pts[i] for i in face_idx]]
            poly = Poly3DCollection(verts, alpha=0.6, facecolor=color, edgecolor=c["hand_outline"])
            ax.add_collection3d(poly)

        # Draw fingers
        n_palm = len(palm)
        for fi in range(4):
            base = n_palm + fi * 8
            for face_idx in palm_faces:
                try:
                    verts = [[all_pts[base + i] for i in face_idx]]
                    poly = Poly3DCollection(verts, alpha=0.5, facecolor=color, edgecolor=c["hand_outline"])
                    ax.add_collection3d(poly)
                except IndexError:
                    pass

        # Draw thumb
        thumb_start = n_palm + 32
        if thumb_start + 3 < len(all_pts):
            thumb_verts = [[all_pts[thumb_start + i] for i in range(4)]]
            poly = Poly3DCollection(thumb_verts, alpha=0.5, facecolor=color, edgecolor=c["hand_outline"])
            ax.add_collection3d(poly)

        # Forearm (static reference)
        arm_pts = [(-1.2, -3, -0.12), (1.2, -3, -0.12), (1.2, 0, -0.12), (-1.2, 0, -0.12)]
        arm_verts = [arm_pts]
        poly = Poly3DCollection(arm_verts, alpha=0.3, facecolor=c["text_secondary"], edgecolor=c["grid"])
        ax.add_collection3d(poly)

        # Axis setup
        ax.set_xlim(-4, 4)
        ax.set_ylim(-4, 5)
        ax.set_zlim(-3, 3)
        ax.set_xlabel("Left / Right", color=c["text_secondary"], fontsize=9)
        ax.set_ylabel("Forward", color=c["text_secondary"], fontsize=9)
        ax.set_zlabel("Up / Down", color=c["text_secondary"], fontsize=9)
        ax.view_init(elev=25, azim=-60)
        ax.tick_params(labelsize=7, colors=c["text_secondary"])

        # Title with angle info
        ax.set_title(f"Up/Down: {pitch:+.1f}°   Left/Right: {yaw:+.1f}°",
                    color=color, fontsize=13, pad=10)

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self.viz_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

    def destroy(self):
        self._stop()
        super().destroy()
