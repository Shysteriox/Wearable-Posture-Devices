// POSTURE CORRECTOR v4.1 — Back + Neck monitoring
// Back sensors: CH0=Left shoulder, CH1=Right shoulder, CH2=Middle spine
// Neck sensor:  CH4=Head (on SDA/SCL 4-pin header). CH3 unused.
// Calibration saved to RTC. WDT restarts reload it instantly — no re-sit needed.
// SD capacity at 2s intervals: ~2MB/day. A 16GB card lasts 20+ years.

#include <Wire.h>
#include <SD.h>
#include <SPI.h>
#include <driver/gpio.h>
#include <esp_timer.h>
#include <math.h>

// ─── PINS ──────────────────────────────────────────────────
#define TCAADDR   0x70
#define SDA_PIN   21
#define SCL_PIN   22
#define SD_CS_PIN 5

#define VIB_NECK  25   // Head/neck buzzer motor
#define VIB_LEFT  33   // Swapped to match physical harness orientation
#define VIB_MID   32
#define VIB_RIGHT 26   // Swapped to match physical harness orientation

#define CH_LEFT  0
#define CH_RIGHT 1
#define CH_MID   2
// CH 3 intentionally unused (skip it everywhere)
#define CH_HEAD  4

// ─── THRESHOLDS ────────────────────────────────────────────
const float SLOUCH_THRESH = 18.0f;  // Degrees — spine forward bend
const float TILT_THRESH   = 18.0f;  // Degrees — shoulder lateral tilt
const float NECK_THRESH   = 18.0f;  // Degrees — head relative to spine
const unsigned long HOLD_MS  = 400;
const unsigned long READ_MS  = 300;
const unsigned long SD_MS    = 2000;
const unsigned long CALIB_MS = 5000;

// ─── SENSOR STATE (size 5: ch0-ch4, ch3 skipped) ──────────
bool    imuActive[5] = {false, false, false, false, false};
uint8_t imuAddr[5]   = {0x68, 0x68, 0x68, 0x68, 0x68};

float basePitch[5] = {0, 0, 0, 0, 0};
float sumPitch[5]  = {0, 0, 0, 0, 0};
int   calibSamples = 0;
bool  isCalibrated = false;
unsigned long calibStart = 0;

// RTC memory survives watchdog/software resets
RTC_NOINIT_ATTR float    rtc_basePitch[5];
RTC_NOINIT_ATTR uint32_t rtc_magic;

// ─── ALERT HOLD TRACKING (size 5) ──────────────────────────
// Motors: 0=MID, 1=LEFT, 2=RIGHT, 3=unused, 4=NECK
unsigned long holdStart[5] = {0, 0, 0, 0, 0};
bool          holding[5]   = {false, false, false, false, false};

// ─── SD ────────────────────────────────────────────────────
char logFile[20];
bool sdOK       = false;
unsigned long lastSD  = 0;
unsigned long lastRead = 0;

#include <esp_task_wdt.h>

// ─── WATCHDOG ──────────────────────────────────────────────
void wdt_reset() { esp_task_wdt_reset(); }

void wdt_start() {
  #if ESP_IDF_VERSION >= ESP_IDF_VERSION_VAL(5, 0, 0)
    esp_task_wdt_config_t wdt_config = {
      .timeout_ms = 12000,
      .idle_core_mask = 0,
      .trigger_panic = true
    };
    esp_task_wdt_reconfigure(&wdt_config);
  #else
    esp_task_wdt_init(12, true);
  #endif
  esp_task_wdt_add(NULL);
  wdt_reset();
}

// ─── MOTOR CONTROL ─────────────────────────────────────────
// Motor indices:  0=MID(back center), 1=LEFT, 2=RIGHT, 4=NECK(head)
const int motorPin[5] = {VIB_MID, VIB_LEFT, VIB_RIGHT, -1, VIB_NECK};
bool motorState[5] = {false, false, false, false, false};

void setMotor(int m, bool on) {
  if (m == 3) return; // ch3 unused
  int pin = motorPin[m];
  if (on) {
    if (!motorState[m]) {
      motorState[m] = true;
      analogWrite(pin, 100);
      delay(40);
      analogWrite(pin, 175);
    }
  } else {
    if (motorState[m]) {
      motorState[m] = false;
      analogWrite(pin, 0);
    }
  }
}

