#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_LSM6DS3TRC.h>
#include <Adafruit_LIS3MDL.h>
#include <MadgwickAHRS.h>
#include <math.h>

Madgwick filter;
Madgwick filter2;

static const lsm6ds_accel_range_t ACCEL_RANGE = LSM6DS_ACCEL_RANGE_4_G;
static const lsm6ds_gyro_range_t  GYRO_RANGE  = LSM6DS_GYRO_RANGE_250_DPS;
static const lis3mdl_range_t      MAG_RANGE   = LIS3MDL_RANGE_4_GAUSS;

Adafruit_LSM6DS3TRC lsm6ds3{};
Adafruit_LIS3MDL lis3mdl{};
Adafruit_LSM6DS3TRC lsm6ds3_2{};
Adafruit_LIS3MDL lis3mdl_2{};

TwoWire I2C_1 = TwoWire(0);

int listb[2000];
int list[20];
int num = 0;
int bias = -14;
double ax;
double ay;
double az;
double gx;
double gy;
double gz;
double mx;
double my;
double mz;
double ax_2;
double ay_2;
double az_2;
double gx_2;
double gy_2;
double gz_2;
double mx_2;
double my_2;
double mz_2;

void setup() {
  Serial.begin(115200);
  filter.begin(100);
  filter2.begin(100);
  Serial.println("I²C Scanner:");
  delay(500);
  I2C_1.begin(21, 22);
  Serial.println("Scanning I2C_1 on 21=SDA,22=SCL");
  for (uint8_t addr = 1; addr < 127; addr++) {
    I2C_1.beginTransmission(addr);
    if (I2C_1.endTransmission() == 0) {
      Serial.print(" Found @0x"); Serial.println(addr, HEX);
    }
  }
  Serial.println("Scanning I2C_2 on 34=SDA,35=SCL");
  if (!lsm6ds3.begin_I2C(0x6A, &I2C_1)) {Serial.println("! lsm6ds3 missing");}
  if (!lis3mdl.begin_I2C(0x1C, &I2C_1)) {Serial.println("! lis3mdl missing");}
  if (!lsm6ds3_2.begin_I2C(0x6B, &I2C_1)) {Serial.println("! lsm6ds3_2 missing");}
  if (!lis3mdl_2.begin_I2C(0x1E, &I2C_1)) {Serial.println("! lis3mdl_2 missing");}
  Serial.println("All sensors inited!");
  lsm6ds3.setAccelRange(ACCEL_RANGE);
  lsm6ds3.setGyroRange(GYRO_RANGE);
  lis3mdl.setRange(MAG_RANGE);
  lsm6ds3_2.setAccelRange(ACCEL_RANGE);
  lsm6ds3_2.setGyroRange(GYRO_RANGE);
  lis3mdl_2.setRange(MAG_RANGE);
  Serial.println();
}
void loop() {
  sensors_event_t accel, gyro, temp;
  lsm6ds3.getEvent(&accel, &gyro, &temp);
  sensors_event_t accel2, gyro2, temp2;
  lsm6ds3_2.getEvent(&accel2, &gyro2, &temp2);/*
  Serial.print("Accel (m/s²): ");
  Serial.print(accel.acceleration.x, 3); Serial.print(", ");
  Serial.print(accel.acceleration.y, 3); Serial.print(", ");
  Serial.println(accel.acceleration.z, 3);
  Serial.print("Gyro  (°/s):  ");
  Serial.print(gyro.gyro.x, 3); Serial.print(", ");
  Serial.print(gyro.gyro.y, 3); Serial.print(", ");
  Serial.println(gyro.gyro.z, 3);*/
  sensors_event_t mag;
  lis3mdl.getEvent(&mag);
  sensors_event_t mag2;
  lis3mdl_2.getEvent(&mag2);/*
  Serial.print("Mag   (gauss): ");
  Serial.print(mag.magnetic.x, 3); Serial.print(", ");
  Serial.print(mag.magnetic.y, 3); Serial.print(", ");
  Serial.println(mag.magnetic.z, 3); */
  ax = accel.acceleration.x / 9.80665;
  ay = accel.acceleration.y / 9.80665;
  az = accel.acceleration.z / 9.80665;
  gx = gyro.gyro.x;
  gy = gyro.gyro.y;
  gz = gyro.gyro.z;
  mx = mag.magnetic.x;
  my = mag.magnetic.y;
  mz = mag.magnetic.z;
  ax_2 = accel2.acceleration.x / 9.80665;
  ay_2 = accel2.acceleration.y / 9.80665;
  az_2 = accel2.acceleration.z / 9.80665;
  gx_2 = gyro2.gyro.x;
  gy_2 = gyro2.gyro.y;
  gz_2 = gyro2.gyro.z;
  mx_2 = mag2.magnetic.x;
  my_2 = mag2.magnetic.y;
  mz_2 = mag2.magnetic.z;
  filter.update(gx, gy, gz, ax, ay, az, mx, my, mz);
  Serial.print("Roll: ");  Serial.print(filter.getRoll());
  Serial.print(" Pitch: "); Serial.print(filter.getPitch());
  Serial.print(" Yaw: ");   Serial.print(filter.getYaw());
  filter2.update(gx_2, gy_2, gz_2, ax_2, ay_2, az_2, mx_2, my_2, mz_2);
  Serial.print("         Roll2: ");  Serial.print(filter2.getRoll());
  Serial.print(" Pitch2: "); Serial.print(filter2.getPitch());
  Serial.print(" Yaw2: ");   Serial.println(filter2.getYaw());
} 