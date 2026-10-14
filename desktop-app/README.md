# Desktop app (PostureOS)

A Windows-oriented Python desktop app for looking at the CSV logs from the two devices. It was written for the wrist glove first and later extended to recognise the posture corrector's log format. It is a viewer: it does not change any threshold on a device.

Not tested again for this repo: the app was copied in as it was, and no screenshot of it is included here.

## What it does, read from the code

- **Load logs.** Open CSV files, or scan the working folders for them (`data_loader.py`). A file with `ms` and `mid` columns is treated as a posture-corrector log; one with `elapsed_sec,pitch_diff,yaw_diff,vibra_active` is treated as a wrist log. Any `# Session started:` line is read as `YYYY-MM-DD HH:MM:SS`, which is the format the current wrist firmware writes.
- **Download from the device.** `serial_comm.py` talks to the wrist glove over USB serial at 115200 baud: `CMD:HANDSHAKE` (expects `WRIST_DEVICE_V1`), `CMD:LIST`, `CMD:DOWNLOAD:<file>` (see [`../wrist-glove/METHODS.md`](../wrist-glove/METHODS.md), section 10). Downloaded files go to a `downloaded_logs/` folder next to the app. The posture corrector speaks a different set of serial commands, so it cannot be downloaded from here.
- **Pages** (`pages/`): dashboard, overall history, timeline, hand replay (a 3D hand drawn with matplotlib from the pitch and yaw columns), a "JARVIS scan" view, and a raw-data table. There is also a settings page for colour themes. The theme is saved to `posture_os_theme.json`, which is in `.gitignore`.

## How the numbers on its pages are made

These are simple counts over the log rows, so read them as descriptions of the file and not as an assessment of anyone's posture:

- **"Good posture %"** is the share of rows where `vibra_active` is 0, i.e. where no motor was on. It depends on the device's thresholds and has no clinical meaning.
- **Direction counts** (up, down, left, right) count rows where `vibra_active` is 1 and the angle is beyond the threshold in that direction. The wrist thresholds are copied into `data_loader.py` as 30 degrees (up and down) and 13 degrees (left and right), and have to be changed by hand if the firmware changes.
- **For posture-corrector logs** the app uses 18 degrees. It maps the file onto the wrist-style columns: `pitch_diff` is the `mid` column, `yaw_diff` is `left - right`, and `vibra_active` is any of `ctr`, `lft`, `rgt`, `nck`. A "Slouch" count is then rows with `|mid| > 18` while a motor is on. The `left - right` difference is the app's own choice and is not a quantity the firmware computes.

## Running it

```bash
pip install -r requirements.txt
python visualizer.py
```

Run it from inside `desktop-app/` so the `theme`, `data_loader`, `serial_comm` and `pages` imports resolve. The matplotlib pages use the `TkAgg` backend, so Tk must be available.

To build a standalone Windows executable (not done for this repo):

```bash
build_exe.bat
```

It runs PyInstaller in one-file mode and writes `dist/WristPostureVisualizer.exe`. One thing to know: the batch file only installs `pyinstaller pandas matplotlib customtkinter` when PyInstaller is missing, not `pyserial`, and the app exits with an error dialog if `pyserial` is not installed. Install everything from `requirements.txt` first. A frozen build also redirects output to `posture_os_debug.log` next to the executable.

## sample_data/

`W_0710_1430.CSV` and `W_0712_0915.CSV` are sample files that ship with the app so its pages have something to show. They are **not recordings** and are not used in any number in this repo. They look hand-written: their values are round and regular, and their dates do not match any session in `data/`. The real development recordings are in [`../data/`](../data/).
