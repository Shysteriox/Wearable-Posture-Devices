"""
Data Loader for Wrist Posture Visualizer
Handles CSV parsing, SD card scanning, statistics, and multi-session aggregation.
"""
import os
import re
import ctypes
import platform
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

import pandas as pd


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

@dataclass
class SessionData:
    """Represents one CSV recording session from the wrist device."""
    file_path: str
    session_start: Optional[datetime]
    device_name: str
    df: pd.DataFrame
    filename: str = ""

    def __post_init__(self):
        if not self.filename:
            self.filename = os.path.basename(self.file_path)

    @property
    def elapsed_seconds(self) -> float:
        """Total duration of the recording in seconds."""
        if self.df.empty:
            return 0.0
        return float(self.df["elapsed_sec"].max() - self.df["elapsed_sec"].min())

    @property
    def display_name(self) -> str:
        """User-friendly name for the session."""
        if self.session_start:
            return self.session_start.strftime("%b %d, %Y  %I:%M %p")
        return self.filename

    def get_time_series(self) -> pd.Series:
        """Return a time series — real timestamps if available, else elapsed seconds."""
        if self.session_start:
            return pd.Series([
                self.session_start + timedelta(seconds=float(s))
                for s in self.df["elapsed_sec"]
            ])
        return self.df["elapsed_sec"]


@dataclass
class SessionStats:
    """Computed statistics for a single session."""
    duration_seconds: float = 0.0
    total_samples: int = 0
    violation_count: int = 0
    good_posture_pct: float = 100.0

    # Violations by direction
    violations_up: int = 0
    violations_down: int = 0
    violations_left: int = 0
    violations_right: int = 0
    worst_direction: str = "None"

    # Peak angles
    max_pitch: float = 0.0
    min_pitch: float = 0.0
    max_yaw: float = 0.0
    min_yaw: float = 0.0

    # Averages
    avg_pitch: float = 0.0
    avg_yaw: float = 0.0


@dataclass
class AggregateStats:
    """Aggregated statistics across multiple sessions."""
    total_sessions: int = 0
    total_wear_seconds: float = 0.0
    total_violations: int = 0
    overall_good_pct: float = 100.0
    total_samples: int = 0

    violations_up: int = 0
    violations_down: int = 0
    violations_left: int = 0
    violations_right: int = 0
    worst_direction: str = "None"

    # Per-session scores for trend chart
    session_scores: List[Tuple[Optional[datetime], float]] = field(default_factory=list)
    session_durations: List[Tuple[Optional[datetime], float]] = field(default_factory=list)


# Thresholds (must match the Arduino firmware values)
THRESHOLD_UP   = 30.0   # Extension
THRESHOLD_DOWN = 30.0   # Flexion
THRESHOLD_LEFT = 13.0   # Radial
THRESHOLD_RIGHT = 13.0  # Ulnar


# ---------------------------------------------------------------------------
# CSV Parsing
# ---------------------------------------------------------------------------