void allOff() {
  for (int m = 0; m < 5; m++) {
    if (m == 3) continue;
    motorState[m] = false;
    analogWrite(motorPin[m], 0);
  }
}

bool motorUpdate(int m, bool bad) {
  if (m == 3) return false;
  unsigned long now = millis();
  if (bad) {
    if (!holding[m]) { holding[m] = true; holdStart[m] = now; }
    bool on = (now - holdStart[m] >= HOLD_MS);
    setMotor(m, on);
    return on;
  } else {
    holding[m] = false; setMotor(m, false); return false;
  }
}

// ─── SOFTWARE I2C (BIT-BANG) ───────────────────────────────
#define SDA_LOW()   { pinMode(SDA_PIN, OUTPUT); digitalWrite(SDA_PIN, LOW); }
#define SDA_HIGH()  { pinMode(SDA_PIN, INPUT_PULLUP); }
#define SCL_LOW()   { pinMode(SCL_PIN, OUTPUT); digitalWrite(SCL_PIN, LOW); }
#define SDA_READ()  digitalRead(SDA_PIN)

inline void sw_i2c_delay() { delayMicroseconds(4); }

bool i2c_scl_high() {
  pinMode(SCL_PIN, INPUT_PULLUP);
  int timeout = 1000;
  while (digitalRead(SCL_PIN) == LOW) {
    delayMicroseconds(1);
    if (--timeout == 0) return false;
  }
  return true;
}

void i2c_start() {
  SDA_HIGH(); i2c_scl_high(); sw_i2c_delay();
  SDA_LOW(); sw_i2c_delay();
  SCL_LOW(); sw_i2c_delay();
}

void i2c_stop() {
  SDA_LOW(); i2c_scl_high(); sw_i2c_delay();
  SDA_HIGH(); sw_i2c_delay();
}

bool i2c_write_byte(uint8_t byte) {
  for (int i = 0; i < 8; i++) {
    if (byte & 0x80) { SDA_HIGH(); } else { SDA_LOW(); }
    byte <<= 1;
    sw_i2c_delay();
    if (!i2c_scl_high()) return false;
    sw_i2c_delay();
    SCL_LOW();
  }
  SDA_HIGH();
  sw_i2c_delay();
  if (!i2c_scl_high()) return false;
  sw_i2c_delay();
  bool ack = (SDA_READ() == 0);
  SCL_LOW();
  return ack;
}

uint8_t i2c_read_byte(bool ack) {
  uint8_t byte = 0;
  SDA_HIGH();
  for (int i = 0; i < 8; i++) {
    sw_i2c_delay();
    if (!i2c_scl_high()) return 0;
    sw_i2c_delay();
    byte <<= 1;
    if (SDA_READ()) byte |= 1;
    SCL_LOW();
  }
  if (ack) { SDA_LOW(); } else { SDA_HIGH(); }
  sw_i2c_delay();
  i2c_scl_high();
  sw_i2c_delay();
  SCL_LOW();
  SDA_HIGH();
  return byte;
}

bool i2c_read_bytes(uint8_t addr, uint8_t reg, uint8_t* buf, int len) {
  i2c_start();
  if (!i2c_write_byte(addr << 1)) { i2c_stop(); return false; }
  if (!i2c_write_byte(reg)) { i2c_stop(); return false; }
  i2c_start();
  if (!i2c_write_byte((addr << 1) | 1)) { i2c_stop(); return false; }
  for (int i = 0; i < len; i++) {
    buf[i] = i2c_read_byte(i < len - 1);
  }
  i2c_stop();
  return true;
}

// ─── MEDIAN FILTER (size 5 channels) ──────────────────────
#define FILTER_SIZE 5
float pitchHistory[5][FILTER_SIZE];
int historyCount[5] = {0, 0, 0, 0, 0};

void addHistory(int ch, float val) {
  for (int i = FILTER_SIZE - 1; i > 0; i--)
    pitchHistory[ch][i] = pitchHistory[ch][i - 1];
  pitchHistory[ch][0] = val;
  if (historyCount[ch] < FILTER_SIZE) historyCount[ch]++;
}

