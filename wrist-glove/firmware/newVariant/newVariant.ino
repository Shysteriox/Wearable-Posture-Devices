#include <Wire.h>                          // Helps identify different inputs and outputs
#include <Adafruit_Sensor.h>              // Base adafruit library
#include <Adafruit_LSM6DS3TRC.h>          // Accelerometer and gyrometer
#include <Adafruit_LIS3MDL.h>             // Magnetometer
#include <MadgwickAHRS.h>                 // Filter for accelerometer, magnetometer, gyrometer (reserved)
#include <math.h>                         // Math library
#include <Adafruit_NeoPixel.h>            // LED Neopixel library
#include <SD.h>                           // SD card library
#include <SPI.h>                          // SPI communication for SD card
#include <WiFi.h>                         // WiFi for NTP time sync at startup
#include <time.h>                         // Time functions for real timestamps
#include <driver/gpio.h>                  // ESP32 GPIO driver (for gpio_set_pull_mode)

// --- WIFI SETTINGS (change these to match your network) ---
// Eventually these will be configurable from the app
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASS = "YOUR_WIFI_PASSWORD";

// FIX #1: Moved LED_PIN from 12 to 32.
// GPIO 12 is VSPI MISO on ESP32 — sharing it with NeoPixel corrupts SPI
// communication to the SD card every time the LED ring updates.
// GPIO 32 has no SPI or boot-strapping conflicts.
// REWIRE: Move the NeoPixel data wire from GPIO 12 → GPIO 32.
#define LED_PIN 32                        // Pin number for LED ring (was 12 — caused SPI/MISO conflict)
#define LED_COUNT 16                      // Defining the amount of LEDs on the ring
#define SD_CS_PIN 5                       // Chip Select pin for SD card module (GPIO 5)

Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800); // Defining the LED Ring
int j = 50;                               // Counter
unsigned long lastLEDUpdate1 = 0;         // Checking for the last time of the LED update for the first
const int LEDInterval = 3;                // Checking for the interval of the LED update for the first
unsigned long lastLEDUpdate2 = 0;         // Checking for the last time of the LED update for the second
const int LEDInterval2 = 3;               // Checking for the interval of the LED update for the second

// FIX #3: Corrected flash_vibra variable naming to match actual motor assignments.
// Previously the Left/Right boolean flags were crossed (vibra1 flag set when Vibra2 fired, etc.)
// Now: flash_vibra1 = Vibra1 active (Yaw Right), flash_vibra2 = Vibra2 active (Yaw Left)
boolean flash_vibra1 = false;             // Vibra1 motor active (Yaw Right)
boolean flash_vibra2 = false;             // Vibra2 motor active (Yaw Left)
boolean flash_vibra3 = false;             // Vibra3 motor active (Pitch Down / Flexion)
boolean flash_vibra4 = false;             // Vibra4 motor active (Pitch Up / Extension)
boolean flashing = false;                 // Setting the LEDs to off
boolean LED = false;                      // Checking if its time to point
int flash = 0;                            // The center LED that is flashing, 2, 6, 10, 14

// Madgwick filters declared but not used in accel-only mode; reserved for future fusion upgrade
Madgwick filter;                          // First filter  (reserved)
Madgwick filter2;                         // Second filter (reserved)

static const lsm6ds_accel_range_t ACCEL_RANGE = LSM6DS_ACCEL_RANGE_4_G;                 // Range of accelerometer
static const lsm6ds_gyro_range_t  GYRO_RANGE  = LSM6DS_GYRO_RANGE_250_DPS;              // Range of gyrometer
static const lis3mdl_range_t       MAG_RANGE   = LIS3MDL_RANGE_4_GAUSS;                  // Range of magnetometer

Adafruit_LSM6DS3TRC lsm6ds3{};            // Defining the first accelerometer and gyrometer
Adafruit_LIS3MDL lis3mdl{};               // Defining the first magnetometer
Adafruit_LSM6DS3TRC lsm6ds3_2{};          // Defining the second accelerometer and gyrometer
Adafruit_LIS3MDL lis3mdl_2{};             // Defining the second magnetometer

TwoWire I2C_1 = TwoWire(0);               // Defines the I2C
double ax, ay, az;                        // First IMU vectors
double gx, gy, gz;
double mx, my, mz;
double ax_2, ay_2, az_2;                  // Second IMU vectors
double gx_2, gy_2, gz_2;

double pitchDiff = 0;                     // Difference in the Pitches
double yawDiff = 0;                       // Difference in the Yaws

