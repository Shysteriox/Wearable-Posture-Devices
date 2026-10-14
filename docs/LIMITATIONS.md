# Limitations

This page lists what these two devices and this repo cannot be trusted for. It is meant to be read before anything else is built or worn.

## Both devices

- **Not medical devices.** Neither has been reviewed or approved for any medical use, and neither has been tested on patients. Nothing in this repo claims that wearing either one improves a wrist, posture, pain or recovery.
- **No accuracy has been measured.** For neither device is there a reference measurement of the angles (a protractor, goniometer, motion capture or clinician). Statements such as "30 degrees" describe what the code computes from its sensors, not what the body is doing.
- **Thresholds are the author's choices.** 30 and 13 degrees on the wrist, 18 degrees on the posture corrector. They were not derived from a study and not tuned against any user. Comments in the firmware that cite clinical or workplace ranges were not checked against a source, so this repo does not repeat them.
- **Tilt only, from gravity.** Both final firmwares use the accelerometer alone. Any acceleration of the body (walking, reaching, a jolt) corrupts the angle for as long as it lasts, and rotation about the vertical axis cannot be measured at all. See [`IMU_AND_ANGLES.md`](IMU_AND_ANGLES.md).
- **Zero is whatever you held at calibration.** Both devices zero themselves at power-on. If the wrist is not straight, or the wearer is slouching, during those seconds, every later angle is offset by that amount.
- **Hardware is partly undocumented.** There is no schematic, bill of materials, photo, or power design in the repo. The motor driver circuit, supply rail and enclosure of each device are not recorded, and no electrical safety, heating or skin-contact review has been done. Each device's `HARDWARE.md` lists the specifics.
- **Tool and library versions were not recorded.** The Arduino core, libraries and Python packages used are unknown. The sketches have not been compiled again for this repo.
- **No battery life, comfort or durability data.**

## Wrist glove

- **The "yaw" is a roll difference.** It is not a yaw and is only meaningful if the two boards' axes line up.
- **Sensor placement is not recorded.** Which sensor is on the forearm and which on the hand decides the sign of both angles.
- **The anatomical correction is unchecked.** The firmware zeroes positive yaw while pitch is above 15 degrees. In one recording that affects about half the rows ([`../data/README.md`](../data/README.md)).
- **The recordings are development tests.** Their wearer, pose and purpose are unknown. They contain unexplained outliers (yaw values above 110 degrees), one file with a pitch offset of about 18 degrees, and one file where the motors are on far more often than in the others. They say nothing about accuracy or about any person.
- **The filter's time constant is unknown.** The low-pass runs once per loop pass and the loop rate was not measured.
- **Direction labels are unverified.** Which way "left", "up" and so on really point depends on mounting and on which hand wears the glove.
- **Time stamps are approximate.** The clock sets itself from WiFi at boot only, with a fixed UTC-7 offset all year.

## Posture corrector

- **It measures tilt, not shoulder height.** A straight-up shrug barely changes a tilt angle. The shoulder sensors report roll only.
- **Direction is not distinguished.** The rule is an absolute value, so forward and backward lean count the same, as do raising and lowering a shoulder.
- **The motors do not say which side.** One back violation drives all three back motors.
- **Left and right may be swapped.** A pin comment says they were "swapped to match physical harness orientation".
- **Power cycling redoes the calibration.** Only a watchdog or software reset keeps it.
- **No recordings are included**, so nothing about behaviour on a real wearer is reported.

## Desktop app

- **"Good posture %" is a motor-state share**: the fraction of log rows where no motor was on. It depends entirely on the device's thresholds and is not a posture score.
- **The thresholds inside the app are copies** of the firmware constants and have to be updated by hand.
- **For posture-corrector logs the app computes its own sideways angle** (`left - right`), which the firmware does not.
- **It was not re-run for this repo**, and `build_exe.bat` does not install `pyserial`, which the app needs at startup.

## This repo

- **Datasheets were not read.** The manufacturer pages for the MPU-6050, LSM6DS3TR-C and LIS3MDL could not be opened when this was written (see [`REFERENCES.md`](REFERENCES.md)), so no statement here depends on them. Register values and addresses come from the firmware, not from datasheets.
- **The sample CSVs in `desktop-app/sample_data/` are not recordings.**
- **The recordings in `data/` came from an earlier firmware build**, with a slightly different file header from the current one.