float getMedian(int ch) {
  int count = historyCount[ch];
  if (count == 0) return 0.0f;
  float temp[FILTER_SIZE];
  for (int i = 0; i < count; i++) temp[i] = pitchHistory[ch][i];
  for (int i = 1; i < count; i++) {
    float key = temp[i]; int j = i - 1;
    while (j >= 0 && temp[j] > key) { temp[j+1] = temp[j]; j--; }
    temp[j+1] = key;
  }
  return temp[count / 2];
}

void clearHistory() {
  for (int ch = 0; ch < 5; ch++) {
    if (ch == 3) continue;
    historyCount[ch] = 0;
    for (int i = 0; i < FILTER_SIZE; i++) pitchHistory[ch][i] = 0.0f;
  }
}

void resetI2C() {
  SDA_HIGH();
  pinMode(SCL_PIN, OUTPUT);
  for (int i = 0; i < 9; i++) {
    digitalWrite(SCL_PIN, LOW);  delayMicroseconds(5);
    digitalWrite(SCL_PIN, HIGH); delayMicroseconds(5);
  }
  pinMode(SCL_PIN, INPUT_PULLUP);
}

bool tcaselect(uint8_t ch) {
  i2c_start();
  if (!i2c_write_byte(TCAADDR << 1)) { i2c_stop(); return false; }
  if (!i2c_write_byte(1 << ch)) { i2c_stop(); return false; }
  i2c_stop();
  delayMicroseconds(500);
  return true;
}

bool tryInit(uint8_t addr) {
  i2c_start();
  if (!i2c_write_byte(addr << 1)) { i2c_stop(); return false; }
  if (!i2c_write_byte(0x6B)) { i2c_stop(); return false; }
  if (!i2c_write_byte(0x00)) { i2c_stop(); return false; }
  i2c_stop();
  delay(5);
  uint8_t id = 0;
  if (!i2c_read_bytes(addr, 0x75, &id, 1)) return false;
  return (id == 0x68 || id == 0x70 || id == 0x72);
}

bool initCh(uint8_t ch) {
  if (!tcaselect(ch)) return false;
  if (tryInit(0x68)) { imuAddr[ch] = 0x68; return true; }
  if (tryInit(0x69)) { imuAddr[ch] = 0x69; return true; }
  return false;
}

// readAngles: pitch = forward/back tilt, roll = side tilt
bool readAngles(uint8_t ch, float &pitch, float &roll) {
  if (!tcaselect(ch)) return false;
  uint8_t buf[6];
  if (!i2c_read_bytes(imuAddr[ch], 0x3B, buf, 6)) return false;
  int16_t ax = (int16_t)(buf[0] << 8 | buf[1]);
  int16_t ay = (int16_t)(buf[2] << 8 | buf[3]);
  int16_t az = (int16_t)(buf[4] << 8 | buf[5]);
  pitch = atan2f(-(float)ax, sqrtf((float)(ay*ay + az*az))) * 180.0f / M_PI;
  roll  = atan2f((float)ay, (float)az) * 180.0f / M_PI;
  return true;
}

void initSD() {
  pinMode(SD_CS_PIN, OUTPUT);
  digitalWrite(SD_CS_PIN, HIGH);
  gpio_set_pull_mode((gpio_num_t)18, GPIO_PULLUP_ONLY);
  gpio_set_pull_mode((gpio_num_t)19, GPIO_PULLUP_ONLY);
  gpio_set_pull_mode((gpio_num_t)23, GPIO_PULLUP_ONLY);
  SPI.begin(18, 19, 23, SD_CS_PIN);
  for (int a = 0; a < 3; a++) {
    if (SD.begin(SD_CS_PIN, SPI, 400000)) {
      sdOK = true;
      int idx = 1;
      do { sprintf(logFile, "/POST_%04d.CSV", idx++);
      } while (SD.exists(logFile) && idx < 9999);
      File f = SD.open(logFile, FILE_WRITE);
      // Columns: ms, mid(back pitch), left(roll), right(roll),
      //          head(head pitch deviation), ctr(back bad), lft, rgt, nck(neck bad)
      if (f) { f.println(F("ms,mid,left,right,head,ctr,lft,rgt,nck")); f.close(); }
      Serial.print(F("[SD] ")); Serial.println(logFile);
      return;
    }
    delay(300);
  }
  Serial.println(F("[SD] none"));
}