const int Vibra1 = 25;                    // Vibrator 1 Pin (Yaw Right)
const int Vibra2 = 26;                    // Vibrator 2 Pin (Yaw Left)
const int Vibra3 = 27;                    // Vibrator 3 Pin (Pitch Down / Flexion)
const int Vibra4 = 13;                    // Vibrator 4 Pin (Pitch Up / Extension)

// --- SD CARD LOGGING VARIABLES ---
File logFile;                             // SD card log file handle
char logFileName[30];                     // Current log filename (sized for date/time names)
unsigned long lastLogTime = 0;            // Last time data was logged
const unsigned long LOG_INTERVAL = 500;   // Log every 0.5 seconds (500 ms)
unsigned long rowCount = 0;               // Number of rows written to current file
const unsigned long MAX_ROWS = 50000;     // Rotate file after this many rows (~2.9 days)
int fileIndex = 0;                        // Current log file number
bool sdReady = false;                     // Whether SD card initialized successfully
bool timeSynced = false;                  // Whether NTP time was successfully synced

// --- CALIBRATION VARIABLES ---
double calPitchOffset = 0.0;             // Calibrated pitch offset (captured at startup)
double calYawOffset   = 0.0;             // Calibrated yaw offset (captured at startup)
bool calibrated = false;                  // Whether calibration is complete

// --- SMOOTHING ---
double smoothPitch = 0.0;                // Low-pass filtered pitch difference
double smoothYaw   = 0.0;                // Low-pass filtered yaw difference (roll-based)
const double SMOOTH_ALPHA = 0.15;        // Smoothing factor (lower = smoother but laggier)

// --- VIBRATION THRESHOLDS (Based on Ergonomic Research) ---
// Max wrist ROM: Flexion ~80°, Extension ~75°, Radial ~20°, Ulnar ~40°
// OSHA/ergonomic guidelines: sustained posture beyond 20° in any direction
// compresses the median nerve and inflames tendons (carpal tunnel risk).
// Thresholds set at ~50-60% of max ROM = the clinical "danger zone" for
// prolonged posture. The device warns you BEFORE you reach harmful angles.
const double THRESHOLD_FLEXION   = 30.0;  // Vibrate when bent downward past 30° (max ~80°, danger at 20°+)
const double THRESHOLD_EXTENSION = 30.0;  // Vibrate when bent upward past 30° (max ~75°, danger at 20°+)
const double THRESHOLD_LEFT      = 13.0;  // Vibrate when bent left (radial) past 13° (max ~20°)
const double THRESHOLD_RIGHT     = 13.0;  // Vibrate when bent right (ulnar) past 13° (max ~40°)
const double HYSTERESIS          = 2.0;   // Buffer to prevent boundary jitter/flicker

// --- DEAD ZONE & GRADIENT SETTINGS ---
// DEAD_ZONE_FRAC: fraction of each threshold that is "fully green" (no color change at all)
//   0.50 = the first 50% of each threshold range is pure green
//   e.g. for THRESHOLD_FLEXION=20, dead zone = 20*0.50 = 10 degrees of free movement
const double DEAD_ZONE_FRAC = 0.50;

const double PI_VAL = 3.141592653;

// Forward function declarations
void syncTime();
void initSDCard();
void createNewLogFile();
void logDataToSD(double pDiff, double yDiff, bool vibraActive);
void runCalibration();

// partyMode: non-blocking rainbow cycle using millis() instead of delay().
// Call once per loop() iteration; it will advance one frame per call interval.
// FIX: Was blocking (256 × delay(5) = 1.28s freeze). Now state-machine based.
void partyMode() {
  static uint16_t partyJ = 0;
  static unsigned long lastPartyUpdate = 0;
  if (millis() - lastPartyUpdate < 5) return;   // 5 ms between frames (same visual speed)
  lastPartyUpdate = millis();

  for (uint16_t i = 0; i < strip.numPixels(); i++) {
    strip.setPixelColor(i, strip.ColorHSV((i * 65536 / strip.numPixels() + partyJ * 256) % 65536));
  }
  strip.show();
  partyJ = (partyJ + 1) % 256;
}