def load_csv(file_path: str) -> SessionData:
    """
    Load a posture device CSV file and return a SessionData object.
    Handles the custom # comment headers for session metadata, and detects Wrist vs Back.
    """
    session_start = None
    device_name = "Wrist Posture Monitor"

    # Parse metadata from comment headers
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line.startswith("# Session started:"):
                time_str = line.split(":", 1)[1].strip()
                try:
                    session_start = datetime.strptime(time_str.strip(), "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    session_start = None
            elif line.startswith("# Device:"):
                device_name = line.split(":", 1)[1].strip()
            elif not line.startswith("#"):
                break

    # Load the CSV data (skip comment lines)
    df = pd.read_csv(file_path, comment="#")

    # Detect if Back Posture Corrector log
    if "ms" in df.columns and "mid" in df.columns:
        device_name = "Back Posture Corrector"
        df["elapsed_sec"] = pd.to_numeric(df["ms"], errors="coerce").fillna(0) / 1000.0
        df["pitch_diff"] = pd.to_numeric(df["mid"], errors="coerce").fillna(0)
        # In Back Corrector, Left and Right are roll deviations. 
        # Tilt difference = Left Roll - Right Roll
        df["yaw_diff"] = pd.to_numeric(df["left"], errors="coerce").fillna(0) - pd.to_numeric(df["right"], errors="coerce").fillna(0)
        # Preserve active motor status columns
        df["ctr"] = pd.to_numeric(df["ctr"], errors="coerce").fillna(0).astype(int)
        df["lft"] = pd.to_numeric(df["lft"], errors="coerce").fillna(0).astype(int)
        df["rgt"] = pd.to_numeric(df["rgt"], errors="coerce").fillna(0).astype(int)
        # v4.1+: head (neck-relative pitch deviation) and nck (neck motor active)
        if "head" in df.columns:
            df["head"] = pd.to_numeric(df["head"], errors="coerce").fillna(0)
        if "nck" in df.columns:
            df["nck"] = pd.to_numeric(df["nck"], errors="coerce").fillna(0).astype(int)
        nck_val = df["nck"] if "nck" in df.columns else 0
        df["vibra_active"] = (df["ctr"] | df["lft"] | df["rgt"] | nck_val).astype(int)
    else:
        # Wrist Posture columns validation
        required = ["elapsed_sec", "pitch_diff", "yaw_diff", "vibra_active"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"CSV is missing columns: {', '.join(missing)}")

        # Clean data types
        df["elapsed_sec"] = pd.to_numeric(df["elapsed_sec"], errors="coerce").fillna(0)
        df["pitch_diff"] = pd.to_numeric(df["pitch_diff"], errors="coerce").fillna(0)
        df["yaw_diff"] = pd.to_numeric(df["yaw_diff"], errors="coerce").fillna(0)
        df["vibra_active"] = pd.to_numeric(df["vibra_active"], errors="coerce").fillna(0).astype(int)

    return SessionData(
        file_path=file_path,
        session_start=session_start,
        device_name=device_name,
        df=df,
    )


def load_multiple_csvs(file_paths: List[str]) -> List[SessionData]:
    """Load multiple CSV files, skipping any that fail to parse."""
    sessions = []
    for path in file_paths:
        try:
            sessions.append(load_csv(path))
        except Exception as e:
            print(f"Warning: Failed to load {path}: {e}")
    # Sort by session start time (None goes last)
    sessions.sort(key=lambda s: s.session_start or datetime.max)
    return sessions


# ---------------------------------------------------------------------------
# SD Card Auto-Detection (Windows)
# ---------------------------------------------------------------------------

def scan_for_csv_files() -> List[str]:
    """
    Scan removable drives for wrist device CSV files.
    Returns a list of absolute file paths.
    """
    found = []
    if platform.system() != "Windows":
        return found

    try:
        # Windows drive type constants
        DRIVE_REMOVABLE = 2
        # Also check DRIVE_FIXED (3) since some SD card readers show as fixed
        for letter in "DEFGHIJKLMNOPQRSTUVWXYZ":
            drive = f"{letter}:\\"
            try:
                drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive)
                if drive_type in (DRIVE_REMOVABLE, 3):  # Removable or Fixed
                    found.extend(_scan_directory(drive))
            except Exception:
                continue
    except Exception:
        pass

    return found


