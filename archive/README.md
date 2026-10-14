# Archive: superseded prototypes and bench sketches

Everything here is **superseded** by `wrist-glove/firmware/newVariant/`. It is kept so the history of the wrist glove is visible, not as a starting point. Nothing in this folder was recompiled or re-run for this repo, and no sketch here is used in any number elsewhere.

## wrist-prototypes/

An earlier wrist build that streamed to the Adafruit IO cloud. The differences from the current firmware, read from the code:

| | prototype | current firmware |
|---|---|---|
| Angle source | Madgwick filter on accelerometer, gyroscope and magnetometer, plus a flex sensor | accelerometer tilt only, difference between two sensors |
| Flex sensor | analog read on GPIO 34 through a lookup table (`listb[2000]`) and a fixed bias of -70 | none |
| LED ring | GPIO 12 | GPIO 32 (GPIO 12 is the SPI MISO pin) |
| Logging | cloud feeds (Adafruit IO) in `AllTogetherNow`; none in `...WithoutAdafruitIO` | microSD CSV, plus USB transfer |
| Calibration | none found | 3 s average at start-up |

- `AllTogetherNow/`: the cloud build. It does `#include "config.h"` for the WiFi and Adafruit IO credentials. `config.h` is deliberately **not** in this repo (it is in `.gitignore`); `config.example.h` shows the shape with placeholder values. Fill in your own and do not commit them.
- `AllTogetherNowWithoutAdafruitIO/`: the same sketch with the cloud calls removed.
- `sketch_jun18a/`: an earlier sensor-only sketch using the same libraries.

The motor pins (25, 26, 27, 13) and the 16-LED ring are the same as in the current firmware.

## hardware-tests/

Short bench sketches written while bringing up parts. They are not part of any device build and some of them were written for a different wiring than the current one.

| sketch | what the code does |
|---|---|
| `LED_FlexStrength/` | reads an analog pin and lights a set of output pins (35, 32, 33, 25, 26) according to the value |
| `MagGravAccel/` | reads the LSM6DS3TR-C and LIS3MDL through the Adafruit libraries |
| `SD_Test/` | SD card read/write test using the `FS`/`SD` libraries, with a pull-up on GPIO 19 |
| `WristSDTest/` | the same idea with the `SdFat` library, with a pull-up on GPIO 19 |
| `Vibrationthigny/` | drives six motor pins (25, 26, 27, 14, 12, 13) with tone-like patterns; it includes `pitches.h`, which is not in this repo, so it will not compile as is |
| `sketch_jun18c/` | reads GPIO 34 through the same flex-sensor lookup as the prototype |
| `sketch_jun27a/` | a 13-line `ESP32Servo` sketch |

The file names are the Arduino IDE's default date-based names (`sketch_jun18c` is "June 18, third sketch"). The year is not in the names and was not recorded.

## Edits to the original files

The sketches are otherwise as written. Two changes were made for publishing: credentials were removed (`config.h` is left out and `config.example.h` was added), and one word in a comment in `hardware-tests/SD_Test/SD_Test.ino` was replaced with `[redacted]` because it matched a string from the credentials file.