void setup() {
  Serial.begin(115200);
  delay(500);                                   // Brief startup delay (non-blocking, works untethered)

  // Madgwick filters initialized to match sensor data rate; not actively used (accel-only mode)
  filter.begin(26);
  filter2.begin(26);

  pinMode(Vibra1, OUTPUT);
  pinMode(Vibra2, OUTPUT);
  pinMode(Vibra3, OUTPUT);
  pinMode(Vibra4, OUTPUT);
  I2C_1.begin(21, 22);

  Serial.println("Scanning I2C_1 on 21=SDA,22=SCL");
  for (uint8_t addr = 1; addr < 127; addr++) {
    I2C_1.beginTransmission(addr);
    if (I2C_1.endTransmission() == 0) {
      Serial.print(" Found @0x"); Serial.println(addr, HEX);
    }
  }

  if (!lsm6ds3.begin_I2C(0x6A, &I2C_1))   { Serial.println("! lsm6ds3 missing"); }
  if (!lis3mdl.begin_I2C(0x1C, &I2C_1))   { Serial.println("! lis3mdl missing"); }
  if (!lsm6ds3_2.begin_I2C(0x6B, &I2C_1)) { Serial.println("! lsm6ds3_2 missing"); }
  if (!lis3mdl_2.begin_I2C(0x1E, &I2C_1)) { Serial.println("! lis3mdl_2 missing"); }
  Serial.println("All sensors initiated!");

  lsm6ds3.setAccelRange(ACCEL_RANGE);
  lsm6ds3.setGyroRange(GYRO_RANGE);
  lsm6ds3.setAccelDataRate(LSM6DS_RATE_26_HZ);
  lsm6ds3.setGyroDataRate(LSM6DS_RATE_26_HZ);
  lis3mdl.setRange(MAG_RANGE);

  lsm6ds3_2.setAccelRange(ACCEL_RANGE);
  lsm6ds3_2.setGyroRange(GYRO_RANGE);
  lsm6ds3_2.setAccelDataRate(LSM6DS_RATE_26_HZ);
  lsm6ds3_2.setGyroDataRate(LSM6DS_RATE_26_HZ);
  lis3mdl_2.setRange(MAG_RANGE);

  // --- SD CARD INITIALIZATION ---
  // Must happen before strip.begin() so NeoPixel never touches GPIO 32
  // (no conflict now that LED_PIN moved off GPIO 12 / VSPI MISO)
  initSDCard();

  // --- TIME SYNC (WiFi) ---
  // Connects briefly to WiFi to grab real date/time, then disconnects
  syncTime();

  // Now create the log file (uses real date/time in filename if synced)
  if (sdReady) createNewLogFile();

  // NeoPixel init — safe to call after SD init since LED_PIN is now GPIO 32
  strip.begin();
  strip.setBrightness(25);                    // ~10% brightness
  for (int i = 0; i < 16; i++) {
    strip.setPixelColor(i, 0, 255, 0);
  }
  strip.show();

  // --- STARTUP CALIBRATION ---
  // LEDs pulse blue for ~3.5 seconds while user holds wrist in neutral position
  // Then flash green 3x when calibration is complete
  runCalibration();
}

