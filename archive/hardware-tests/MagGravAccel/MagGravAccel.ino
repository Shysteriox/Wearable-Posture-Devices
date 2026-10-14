#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_LSM6DS3TRC.h>
#include <Adafruit_LIS3MDL.h>

static const lsm6ds_accel_range_t ACCEL_RANGE = LSM6DS_ACCEL_RANGE_4_G;       // ±4 g
static const lsm6ds_gyro_range_t  GYRO_RANGE  = LSM6DS_GYRO_RANGE_250_DPS;    // ±250 °/s
static const lis3mdl_range_t      MAG_RANGE   = LIS3MDL_RANGE_4_GAUSS;    

Adafruit_LSM6DS3TRC lsm6ds3;
Adafruit_LIS3MDL lis3mdl;

void setup() {
  Serial.begin(115200);
  Serial.println("I²C Scanner:");
  delay(500);
  Wire.begin(21, 22);
  for (uint8_t addr = 1; addr < 127; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      Serial.print("Found device at 0x");
      Serial.println(addr, HEX);
    }
  }
  Serial.println();
  if (!lsm6ds3.begin_I2C(0x6a)) {
    Serial.println("Error: LSM6DS3TR-C not found");
    while (1) delay(10);
  }
  Serial.println("LSM6DS3TR-C detected!");
  if (!lis3mdl.begin_I2C()) {
    Serial.println("Error: LIS3MDL not found");
    while (1) delay(10);
  }
  Serial.println("LIS3MDL detected!");
  lsm6ds3.setAccelRange(ACCEL_RANGE);
  lsm6ds3.setGyroRange(GYRO_RANGE);
  lis3mdl.setRange(MAG_RANGE);
  Serial.println();
}
void loop() {
  sensors_event_t accel, gyro, temp;
  lsm6ds3.getEvent(&accel, &gyro, &temp);
  Serial.print("Accel (m/s²): ");
  Serial.print(accel.acceleration.x, 3); Serial.print(", ");
  Serial.print(accel.acceleration.y, 3); Serial.print(", ");
  Serial.println(accel.acceleration.z, 3);
  Serial.print("Gyro  (°/s):  ");
  Serial.print(gyro.gyro.x, 3); Serial.print(", ");
  Serial.print(gyro.gyro.y, 3); Serial.print(", ");
  Serial.println(gyro.gyro.z, 3);
  sensors_event_t mag;
  lis3mdl.getEvent(&mag);
  Serial.print("Mag   (gauss): ");
  Serial.print(mag.magnetic.x, 3); Serial.print(", ");
  Serial.print(mag.magnetic.y, 3); Serial.print(", ");
  Serial.println(mag.magnetic.z, 3);
  Serial.println("------------------------");
  delay(400);
}