// ─── SETUP ─────────────────────────────────────────────────
void printResetReason() {
  esp_reset_reason_t r = esp_reset_reason();
  Serial.print(F("[SYS] Reset reason: "));
  switch(r) {
    case ESP_RST_UNKNOWN:   Serial.println(F("UNKNOWN")); break;
    case ESP_RST_POWERON:   Serial.println(F("POWERON")); break;
    case ESP_RST_EXT:       Serial.println(F("EXT_PIN")); break;
    case ESP_RST_SW:        Serial.println(F("SOFTWARE")); break;
    case ESP_RST_PANIC:     Serial.println(F("PANIC_CRASH")); break;
    case ESP_RST_INT_WDT:   Serial.println(F("INTERRUPT_WDT")); break;
    case ESP_RST_TASK_WDT:  Serial.println(F("TASK_WDT")); break;
    case ESP_RST_WDT:       Serial.println(F("OTHER_WDT")); break;
    case ESP_RST_DEEPSLEEP: Serial.println(F("DEEPSLEEP")); break;
    case ESP_RST_BROWNOUT:  Serial.println(F("BROWNOUT")); break;
    case ESP_RST_SDIO:      Serial.println(F("SDIO")); break;
    default:                Serial.println(F("OTHER")); break;
  }
}

void setup() {
  Serial.begin(115200);
  delay(800);

  pinMode(VIB_NECK,  OUTPUT); digitalWrite(VIB_NECK,  LOW);
  pinMode(VIB_LEFT,  OUTPUT); digitalWrite(VIB_LEFT,  LOW);
  pinMode(VIB_MID,   OUTPUT); digitalWrite(VIB_MID,   LOW);
  pinMode(VIB_RIGHT, OUTPUT); digitalWrite(VIB_RIGHT, LOW);

  Serial.println(F("POSTURE v4.1"));
  printResetReason();
  Serial.print(F("[SYS] Free Heap: ")); Serial.print(ESP.getFreeHeap()); Serial.println(F(" bytes"));

  esp_reset_reason_t r = esp_reset_reason();
  if (r == ESP_RST_POWERON || r == ESP_RST_EXT) {
    rtc_magic = 0;
    clearHistory();
  }

  resetI2C();
  delay(100);

  // Initialize channels 0,1,2,4 (skip 3)
  for (uint8_t t = 0; t < 5; t++) {
    if (t == 3) continue;
    imuActive[t] = initCh(t);
    Serial.print(F("Ch")); Serial.print(t);
    Serial.println(imuActive[t] ? F(":OK") : F(":off"));
  }

  initSD();
  wdt_start();

  if (rtc_magic == 0x55AA55AA) {
    isCalibrated = true;
    for (int i = 0; i < 5; i++) basePitch[i] = rtc_basePitch[i];
    Serial.print(F("[SYS] Loaded RTC Cal: L=")); Serial.print(basePitch[CH_LEFT], 1);
    Serial.print(F(" R=")); Serial.print(basePitch[CH_RIGHT], 1);
    Serial.print(F(" M=")); Serial.print(basePitch[CH_MID], 1);
    Serial.print(F(" H=")); Serial.println(basePitch[CH_HEAD], 1);
    digitalWrite(VIB_MID, HIGH); delay(200); digitalWrite(VIB_MID, LOW);
  } else {
    Serial.println(F("Sit still — calibrating in 3s..."));
    digitalWrite(VIB_MID, HIGH); delay(150); digitalWrite(VIB_MID, LOW);
    delay(100);
    digitalWrite(VIB_MID, HIGH); delay(150); digitalWrite(VIB_MID, LOW);
    delay(3000);
    calibStart = millis();
  }
}