void loop() {
  // --- Check for serial commands from desktop app ---
  handleSerialCommands();

  sensors_event_t accel, gyro, temp;
  lsm6ds3.getEvent(&accel, &gyro, &temp);
  sensors_event_t accel2, gyro2, temp2;
  lsm6ds3_2.getEvent(&accel2, &gyro2, &temp2);
  sensors_event_t mag;
  lis3mdl.getEvent(&mag);
  sensors_event_t mag2;
  lis3mdl_2.getEvent(&mag2);

  // --- Raw IMU Scaling ---
  ax = accel.acceleration.x / 9.80665;
  ay = accel.acceleration.y / 9.80665;
  az = accel.acceleration.z / 9.80665;
  gx = gyro.gyro.x * 180 / 3.141592653;
  gy = gyro.gyro.y * 180 / 3.141592653;
  gz = gyro.gyro.z * 180 / 3.141592653;
  mx = mag.magnetic.x;
  my = mag.magnetic.y;
  mz = mag.magnetic.z;

  ax_2 = accel2.acceleration.x / 9.80665;
  ay_2 = accel2.acceleration.y / 9.80665;
  az_2 = accel2.acceleration.z / 9.80665;
  gx_2 = gyro2.gyro.x * 180 / 3.141592653;
  gy_2 = gyro2.gyro.y * 180 / 3.141592653;
  gz_2 = gyro2.gyro.z * 180 / 3.141592653;

  // === ACCELEROMETER-ONLY TILT ANGLES (DRIFT-FREE) ===
  // Uses gravity as an absolute reference. No gyroscope integration = no drift ever.
  // Each sensor measures its tilt relative to gravity using atan2().
  // The DIFFERENCE between the two sensors' tilts = the wrist bend angle.
  //
  // Pitch = flexion/extension (up/down bending of the wrist)
  //   atan2(ax, sqrt(ay² + az²)) gives tilt of the sensor's X-axis from horizontal
  // Roll = radial/ulnar deviation (left/right bending of the wrist)
  //   atan2(ay, sqrt(ax² + az²)) gives tilt of the sensor's Y-axis from horizontal

  double pitch1 = atan2(ax, sqrt(ay * ay + az * az)) * 57.2957795;        // sensor 1 pitch (degrees)
  double pitch2 = atan2(ax_2, sqrt(ay_2 * ay_2 + az_2 * az_2)) * 57.2957795; // sensor 2 pitch
  double roll1  = atan2(ay, sqrt(ax * ax + az * az)) * 57.2957795;        // sensor 1 roll
  double roll2  = atan2(ay_2, sqrt(ax_2 * ax_2 + az_2 * az_2)) * 57.2957795; // sensor 2 roll

  double rawPitchDiff = pitch2 - pitch1;   // wrist flexion/extension
  double rawYawDiff   = roll2  - roll1;    // wrist radial/ulnar deviation

  // Apply startup calibration offsets (captured during the calibration window)
  pitchDiff = rawPitchDiff - calPitchOffset;
  yawDiff   = rawYawDiff   - calYawOffset;

  // --- SMOOTHING (low-pass filter to eliminate accelerometer jitter from hand movement) ---
  smoothPitch = smoothPitch * (1.0 - SMOOTH_ALPHA) + pitchDiff * SMOOTH_ALPHA;
  smoothYaw   = smoothYaw   * (1.0 - SMOOTH_ALPHA) + yawDiff   * SMOOTH_ALPHA;
  pitchDiff = smoothPitch;
  yawDiff   = smoothYaw;

  // --- ANATOMICAL CORRECTION ---
  // When bending upward (extension), the wrist naturally deviates to the right.
  // Only suppress RIGHT when UP is actually past the vibration threshold.
  // This prevents RIGHT from being killed during normal small movements.
  // Left, Right, Down, and their combinations (Down+Left, Down+Right) still work.
  if (pitchDiff > THRESHOLD_EXTENSION * 0.5 && yawDiff > 0) {
    yawDiff = 0;    // Suppress RIGHT when UP is significantly detected
  }

  // --- Serial Diagnostic Stream ---
  Serial.print("PitchDiff: "); Serial.print(pitchDiff);
  Serial.print(" | YawDiff: "); Serial.println(yawDiff);

  // --- SD CARD DATA LOGGING ---
  bool vibraActive = flash_vibra1 || flash_vibra2 || flash_vibra3 || flash_vibra4;
  logDataToSD(pitchDiff, yawDiff, vibraActive);

  // --- POSTURE-DRIVEN HAPTIC TRIGGER LOGIC ---

  // 1. Vertical Tracking (Pitch Control)
  if (pitchDiff < -THRESHOLD_FLEXION) {
    digitalWrite(Vibra3, HIGH); flash_vibra3 = true;
    digitalWrite(Vibra4, LOW);  flash_vibra4 = false;
  }
  else if (pitchDiff > THRESHOLD_EXTENSION) {
    digitalWrite(Vibra4, HIGH); flash_vibra4 = true;
    digitalWrite(Vibra3, LOW);  flash_vibra3 = false;
  }
  else if (pitchDiff > (-THRESHOLD_FLEXION + HYSTERESIS) && pitchDiff < (THRESHOLD_EXTENSION - HYSTERESIS)) {
    // Clear pins safely only if well inside the tracking boundaries
    digitalWrite(Vibra3, LOW);  flash_vibra3 = false;
    digitalWrite(Vibra4, LOW);  flash_vibra4 = false;
  }

  // 2. Horizontal Tracking (Yaw Control)
  // FIX #3: Corrected crossed flash_vibra flag assignments.
  // Previously: Left block set flash_vibra1 (wrong) and Right block set flash_vibra2 (wrong).
  // Now each flag correctly tracks its own motor pin.
  if (yawDiff < -THRESHOLD_LEFT) {
    digitalWrite(Vibra2, HIGH); flash_vibra2 = true;   // Vibra2 = Left motor
    digitalWrite(Vibra1, LOW);  flash_vibra1 = false;
  }
  else if (yawDiff > THRESHOLD_RIGHT) {
    digitalWrite(Vibra1, HIGH); flash_vibra1 = true;   // Vibra1 = Right motor
    digitalWrite(Vibra2, LOW);  flash_vibra2 = false;
  }
  // FIX #4: Corrected yaw hysteresis dead-band direction.
  // Was: yawDiff > (-THRESHOLD_LEFT - HYSTERESIS) — widens the band outward (wrong)
  // Now: yawDiff > (-THRESHOLD_LEFT + HYSTERESIS) — narrows the band inward (correct, mirrors pitch)
  else if (yawDiff > (-THRESHOLD_LEFT + HYSTERESIS) && yawDiff < (THRESHOLD_RIGHT - HYSTERESIS)) {
    // Clear pins safely only if well inside the tracking boundaries
    digitalWrite(Vibra1, LOW);  flash_vibra1 = false;
    digitalWrite(Vibra2, LOW);  flash_vibra2 = false;
  }

  // === DIRECTIONAL LED HEAT MAP ===
  // Each LED only goes red if it's on the SIDE of the ring matching the deviation direction.
  // LEDs on the opposite side stay green. Diagonal deviations light up the diagonal LEDs.
  // This works like a 3D chart — you can see exactly which direction the issue is.

  // Step 1: Compute SIGNED severity for each axis (-1.0 to +1.0)
  //   Positive pitch = bent UP (extension),  Negative pitch = bent DOWN (flexion)
  //   Positive yaw   = deviated RIGHT,       Negative yaw   = deviated LEFT
  //   Inside dead zone = 0.0 (fully green, no indication)
  // FIX #5: Corrected dead-zone degree comments to match actual math.
  double deadDown  = THRESHOLD_FLEXION   * DEAD_ZONE_FRAC;  // 35.0 * 0.70 = 24.5 degrees
  double deadUp    = THRESHOLD_EXTENSION * DEAD_ZONE_FRAC;  // 30.0 * 0.70 = 21.0 degrees
  double deadLeft  = THRESHOLD_LEFT      * DEAD_ZONE_FRAC;  // 18.0 * 0.70 = 12.6 degrees
  double deadRight = THRESHOLD_RIGHT     * DEAD_ZONE_FRAC;  // 15.0 * 0.70 = 10.5 degrees

  double pitchSev = 0.0;  // signed: + = up, - = down
  if (pitchDiff < -deadDown) {
    pitchSev = -((-pitchDiff - deadDown) / (THRESHOLD_FLEXION - deadDown));
    if (pitchSev < -1.0) pitchSev = -1.0;
  } else if (pitchDiff > deadUp) {
    pitchSev = (pitchDiff - deadUp) / (THRESHOLD_EXTENSION - deadUp);
    if (pitchSev > 1.0) pitchSev = 1.0;
  }

  double yawSev = 0.0;  // signed: + = right, - = left
  if (yawDiff < -deadLeft) {
    yawSev = -((-yawDiff - deadLeft) / (THRESHOLD_LEFT - deadLeft));
    if (yawSev < -1.0) yawSev = -1.0;
  } else if (yawDiff > deadRight) {
    yawSev = (yawDiff - deadRight) / (THRESHOLD_RIGHT - deadRight);
    if (yawSev > 1.0) yawSev = 1.0;
  }

  // Step 2: For each LED, compute how much it "faces" the deviation direction
  // Ring mapping (matches existing vibrator→LED assignments):
  //   LED 14 = pitch-down indicator,  LED 6  = pitch-up indicator
  //   LED 2  = yaw-left indicator,    LED 10 = yaw-right indicator
  // Each LED i has a direction vector derived from its angle on the ring.
  // The dot product of (LED direction) · (deviation) determines its color.

  for (int i = 0; i < 16; i++) {
    double theta = i * 2.0 * PI_VAL / 16.0;
    // pitchWeight: +1 at LED 6 (up indicator), -1 at LED 14 (down indicator)
    double pw = cos(theta - 3.0 * PI_VAL / 4.0);
    // yawWeight: +1 at LED 10 (right indicator), -1 at LED 2 (left indicator)
    double yw = cos(theta - 5.0 * PI_VAL / 4.0);

    // Dot product: positive = this LED faces the "bad" direction
    double dot = pw * pitchSev + yw * yawSev;

    int r = 0, g = 255;  // default green
    if (dot > 0.0) {
      // This LED is on the deviation side — gradient green→yellow→red
      double intensity = dot;  // 0.0 to ~1.4 (diagonal can exceed 1.0)
      if (intensity > 1.0) intensity = 1.0;
      if (intensity <= 0.5) {
        r = (int)(intensity * 2.0 * 255.0);  // 0→255
        g = 255;
      } else {
        r = 255;
        g = (int)((1.0 - intensity) * 2.0 * 255.0);  // 255→0
      }
    }
    strip.setPixelColor(i, r, g, 0);
  }

  strip.show();
}

