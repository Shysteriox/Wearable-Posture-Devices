# References

Only sources that were opened and checked are listed (2 entries, numbered in the order they are first cited). Each was checked on 2026-10-13.

1. Texas Instruments. *TCA9548A: 8-channel 1.65- to 5.5-V I2C/SMBus switch with reset & voltage translation*; product page. https://www.ti.com/product/TCA9548A (accessed Oct 13, 2026).
2. Madgwick, S. O. H. *An efficient orientation filter for inertial and inertial/magnetic sensor arrays*; technical report, April 30, 2010. https://x-io.co.uk/downloads/madgwick_internal_report.pdf (accessed Oct 13, 2026).

## Notes

- Entry 1 supports one statement: the TCA9548A is an 8-channel I2C switch that runs at 400 kHz, which is why four same-address IMUs can share one bus ([`IMU_AND_ANGLES.md`](IMU_AND_ANGLES.md), [`../posture-corrector/HARDWARE.md`](../posture-corrector/HARDWARE.md)).
- Entry 2 describes the orientation filter that the `MadgwickAHRS` library in the wrist sketches is named after. The wrist prototypes in [`../archive/`](../archive/) used it, and the final wrist firmware still constructs it but never calls it. Its published accuracy figures are for its own test setup and are not claimed for the sensors here.
- **Not checked.** The manufacturer pages for the MPU-6050 (TDK, returned HTTP 403), the LSM6DS3TR-C and the LIS3MDL (STMicroelectronics, timed out) could not be opened. Register values and I2C addresses in this repo are therefore read from the firmware, and no claim relies on those datasheets. They should be added here once they have been opened and read.
- The Arduino libraries the sketches include are named in each device's `HARDWARE.md` and in [`../archive/README.md`](../archive/README.md). Their versions were not recorded and they are not listed as references.
