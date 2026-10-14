"""Regenerate the schematic figures used in the READMEs.

Usage:  python tools/make_diagrams.py

Writes 300 dpi PNGs into wrist-glove/images/ and posture-corrector/images/.
Needs matplotlib. Every number drawn here is read from the firmware in this repo
(wrist-glove/firmware/newVariant, posture-corrector/firmware/PostureCorrector).
The schematics are not to scale and show only what the firmware states.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch, Polygon, Rectangle

ROOT = Path(__file__).resolve().parent.parent

BLUE, ORANGE, GREEN = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#dcdcd8"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "figure.facecolor": "white",
    "savefig.facecolor": "white",
    "axes.edgecolor": GRID,
})


def save(fig, rel):
    out = ROOT / rel
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("wrote", rel)


def imu(ax, x, y, size=0.6):
    ax.add_patch(Rectangle((x - size / 2, y - size / 2), size, size, fc=BLUE, ec=INK, lw=0.8, zorder=5))


def mono_block(ax, x, y, lines, size=8.5, step=0.62, bold_first=False):
    for i, line in enumerate(lines):
        ax.text(x, y - i * step, line, fontsize=size, family="monospace", color=INK,
                fontweight="bold" if (bold_first and i == 0) else "normal", va="top")


# --------------------------------------------------------------------------
def posture_channels():
    fig, ax = plt.subplots(figsize=(9.6, 5.4))
    ax.set_xlim(0, 19.2)
    ax.set_ylim(0, 10.8)
    ax.set_aspect("equal")
    ax.axis("off")

    cx = 5.0
    ax.add_patch(Circle((cx, 9.1), 0.95, fc="white", ec=INK2, lw=1.2))
    ax.add_patch(Rectangle((cx - 0.35, 7.7), 0.7, 0.5, fc="white", ec=INK2, lw=1.2))
    ax.add_patch(Polygon([(cx - 2.3, 7.6), (cx + 2.3, 7.6), (cx + 2.7, 3.4), (cx - 2.7, 3.4)],
                         closed=True, fc="white", ec=INK2, lw=1.2))

    imu(ax, cx, 9.1)
    imu(ax, cx - 1.6, 7.0)
    imu(ax, cx + 1.6, 7.0)
    imu(ax, cx, 5.4)
    ax.text(cx - 1.25, 9.1, "HEAD\nmux ch 4", ha="right", va="center", fontsize=8.5, color=INK)
    ax.text(cx - 2.6, 7.0, "LEFT\nmux ch 0", ha="right", va="center", fontsize=8.5, color=INK)
    ax.text(cx + 2.6, 7.0, "RIGHT\nmux ch 1", ha="left", va="center", fontsize=8.5, color=INK)
    ax.text(cx + 0.55, 5.4, "MID\nmux ch 2", ha="left", va="center", fontsize=8.5, color=INK)
    ax.text(cx, 2.85, "schematic, not to scale", ha="center", fontsize=8, color=INK2, style="italic")

    ax.text(10.6, 10.2, "What the firmware reads and drives", fontsize=10, fontweight="bold", color=INK, va="top")
    mono_block(ax, 10.6, 9.3, [
        "mux ch  name   angle used",
        "  0     LEFT   roll",
        "  1     RIGHT  roll",
        "  2     MID    pitch",
        "  4     HEAD   pitch",
        "  3     unused",
    ])
    mono_block(ax, 10.6, 5.4, [
        "back alert: |MID| > 18 deg, or",
        "            |LEFT| or |RIGHT| > 18 deg",
        "neck alert: |HEAD - MID| > 18 deg",
        "(all angles = change from the",
        " 5 s calibration)",
    ])
    mono_block(ax, 10.6, 2.0, [
        "motors (GPIO): NECK 25, LEFT 33,",
        "               MID 32, RIGHT 26",
        "I2C: SDA 21, SCL 22 -> TCA9548A 0x70",
    ])
    fig.text(0.01, -0.02,
             "Channel names are the firmware's (CH_LEFT, CH_RIGHT, CH_MID, CH_HEAD). The firmware does not say where on the body each sensor\n"
             "sits, so the positions drawn follow the names; the left/right viewing side is not specified.",
             fontsize=7.5, color=INK2, va="top")
    save(fig, "posture-corrector/images/sensor_channels.png")


# --------------------------------------------------------------------------
def posture_timeline():
    fig, ax = plt.subplots(figsize=(9.6, 3.6))
    ax.set_xlim(0, 12.2)
    ax.set_ylim(0, 5.2)
    ax.axis("off")

    segs = [
        (0.0, 0.4, ORANGE, None),
        (0.4, 3.4, GRID, "wait 3 s\n(sit still)"),
        (3.4, 8.4, BLUE, "calibrate 5 s\none sample per 300 ms read pass"),
        (8.4, 9.4, ORANGE, None),
        (9.4, 12.0, GREEN, "monitoring"),
    ]
    y0, h = 2.2, 0.9
    for a, b, c, label in segs:
        ax.add_patch(Rectangle((a, y0), b - a, h, fc=c, ec=INK, lw=0.6, alpha=0.9 if c != GRID else 1.0))
        if label:
            ax.text((a + b) / 2, y0 + h / 2, label, ha="center", va="center", fontsize=7.8,
                    color="white" if c in (BLUE, GREEN) else INK)
    ax.annotate("2 x 150 ms buzz\n(MID motor)", xy=(0.2, y0 + h), xytext=(0.2, 4.2), ha="left",
                fontsize=7.8, color=INK, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
    ax.annotate("baseline saved to RTC memory, then\n2 x 400 ms buzz on all motors", xy=(8.9, y0 + h), xytext=(6.4, 4.2),
                ha="left", fontsize=7.8, color=INK, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))

    for t in (0, 3.4, 8.4, 9.4):
        ax.plot([t, t], [y0 - 0.12, y0], color=INK2, lw=0.8)
        ax.text(t, y0 - 0.2, f"{t:g} s", ha="center", va="top", fontsize=7.5, color=INK2)

    ax.text(0.0, 1.2,
            "Monitoring: the 4 IMUs are read every 300 ms (5-sample median each). The 400 ms hold is tested once per read pass,\n"
            "so a motor starts on the third consecutive bad read, about 600 ms. One CSV row every 2000 ms.",
            fontsize=7.8, color=INK, va="top")
    ax.text(0.0, 0.35,
            "Time zero is the first buzz in setup(); IMU and SD initialisation before it are not drawn. Power-on and EN-pin resets always recalibrate.\n"
            "After a watchdog or software reset the saved baseline is reloaded instead (a single 200 ms MID buzz) and the sequence above is skipped.",
            fontsize=7.2, color=INK2, va="top")
    save(fig, "posture-corrector/images/boot_and_calibration.png")


# --------------------------------------------------------------------------
def wrist_pair():
    fig, ax = plt.subplots(figsize=(10.0, 4.4))
    ax.set_xlim(0, 20)
    ax.set_ylim(0, 8.8)
    ax.set_aspect("equal")
    ax.axis("off")

    for x0 in (1.0, 9.4):
        ax.add_patch(FancyBboxPatch((x0, 5.6), 6.6, 2.2, boxstyle="round,pad=0.02,rounding_size=0.5",
                                    fc="white", ec=INK2, lw=1.2))
    ax.plot([8.5, 8.5], [5.2, 8.2], color=INK2, lw=0.9, ls=(0, (4, 3)))
    ax.text(8.5, 8.4, "wrist joint", ha="center", fontsize=7.8, color=INK2)
    imu(ax, 4.3, 6.7)
    imu(ax, 12.7, 6.7)
    ax.text(4.3, 5.0, "sensor 1 (?)", ha="center", va="top", fontsize=8.5, color=INK)
    ax.text(12.7, 5.0, "sensor 2 (?)", ha="center", va="top", fontsize=8.5, color=INK)
    ax.text(16.4, 6.7, "one IMU on each side\nof the joint; which side\nis which is not stated",
            fontsize=7.6, color=INK2, va="center", style="italic")

    mono_block(ax, 1.0, 3.9, [
        "pitch_diff = pitch(sensor 2) - pitch(sensor 1)   flexion / extension",
        "yaw_diff   = roll(sensor 2)  - roll(sensor 1)    radial / ulnar deviation",
        "  pitch = atan2(ax, sqrt(ay^2 + az^2))   roll = atan2(ay, sqrt(ax^2 + az^2))",
    ], size=8.2, step=0.62)
    mono_block(ax, 1.0, 1.7, [
        "sensor 1: LSM6DS3TR-C @ 0x6A  (LIS3MDL @ 0x1C initialised; angles ignore it)",
        "sensor 2: LSM6DS3TR-C @ 0x6B  (LIS3MDL @ 0x1E initialised; angles ignore it)",
    ], size=8.2, step=0.62)
    fig.text(0.01, 0.0,
             "(?) The firmware does not say which sensor is on the forearm and which on the hand; the tilt difference is what it computes.\n"
             "The column called yaw_diff in the firmware and the logs is computed from roll (accelerometer only), not from a true yaw.",
             fontsize=7.4, color=INK2, va="top")
    save(fig, "wrist-glove/images/sensor_pair.png")


# --------------------------------------------------------------------------
def wrist_thresholds():
    fig, ax = plt.subplots(figsize=(9.6, 3.3))
    ax.set_xlim(-48, 48)
    ax.set_ylim(0.2, 3.2)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.set_yticks([])
    ax.set_xticks([-45, -30, -13, 0, 13, 30, 45])
    ax.tick_params(axis="x", labelsize=8, colors=INK2, length=3)
    ax.grid(axis="x", color=GRID, lw=0.5)
    ax.set_axisbelow(True)
    ax.set_xlabel("smoothed angle difference, degrees (firmware sign convention)", fontsize=8.5, color=INK2)

    rows = [
        # y, name, trigger, release, left label, right label
        (2.0, "pitch_diff", 30.0, 28.0, "flexion\nVibra3, GPIO 27", "extension\nVibra4, GPIO 13"),
        (0.5, "yaw_diff", 13.0, 11.0, "radial / left\nVibra2, GPIO 26", "ulnar / right\nVibra1, GPIO 25"),
    ]
    h = 0.62
    for y, name, trig, rel, lab_l, lab_r in rows:
        ax.add_patch(Rectangle((-rel, y), 2 * rel, h, fc=GREEN, alpha=0.35, ec="none"))
        for a, b in ((-trig, -rel), (rel, trig)):
            ax.add_patch(Rectangle((a, y), b - a, h, fc=ORANGE, alpha=0.4, ec="none"))
        for a, b in ((-48, -trig), (trig, 48)):
            ax.add_patch(Rectangle((a, y), b - a, h, fc=ORANGE, alpha=0.85, ec="none"))
        ax.text(0, y + h / 2, f"{name}\nmotors off inside +/-{rel:g}", ha="center", va="center",
                fontsize=7.6, color=INK, linespacing=1.15)
        ax.text(-(trig + 48) / 2, y + h + 0.1, lab_l, ha="center", va="bottom", fontsize=7.4, color=INK)
        ax.text((trig + 48) / 2, y + h + 0.1, lab_r, ha="center", va="bottom", fontsize=7.4, color=INK)
    ax.set_title("Wrist thresholds as coded in newVariant.ino", fontsize=9.5, fontweight="bold", color=INK, pad=8)
    fig.text(0.01, -0.02,
             "Solid orange = motor on past the trigger; light orange = 2 degree hysteresis band (previous state is held); green = motor cleared.\n"
             "THRESHOLD_FLEXION/EXTENSION = 30, THRESHOLD_LEFT/RIGHT = 13, HYSTERESIS = 2; the trigger tests are strict (< and >) and there is no hold timer.\n"
             "Positive yaw_diff is zeroed while pitch_diff > 15 (the 'anatomical correction'). Not checked against a protractor or any clinical reference;\n"
             "which physical direction is positive depends on the sensor mounting, which is unconfirmed.",
             fontsize=7.2, color=INK2, va="top")
    save(fig, "wrist-glove/images/thresholds.png")


if __name__ == "__main__":
    posture_channels()
    posture_timeline()
    wrist_pair()
    wrist_thresholds()