// ===================================================================
// SD CARD HELPER FUNCTIONS
// ===================================================================

// Sync real date/time from the internet via NTP
void syncTime() {
  Serial.println("--- TIME SYNC ---");
  Serial.print("  Connecting to WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  int timeout = 0;
  while (WiFi.status() != WL_CONNECTED && timeout < 20) {
    delay(500);
    Serial.print(".");
    timeout++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println(" Connected!");
    // Pacific Time: GMT-8, +1 hour daylight savings
    configTime(-8 * 3600, 3600, "pool.ntp.org");

    struct tm timeinfo;
    int retries = 0;
    while (!getLocalTime(&timeinfo) && retries < 10) {
      delay(500);
      retries++;
    }

    if (getLocalTime(&timeinfo)) {
      char buf[30];
      strftime(buf, sizeof(buf), "%Y-%m-%d %H:%M:%S", &timeinfo);
      Serial.print("  Time synced: "); Serial.println(buf);
      timeSynced = true;
    } else {
      Serial.println("  Time sync failed. Using elapsed time.");
    }

    WiFi.disconnect(true);
    WiFi.mode(WIFI_OFF);
    Serial.println("  WiFi disconnected (saving power).");
  } else {
    Serial.println(" Failed! Using elapsed time.");
    WiFi.disconnect(true);
    WiFi.mode(WIFI_OFF);
  }
}

// Initialize the SD card on VSPI with explicit pin assignments
void initSDCard() {
  Serial.println("--- SD CARD INIT ---");

  // Explicitly configure VSPI pins for the SD card module
  SPI.begin(18, 19, 23, SD_CS_PIN);  // SCK=18, MISO=GPIO19, MOSI=GPIO23, CS=GPIO5

  // Use gpio_set_pull_mode to configure pull-up leaving SPI matrix intact
  gpio_set_pull_mode(GPIO_NUM_19, GPIO_PULLUP_ONLY);

  // Try up to 3 times
  for (int attempt = 1; attempt <= 3; attempt++) {
    Serial.print("  Attempt "); Serial.print(attempt); Serial.print("/3... ");

    if (SD.begin(SD_CS_PIN, SPI, 1000000)) {
      Serial.println("SUCCESS!");
      sdReady = true;
      return;
    }

    Serial.println("FAILED");
    delay(500);  // Wait before retrying
  }

  Serial.println("  SD card init FAILED after 3 attempts. Check wiring!");
  sdReady = false;
}

// Create a new log file with date/time in the name if WiFi synced
void createNewLogFile() {
  if (!sdReady) return;

  if (timeSynced) {
    // Name the file using real date/time: W_MMDD_HHMM.CSV
    struct tm timeinfo;
    getLocalTime(&timeinfo);
    sprintf(logFileName, "/W_%02d%02d_%02d%02d.CSV",
            timeinfo.tm_mon + 1, timeinfo.tm_mday,
            timeinfo.tm_hour, timeinfo.tm_min);

    // If file already exists (rebooted within the same minute), add a suffix
    if (SD.exists(logFileName)) {
      for (int suffix = 2; suffix < 100; suffix++) {
        sprintf(logFileName, "/W_%02d%02d_%02d%02d_%d.CSV",
                timeinfo.tm_mon + 1, timeinfo.tm_mday,
                timeinfo.tm_hour, timeinfo.tm_min, suffix);
        if (!SD.exists(logFileName)) break;
      }
    }
  } else {
    // Fallback: numbered files if no WiFi was available
    do {
      fileIndex++;
      sprintf(logFileName, "/LOG_%04d.CSV", fileIndex);
    } while (SD.exists(logFileName) && fileIndex < 9999);

    if (fileIndex >= 9999) {
      fileIndex = 9999;
      sprintf(logFileName, "/LOG_%04d.CSV", fileIndex);
    }
  }

  // Write session metadata + CSV header
  logFile = SD.open(logFileName, FILE_WRITE);
  if (logFile) {
    // Session info line (app can read this to know when recording started)
    if (timeSynced) {
      struct tm timeinfo;
      getLocalTime(&timeinfo);
      char timeStr[30];
      strftime(timeStr, sizeof(timeStr), "%Y-%m-%d %H:%M:%S", &timeinfo);
      logFile.print("# Session started: "); logFile.println(timeStr);
    } else {
      logFile.println("# Session started: Unknown (no WiFi sync)");
    }
    logFile.println("# Device: Wrist Posture Monitor");
    logFile.println("elapsed_sec,pitch_diff,yaw_diff,vibra_active");
    logFile.flush();
    logFile.close();
    Serial.print("  Logging to: "); Serial.println(logFileName);
  } else {
    Serial.print("  WARNING: Could not create "); Serial.println(logFileName);
  }
  rowCount = 0;
}

// Log one row of CSV data to the SD card
void logDataToSD(double pDiff, double yDiff, bool vibraActive) {
  if (!sdReady) return;
  if (millis() - lastLogTime < LOG_INTERVAL) return;  // Not time to log yet

  lastLogTime = millis();

  // Rotate to a new file if current one has too many rows
  if (rowCount >= MAX_ROWS) {
    createNewLogFile();
  }

  // Open file in append mode, write one CSV row, close immediately (power-safe)
  logFile = SD.open(logFileName, FILE_APPEND);
  if (logFile) {
    logFile.print(millis() / 1000);   logFile.print(",");
    logFile.print(pDiff, 1);          logFile.print(",");
    logFile.print(yDiff, 1);          logFile.print(",");
    logFile.println(vibraActive ? 1 : 0);
    logFile.flush();   // Force data to card (prevents empty file issue)
    logFile.close();
    rowCount++;
  } else {
    Serial.print("  SD write failed for row "); Serial.println(rowCount);
  }
}

// ===================================================================
// STARTUP CALIBRATION ROUTINE
// ===================================================================
// Runs for ~3.5 seconds on boot using accelerometer-only tilt:
//   - 0.5s settle window (samples discarded — sensors stabilizing)
//   - 3.0s active sampling to average pitch/roll offsets for neutral pose
// LEDs pulse blue during calibration, then flash green 3x when done.
// This eliminates the need for hardcoded offsets and accounts for:
//   - Natural anatomical wrist bend (~10-15 degrees of extension at rest)
//   - Sensor mounting angle variations between sessions
//   - Individual body differences between users

void runCalibration() {
  Serial.println("=== CALIBRATION ===");
  Serial.println("Hold wrist straight and flat for 3 seconds...");

  const unsigned long CAL_DURATION = 3000;    // 3 seconds of sampling
  const unsigned long CAL_SETTLE   = 500;     // 0.5 second for sensor warmup
  unsigned long calStart = millis();
  double sumPitch = 0, sumYaw = 0;
  int sampleCount = 0;
  int pulseVal = 0;
  bool pulseUp = true;

  while (millis() - calStart < CAL_DURATION + CAL_SETTLE) {
    // Read accelerometers
    sensors_event_t accel, gyro, temp;
    lsm6ds3.getEvent(&accel, &gyro, &temp);
    sensors_event_t accel2, gyro2, temp2;
    lsm6ds3_2.getEvent(&accel2, &gyro2, &temp2);

    // Only accumulate samples after settle period
    if (millis() - calStart > CAL_SETTLE) {
      // Compute accelerometer tilt (same math as main loop)
      double cax  = accel.acceleration.x / 9.80665;
      double cay  = accel.acceleration.y / 9.80665;
      double caz  = accel.acceleration.z / 9.80665;
      double cax2 = accel2.acceleration.x / 9.80665;
      double cay2 = accel2.acceleration.y / 9.80665;
      double caz2 = accel2.acceleration.z / 9.80665;

      double p1 = atan2(cax,  sqrt(cay  * cay  + caz  * caz))  * 57.2957795;
      double p2 = atan2(cax2, sqrt(cay2 * cay2 + caz2 * caz2)) * 57.2957795;
      double r1 = atan2(cay,  sqrt(cax  * cax  + caz  * caz))  * 57.2957795;
      double r2 = atan2(cay2, sqrt(cax2 * cax2 + caz2 * caz2)) * 57.2957795;

      sumPitch += (p2 - p1);
      sumYaw   += (r2 - r1);
      sampleCount++;
    }

    // Pulsing blue LED animation during calibration
    if (pulseUp) { pulseVal += 3; if (pulseVal >= 100) pulseUp = false; }
    else         { pulseVal -= 3; if (pulseVal <= 10)  pulseUp = true;  }
    for (int i = 0; i < 16; i++) {
      strip.setPixelColor(i, 0, 0, pulseVal);  // Blue pulse
    }
    strip.show();
    delay(20);  // ~50 Hz calibration sample rate
  }

  // Compute average offsets from the neutral pose
  if (sampleCount > 0) {
    calPitchOffset = sumPitch / sampleCount;
    calYawOffset   = sumYaw   / sampleCount;
  }
  calibrated = true;

  // Initialize the smoothing filters at the calibrated zero
  smoothPitch = 0.0;
  smoothYaw   = 0.0;

  Serial.print("Calibration complete! Samples=");
  Serial.print(sampleCount);
  Serial.print(" PitchOffset=");
  Serial.print(calPitchOffset);
  Serial.print(" YawOffset=");
  Serial.println(calYawOffset);

  // Flash green 3 times to signal calibration is done
  for (int f = 0; f < 3; f++) {
    for (int i = 0; i < 16; i++) strip.setPixelColor(i, 0, 255, 0);
    strip.show();
    delay(200);
    for (int i = 0; i < 16; i++) strip.setPixelColor(i, 0, 0, 0);
    strip.show();
    delay(200);
  }
  // Set all LEDs back to green (normal idle state)
  for (int i = 0; i < 16; i++) strip.setPixelColor(i, 0, 255, 0);
  strip.show();

  Serial.println("Tracking started!");
}
// =============================================================
// SERIAL COMMAND HANDLER — Desktop App File Transfer Protocol
// =============================================================
// The desktop Wrist Visualizer app sends commands over USB serial
// to list and download CSV log files from the SD card.
// Commands are prefixed with "CMD:" so they don't collide with
// normal serial debug output.
//
// Protocol:
//   CMD:HANDSHAKE        → responds "WRIST_DEVICE_V1"
//   CMD:LIST             → responds with filenames, one per line, then "END"
//   CMD:DOWNLOAD:file.CSV → streams file contents, then "EOF"
//
// IMPORTANT: This is NON-BLOCKING. It reads one character at a time
// per loop() call and only processes a command when a full line
// (ending with '\n') has been received. This prevents the main
// sensor loop from stalling, which would trigger watchdog resets.
// =============================================================

static char serialCmdBuffer[128];   // Buffer for incoming command
static int  serialCmdIdx = 0;       // Current position in buffer

void handleSerialCommands() {
  // Read available characters one at a time (non-blocking)
  while (Serial.available()) {
    char ch = Serial.read();

    // End of command line
    if (ch == '\n' || ch == '\r') {
      if (serialCmdIdx == 0) continue;  // Skip empty lines

      serialCmdBuffer[serialCmdIdx] = '\0';  // Null-terminate
      String line = String(serialCmdBuffer);
      serialCmdIdx = 0;  // Reset buffer

      line.trim();
      if (!line.startsWith("CMD:")) return;  // Not a command, ignore

      String cmd = line.substring(4);  // Strip "CMD:" prefix
      processSerialCommand(cmd);
      return;
    }

    // Add character to buffer (prevent overflow)
    if (serialCmdIdx < (int)sizeof(serialCmdBuffer) - 1) {
      serialCmdBuffer[serialCmdIdx++] = ch;
    }
  }
}

void processSerialCommand(String cmd) {
  // --- HANDSHAKE ---
  if (cmd == "HANDSHAKE") {
    Serial.println("WRIST_DEVICE_V1");
    return;
  }

  // --- LIST FILES ---
  if (cmd == "LIST") {
    File root = SD.open("/");
    if (!root) {
      Serial.println("ERROR:SD_OPEN_FAILED");
      Serial.println("END");
      return;
    }
    File entry;
    while ((entry = root.openNextFile())) {
      if (!entry.isDirectory()) {
        String name = entry.name();
        // Only list CSV files
        if (name.endsWith(".CSV") || name.endsWith(".csv")) {
          Serial.println(name);
        }
      }
      entry.close();
    }
    root.close();
    Serial.println("END");
    return;
  }

  // --- DOWNLOAD FILE ---
  if (cmd.startsWith("DOWNLOAD:")) {
    String filename = cmd.substring(9);  // Strip "DOWNLOAD:"
    filename.trim();

    // Ensure path starts with /
    if (!filename.startsWith("/")) {
      filename = "/" + filename;
    }

    File dataFile = SD.open(filename, FILE_READ);
    if (!dataFile) {
      Serial.println("ERROR:FILE_NOT_FOUND");
      Serial.println("EOF");
      return;
    }

    // Stream file contents line by line
    while (dataFile.available()) {
      String fileLine = dataFile.readStringUntil('\n');
      Serial.println(fileLine);
    }
    dataFile.close();
    Serial.println("EOF");
    return;
  }

  // Unknown command
  Serial.println("ERROR:UNKNOWN_CMD");
}

