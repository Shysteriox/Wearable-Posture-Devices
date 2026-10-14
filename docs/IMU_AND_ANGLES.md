# Angles from an accelerometer

Both devices turn accelerometer readings into tilt angles. This page explains what that can and cannot tell you. The code that does it is described in [`../wrist-glove/METHODS.md`](../wrist-glove/METHODS.md) and [`../posture-corrector/METHODS.md`](../posture-corrector/METHODS.md).

## What the sensor reports

A 3-axis accelerometer reports the acceleration of its own frame along three axes. If the board is not accelerating, that is gravity alone: a vector of length 1 g that points straight down, written in the board's own axes. How far that vector leans into each axis tells you how the board is tilted relative to vertical.

- Tilting the board about a horizontal axis changes the three readings, so those two rotations (pitch and roll) can be recovered with `atan2` of the readings.
- Rotating the board about the vertical axis does not change the gravity vector at all. A rotation about the vertical (yaw, or heading) is therefore **invisible** to an accelerometer. A magnetometer can supply it, or a gyroscope can integrate it over time.

## The formulas the two firmwares use

The two devices are separate projects and were written separately, so the formulas and sign conventions are not the same. That is expected, not a mistake.

| | pitch | roll |
|---|---|---|
| Wrist glove | `atan2(ax, sqrt(ay^2 + az^2))` | `atan2(ay, sqrt(ax^2 + az^2))` |
| Posture corrector | `atan2(-ax, sqrt(ay^2 + az^2))` | `atan2(ay, az)` |

- The wrist roll stays within -90 to +90 degrees. The posture roll covers -180 to +180 and wraps at the ends. The posture firmware subtracts the stored baseline directly and has no wrap-around handling, so a roll that crosses +-180 would show as a jump. Whether the actual mounting ever gets there is not known.
- The wrist glove subtracts one sensor's angle from the other's, and labels the difference of the two rolls "yaw". It is a roll difference ([`../wrist-glove/METHODS.md`](../wrist-glove/METHODS.md), section 2). The difference of two angles that each lie within +-90 degrees can reach +-180.
- The posture corrector compares each angle with its own value at calibration, so only changes matter, not the absolute angle.

## Why the angle is wrong when the board moves

The accelerometer cannot tell gravity from motion. It reports the sum. While the hand or torso is accelerating, the vector it sees is gravity plus the motion, so the computed tilt is off by an amount that depends on how hard the motion is. Both firmwares smooth the angle (the wrist glove with a one-pole low-pass, the posture corrector with a median of five), which reduces short bursts but does not remove a sustained acceleration.

A gyroscope does not have this problem over short times, but integrating it drifts. Fusing the two, as the Madgwick filter does [2], is the standard answer. The wrist glove's code still constructs Madgwick filters and starts them at 26 Hz, but never calls them. Neither final firmware uses its gyroscope or magnetometer. A filter's accuracy depends on the specific sensors and test setup, so no number from the Madgwick report is claimed for this hardware.

## The noise floor that was measured

The only measurement of the sensors' own steadiness is one recording with the wrist glove lying still on a bench ([`../data/README.md`](../data/README.md)): both angle differences stayed within 1.3 degrees of zero over 17 minutes. That says the two-sensor difference, the startup calibration and the filter give a steady zero at rest. It does not say the angle is correct while the wrist moves.

## Why the posture corrector needs a multiplexer

All four IMUs answer at the same I2C address (0x68 unless a pin is strapped), so a plain bus cannot tell them apart. A TCA9548A switch [1] routes the bus to one of its eight channels at a time; the firmware selects a channel, reads that IMU, and moves to the next.

## References

The numbers in square brackets are in [`REFERENCES.md`](REFERENCES.md).