void checkSerialCommands() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd.equalsIgnoreCase(F("dump"))) {
      if (!sdOK) { Serial.println(F("[CMD] SD offline")); return; }
      Serial.println(F("=== START DUMP ==="));
      File f = SD.open(logFile, FILE_READ);
      if (f) {
        while (f.available()) Serial.write(f.read());
        f.close();
        Serial.println(F("=== END DUMP ==="));
      } else { Serial.println(F("[CMD] Open fail")); }
    } else if (cmd.equalsIgnoreCase(F("list"))) {
      if (!sdOK) { Serial.println(F("[CMD] SD offline")); return; }
      Serial.println(F("=== SD FILES ==="));
      File root = SD.open("/");
      if (root) {
        File file = root.openNextFile();
        while (file) {
          Serial.print(file.name()); Serial.print(F(" \t")); Serial.println(file.size());
          file = root.openNextFile();
        }
        root.close();
      }
    } else if (cmd.equalsIgnoreCase(F("clear"))) {
      if (sdOK) { SD.remove(logFile); Serial.println(F("[CMD] Current log cleared")); }
    } else if (cmd.startsWith(F("read "))) {
      if (!sdOK) { Serial.println(F("[CMD] SD offline")); return; }
      String fname = cmd.substring(5); fname.trim();
      if (!fname.startsWith("/")) fname = "/" + fname;
      File f = SD.open(fname, FILE_READ);
      if (f) {
        Serial.print(F("=== START: ")); Serial.println(fname);
        while (f.available()) Serial.write(f.read());
        f.close(); Serial.println(F("=== END ==="));
      } else { Serial.println(F("[CMD] File not found")); }
    } else {
      Serial.println(F("[CMD] Commands: dump, list, clear, read <filename>"));
    }
  }
}

// ─── ACTIVE VIBRATION BLANKING ─────────────────────────────
bool tempSilenced = false;
void tempSilenceMotors() {
  bool active = motorState[0] || motorState[1] || motorState[2] || motorState[4];
  if (active) {
    analogWrite(VIB_MID,  0);
    analogWrite(VIB_LEFT, 0);
    analogWrite(VIB_RIGHT,0);
    analogWrite(VIB_NECK, 0);
    delay(40);
    tempSilenced = true;
  }
}

void restoreMotors() {
  if (tempSilenced) {
    for (int m = 0; m < 5; m++) {
      if (m == 3) continue;
      if (motorState[m]) analogWrite(motorPin[m], 175);
    }
    tempSilenced = false;
  }
}