def _scan_directory(directory: str, depth: int = 0, max_depth: int = 1) -> List[str]:
    """Scan a directory (up to max_depth) for matching CSV files."""
    found = []
    pattern = re.compile(r"^(W_\d{4}_\d{4}|LOG_\d{4}|POST_\d{4})\.CSV$", re.IGNORECASE)

    try:
        for entry in os.scandir(directory):
            if entry.is_file() and pattern.match(entry.name):
                found.append(entry.path)
            elif entry.is_dir() and depth < max_depth and not entry.name.startswith("."):
                found.extend(_scan_directory(entry.path, depth + 1, max_depth))
    except PermissionError:
        pass

    return found


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def calculate_stats(session: SessionData) -> SessionStats:
    """Calculate posture statistics for a single session."""
    df = session.df
    if df.empty:
        return SessionStats()

    total = len(df)
    violations = int(df["vibra_active"].sum())
    good_pct = ((total - violations) / total) * 100 if total > 0 else 100.0

    is_back = (session.device_name == "Back Posture Corrector")

    # Custom thresholds for back posture vs wrist posture
    t_up    = 18.0 if is_back else THRESHOLD_UP
    t_down  = 18.0 if is_back else THRESHOLD_DOWN
    t_left  = 18.0 if is_back else THRESHOLD_LEFT
    t_right = 18.0 if is_back else THRESHOLD_RIGHT

    # Count violations by direction
    if is_back:
        # Back device: slouch = middle pitch deviation > threshold
        v_up = 0
        v_left  = int(df["lft"].sum()) if "lft" in df.columns else 0
        v_right = int(df["rgt"].sum()) if "rgt" in df.columns else 0
        v_down  = int(((df["pitch_diff"].abs() > t_down) & (df["vibra_active"] == 1)).sum())
        v_neck  = int(df["nck"].sum()) if "nck" in df.columns else 0
    else:
        v_up    = int(((df["pitch_diff"] > t_up)    & (df["vibra_active"] == 1)).sum())
        v_down  = int(((df["pitch_diff"] < -t_down)  & (df["vibra_active"] == 1)).sum())
        v_right = int(((df["yaw_diff"]   > t_right)  & (df["vibra_active"] == 1)).sum())
        v_left  = int(((df["yaw_diff"]   < -t_left)  & (df["vibra_active"] == 1)).sum())
        v_neck  = 0

    # Determine worst direction
    if is_back:
        dir_counts = {"Slouch": v_down, "Tilt Left": v_left, "Tilt Right": v_right}
        if v_neck > 0:
            dir_counts["Neck"] = v_neck
    else:
        dir_counts = {"Up": v_up, "Down": v_down, "Left": v_left, "Right": v_right}
    worst = max(dir_counts, key=dir_counts.get) if any(dir_counts.values()) else "None"

    return SessionStats(
        duration_seconds=session.elapsed_seconds,
        total_samples=total,
        violation_count=violations,
        good_posture_pct=round(good_pct, 1),
        violations_up=v_up,
        violations_down=v_down,
        violations_left=v_left,
        violations_right=v_right,
        worst_direction=worst,
        max_pitch=round(float(df["pitch_diff"].max()), 1),
        min_pitch=round(float(df["pitch_diff"].min()), 1),
        max_yaw=round(float(df["yaw_diff"].max()), 1),
        min_yaw=round(float(df["yaw_diff"].min()), 1),
        avg_pitch=round(float(df["pitch_diff"].mean()), 1),
        avg_yaw=round(float(df["yaw_diff"].mean()), 1),
    )


def aggregate_stats(sessions: List[SessionData]) -> AggregateStats:
    """Aggregate statistics across multiple sessions for the Overall History page."""
    if not sessions:
        return AggregateStats()

    agg = AggregateStats(total_sessions=len(sessions))
    all_stats = []

    for session in sessions:
        stats = calculate_stats(session)
        all_stats.append(stats)

        agg.total_wear_seconds += stats.duration_seconds
        agg.total_samples += stats.total_samples
        agg.total_violations += stats.violation_count
        agg.violations_up += stats.violations_up
        agg.violations_down += stats.violations_down
        agg.violations_left += stats.violations_left
        agg.violations_right += stats.violations_right

        agg.session_scores.append((session.session_start, stats.good_posture_pct))
        agg.session_durations.append((session.session_start, stats.duration_seconds))

    # Overall good posture percentage
    if agg.total_samples > 0:
        agg.overall_good_pct = round(
            ((agg.total_samples - agg.total_violations) / agg.total_samples) * 100, 1
        )

    # Worst direction overall
    dir_counts = {
        "Up": agg.violations_up,
        "Down": agg.violations_down,
        "Left": agg.violations_left,
        "Right": agg.violations_right,
    }
    agg.worst_direction = max(dir_counts, key=dir_counts.get) if any(dir_counts.values()) else "None"

    return agg
