"""Print descriptive statistics for the wrist development logs in data/wrist/.

Usage:  python tools/summarize_logs.py            (prints a Markdown table)
        python tools/summarize_logs.py --figure   (also writes docs/figures/log_overview.png)

Only the standard library is needed for the table; --figure needs matplotlib.
Nothing here measures accuracy: there is no reference measurement to compare with.
"""
import csv
import hashlib
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GROUPS = [("sessions", ROOT / "data" / "wrist" / "sessions"),
          ("bench", ROOT / "data" / "wrist" / "bench")]


def load(path):
    rows = []
    with open(path, newline="") as f:
        reader = csv.reader(line for line in f if not line.startswith("#"))
        header = next(reader)
        assert header == ["elapsed_sec", "pitch_diff", "yaw_diff", "vibra_active"], header
        for r in reader:
            rows.append((int(r[0]), float(r[1]), float(r[2]), int(r[3])))
    return rows


def summarize(path):
    rows = load(path)
    t = [r[0] for r in rows]
    pitch = [r[1] for r in rows]
    yaw = [r[2] for r in rows]
    vib = [r[3] for r in rows]
    events = sum(1 for a, b in zip(vib, vib[1:]) if a == 0 and b == 1) + (1 if vib[0] else 0)
    gaps = [b - a for a, b in zip(t, t[1:]) if b - a >= 2]
    return {
        "file": path.name,
        "rows": len(rows),
        "minutes": (t[-1] - t[0]) / 60.0,
        "vib_pct": 100.0 * sum(vib) / len(vib),
        "events": events,
        "pitch_med": statistics.median(pitch),
        "yaw_med": statistics.median(yaw),
        "pitch_absmax": max(abs(p) for p in pitch),
        "yaw_absmax": max(abs(y) for y in yaw),
        "gaps": len(gaps),
        "sha": hashlib.sha256(path.read_bytes()).hexdigest(),
        "series": (t, pitch, yaw, vib),
    }


def main():
    all_stats = []
    print("| group | file | rows | minutes | % rows vibrating | vibration onsets | pitch median | yaw median | max abs pitch | max abs yaw |")
    print("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for group, folder in GROUPS:
        for p in sorted(folder.glob("*.CSV")):
            s = summarize(p)
            all_stats.append((group, s))
            print(f"| {group} | {s['file']} | {s['rows']} | {s['minutes']:.1f} | {s['vib_pct']:.1f} | "
                  f"{s['events']} | {s['pitch_med']:.1f} | {s['yaw_med']:.1f} | "
                  f"{s['pitch_absmax']:.1f} | {s['yaw_absmax']:.1f} |")
    print()
    print("SHA-256 of the files as stored in this repo (line endings normalised, see data/README.md):")
    for group, s in all_stats:
        print(f"  {s['sha']}  {s['file']}")
    if "--figure" in sys.argv:
        figure(all_stats)


def figure(all_stats):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    sessions = [s for g, s in all_stats if g == "sessions"]
    fig, axes = plt.subplots(len(sessions), 1, figsize=(9, 1.9 * len(sessions)), sharex=False)
    for ax, s in zip(axes, sessions):
        t, pitch, yaw, vib = s["series"]
        t0 = t[0]
        x = [(v - t0) / 60.0 for v in t]
        ax.plot(x, pitch, lw=0.6, color="#2a78d6", label="pitch_diff")
        ax.plot(x, yaw, lw=0.6, color="#eb6834", label="yaw_diff")
        ax.fill_between(x, -90, 90, where=[bool(v) for v in vib], color="#52514e", alpha=0.18, lw=0,
                        label="motor on")
        ax.grid(color="#dcdcd8", lw=0.4)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.set_ylabel("deg", fontsize=8)
        ax.set_title(s["file"], fontsize=8, loc="left")
        ax.tick_params(labelsize=7)
    axes[-1].set_xlabel("minutes since first row (uptime clock, not wall clock)", fontsize=8)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, fontsize=7, loc="upper right", ncol=3, frameon=False,
               bbox_to_anchor=(0.98, 0.985))
    fig.suptitle("Wrist development recordings: angle differences, grey = motor on\n"
                 "descriptive only; no reference measurement exists to judge accuracy", fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    out = ROOT / "docs" / "figures" / "log_overview.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=300)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