// ─── LOOP ──────────────────────────────────────────────────
void loop() {
  checkSerialCommands();
  delay(1);

  unsigned long now = millis();
  if (now - lastRead < READ_MS) return;
  lastRead = now;

  wdt_reset();

  // Silence all motors before reading IMUs to prevent vibration feedback
  tempSilenceMotors();

  float pitch[5] = {0, 0, 0, 0, 0};
  bool  good[5]  = {false, false, false, false, false};
  int   cnt = 0;

  for (uint8_t ch = 0; ch < 5; ch++) {
    if (ch == 3) continue;
    if (!imuActive[ch]) continue;
    float p = 0.0f, r = 0.0f;
    if (readAngles(ch, p, r)) {
      // Shoulder sensors (ch0,ch1) track roll for side tilt.
      // Spine (ch2) and Head (ch4) track pitch for forward bend.
      float rawVal = (ch == CH_MID || ch == CH_HEAD) ? p : r;
      addHistory(ch, rawVal);
    }
    if (historyCount[ch] > 0) {
      pitch[ch] = getMedian(ch);
      good[ch] = true;
      cnt++;
    }
  }

  restoreMotors();

  if (cnt == 0) { resetI2C(); return; }

  // ── CALIBRATION ──
  if (!isCalibrated) {
    unsigned long elapsed = now - calibStart;
    if (elapsed < CALIB_MS) {
      for (int t = 0; t < 5; t++) {
        if (t == 3) continue;
        if (good[t]) sumPitch[t] += pitch[t];
      }
      calibSamples++;
      int remain = (CALIB_MS - elapsed) / 1000 + 1;
      static int lastRemainPrinted = -1;
      if (remain != lastRemainPrinted) {
        Serial.print(remain); Serial.println(F("s..."));
        lastRemainPrinted = remain;
      }
      return;
    }
    isCalibrated = true;
    int n = max(calibSamples, 1);
    for (int t = 0; t < 5; t++) {
      if (t == 3) continue;
      basePitch[t] = sumPitch[t] / n;
      rtc_basePitch[t] = basePitch[t];
    }
    rtc_magic = 0x55AA55AA;
    Serial.print(F("CALIB DONE L=")); Serial.print(basePitch[CH_LEFT], 1);
    Serial.print(F(" R=")); Serial.print(basePitch[CH_RIGHT], 1);
    Serial.print(F(" M=")); Serial.print(basePitch[CH_MID], 1);
    Serial.print(F(" H=")); Serial.println(basePitch[CH_HEAD], 1);
    // Double-buzz all active motors to confirm calibration done
    for (int m = 0; m < 5; m++) { if (m != 3) setMotor(m, true); }
    delay(400);
    for (int m = 0; m < 5; m++) { if (m != 3) setMotor(m, false); }
    delay(200);
    for (int m = 0; m < 5; m++) { if (m != 3) setMotor(m, true); }
    delay(400);
    for (int m = 0; m < 5; m++) { if (m != 3) setMotor(m, false); }
    return;
  }

  // ── MONITORING ──
  float dL = good[CH_LEFT]  ? pitch[CH_LEFT]  - basePitch[CH_LEFT]  : 0;
  float dR = good[CH_RIGHT] ? pitch[CH_RIGHT] - basePitch[CH_RIGHT] : 0;
  float dM = good[CH_MID]   ? pitch[CH_MID]   - basePitch[CH_MID]   : 0;
  float dH = good[CH_HEAD]  ? pitch[CH_HEAD]  - basePitch[CH_HEAD]  : 0;

  // ── BACK DETECTION ──
  bool slouch = fabsf(dM) > SLOUCH_THRESH;

  bool tiltLeft  = false;
  bool tiltRight = false;
  float absL = fabsf(dL);
  float absR = fabsf(dR);
  if (absL > TILT_THRESH || absR > TILT_THRESH) {
    if (absL >= absR) tiltLeft  = true;
    else              tiltRight = true;
  }

  bool anyTilt = tiltLeft || tiltRight;
  bool backBad = slouch || anyTilt;

  // ── NECK DETECTION ──
  // dNeck = head angle relative to spine — cancels out body sway
  float dNeck = dH - dM;
  // Only flag neck if the head sensor is actually active
  bool neckBad = good[CH_HEAD] && (fabsf(dNeck) > NECK_THRESH);

  // ── MOTOR OUTPUTS ──
  // Back: all 3 back motors buzz together for any back violation
  motorUpdate(0, backBad); // MID
  motorUpdate(1, backBad); // LEFT
  motorUpdate(2, backBad); // RIGHT
  // Neck: only the neck/head motor buzzes for neck violations
  motorUpdate(4, neckBad); // NECK

  // ── SERIAL OUTPUT ──
  Serial.print(now / 1000); Serial.print(F("s M="));
  Serial.print(dM, 1); Serial.print(F(" L="));
  Serial.print(dL, 1); Serial.print(F(" R="));
  Serial.print(dR, 1); Serial.print(F(" H="));
  Serial.print(dH, 1); Serial.print(F(" N="));
  Serial.print(dNeck, 1); Serial.print(F("  "));
  if (!backBad && !neckBad) {
    Serial.print(F("OK"));
  } else {
    if (slouch)    Serial.print(F("SLOUCH "));
    if (tiltLeft)  Serial.print(F("TILT-L "));
    if (tiltRight) Serial.print(F("TILT-R "));
    if (neckBad)   Serial.print(F("NECK "));
  }
  Serial.print(F(" RAM:")); Serial.println(ESP.getFreeHeap());

  // ── SD LOGGING ──
  if (sdOK && now - lastSD >= SD_MS) {
    lastSD = now;
    File f = SD.open(logFile, FILE_APPEND);
    if (f) {
      f.print(now);        f.print(',');
      f.print(dM, 2);      f.print(',');
      f.print(dL, 2);      f.print(',');
      f.print(dR, 2);      f.print(',');
      f.print(dNeck, 2);   f.print(',');  // head deviation relative to spine
      f.print(backBad ? 1 : 0);  f.print(',');
      f.print(tiltLeft  ? 1 : 0); f.print(',');
      f.print(tiltRight ? 1 : 0); f.print(',');
      f.println(neckBad ? 1 : 0);
      f.close();
    }
  }
}
