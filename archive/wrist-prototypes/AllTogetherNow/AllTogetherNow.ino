#include "config.h"                       //has wifi password, and adafruit login
#include <Wire.h>                         //helps identify different inputs and outputs
#include <Adafruit_Sensor.h>              //base adafruit library
#include <Adafruit_LSM6DS3TRC.h>          //accelerometer and gyrometer
#include <Adafruit_LIS3MDL.h>             //magnometer
#include <MadgwickAHRS.h>                 //filter for accelerometer, magnometer, gyrometer
#include <math.h>                         //math library
#include <Adafruit_NeoPixel.h>            //LED Neopixel library

#define LED_PIN 12                                                        //pin number for LED ring
#define LED_COUNT 16                                                      //defining the amount of LEDs on the ring

Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);        //defining the LED Ring
int j = 50;                                                               //counter
unsigned long lastLEDUpdate1 = 0;                                         //checking for the last time of the LED update for the first
const int LEDInterval = 3;                                                //checking for the interval of the LED update for the first
unsigned long lastLEDUpdate2 = 0;                                         //checking for the last time of the LED update for the second
const int LEDInterval2 = 3;                                               //checking for the interval of the LED update for the second
boolean flash_vibra1 = false;                                             //1st vibrators check
boolean flash_vibra2 = false;                                             //2nd vibrators check
boolean flash_vibra3 = false;                                             //3rd vibrators check
boolean flash_vibra4 = false;                                             //4th vibrators check
boolean flashing = false;                                                 //setting the LEDs to off
boolean LED = false;                                                      //checking if its time to point
int flash = 0;                                                            //the center LED that is flashing, 2, 6, 10.14

Madgwick filter;                                                          //first filter
Madgwick filter2;                                                         //second filter

static const lsm6ds_accel_range_t ACCEL_RANGE = LSM6DS_ACCEL_RANGE_4_G;                 //range of accelerometer
static const lsm6ds_gyro_range_t  GYRO_RANGE  = LSM6DS_GYRO_RANGE_250_DPS;              //range of gyrometer
static const lis3mdl_range_t      MAG_RANGE   = LIS3MDL_RANGE_4_GAUSS;                  //range of magnometer

Adafruit_LSM6DS3TRC lsm6ds3{};            //defining the first accelerometer and gyrometer
Adafruit_LIS3MDL lis3mdl{};               //defining the first magnometer
Adafruit_LSM6DS3TRC lsm6ds3_2{};          //defining the second accelerometer and gyrometer
Adafruit_LIS3MDL lis3mdl_2{};             //defining the second magnometer

TwoWire I2C_1 = TwoWire(0);               // defines the I^2C
double ax;                                //First Accelerometer's X
double ay;                                //First Accelerometer's Y
double az;                                //First Accelerometer's Z
double gx;                                //First Gyrometer's X
double gy;                                //First Gyrometer's Y
double gz;                                //First Gyrometer's Z
double mx;                                //First Magnometer's X
double my;                                //First Magnometer's Y
double mz;                                //First Magnometer's Z
double ax_2;                              //Second Accelerometer's X
double ay_2;                              //Second Accelerometer's Y
double az_2;                              //Second Accelerometer's Z
double gx_2;                              //Second Gyrometer's X
double gy_2;                              //Second Gyrometer's Y
double gz_2;                              //Second Gyrometer's Z
double mx_2;                              //Second Magnometer's X
double my_2;                              //Second Magnometer's Y
double mz_2;                              //Second Magnometer's Z

double roll = 0;                          //First Roll
double pitch = 0;                         //First Pitch
double yaw = 0;                           //First Yaw
double roll2 = 0;                         //Second Roll
double pitch2 = 0;                        //Second Pitch
double yaw2 = 0;                          //Second Yaw
double angle = 0;                         //Angle of Flex Sensor
double pitchDiff = 0;                     //Difference in the Pitches
double yawDiff = 0;                       //Difference in the Yaws
double rollDiff = 0;                      //Difference in the Rolls
int listb[2000] = {0};                    //List of all angles based on each return value from the flex sensor
int list[10];                             //List of the last 20 averages in the flex sensor
int num = 0;                              //current iterating number in the average list
int bias = -70;                           //Bias of the flex sensor
int period = 12 *1000;                    //Amount of time between each data send
int var = 1;                              //Amount of times the period has been completed

const int Vibra1 = 25;                    //Vibrator 1 Pin
const int Vibra2 = 26;                    //Vibrator 2 Pin
const int Vibra3 = 27;                    //Vibrator 3 Pin
const int Vibra4 = 13;                    //Vibrator 4 Pin

AdafruitIO_Feed *Roll = io.feed("Roll");                            //The feed of data for the roll
AdafruitIO_Feed *Pitch = io.feed("Pitch");                          //The feed of data for the pitch
AdafruitIO_Feed *Yaw = io.feed("Yaw");                              //The feed of data for the yaw
AdafruitIO_Feed *Roll2 = io.feed("Roll2");                          //The feed of data for the second roll
AdafruitIO_Feed *Pitch2 = io.feed("Pitch2");                        //The feed of data for the second pitch 
AdafruitIO_Feed *Yaw2 = io.feed("Yaw2");                            //The feed of data for the second yaw
AdafruitIO_Feed *RollDiff = io.feed("RollDiff");                    //The feed of data for the difference in the rolls
AdafruitIO_Feed *PitchDiff = io.feed("PitchDiff");                  //The feed of data for the difference in the pitches
AdafruitIO_Feed *YawDiff = io.feed("YawDiff");                      //The feed of data for the differences in the yaws
AdafruitIO_Feed *Angle = io.feed("Angle");                          //The feed of data for the angle fo the flex sensor

void partyMode() {                              //for when you're a little down
  uint16_t i, j;                                //defining the loop variables
  for(j = 0; j < 256; j++) {                    //outer loop
    for(i = 0; i < strip.numPixels(); i++) {    //one for each pin
      strip.setPixelColor(i, strip.ColorHSV((i * 65536 / strip.numPixels() + j * 256) % 65536));    
    }                                           //rainbow
    strip.show();                               //showing the rainbow
    delay(5);                                   //wait for 5 milliseconds
  }
}


void setup() {
  Serial.begin(115200);                                             //setting up the serial monitor
  while(! Serial);                                                  //checking for connection to Adafruit IO
  Serial.print("Connecting to Adafruit IO");
  io.connect();
  while(io.status() < AIO_CONNECTED) {
    Serial.print(".");
    delay(500);
  }
  Serial.println();
  Serial.println(io.statusText());
  filter.begin(8);
  filter2.begin(8);
  Serial.println("I²C Scanner:");
  delay(500);
  pinMode(Vibra1, OUTPUT);                    //setting up vibrator 1 pin
  pinMode(Vibra2, OUTPUT);                    //setting up vibrator 2 pin
  pinMode(Vibra3, OUTPUT);                    //setting up vibrator 3 pin
  pinMode(Vibra4, OUTPUT);                    //setting up vibrator 4 pin
  I2C_1.begin(21, 22);                        //I^2C pin identification
 
 
  Serial.println("Scanning I2C_1 on 21=SDA,22=SCL");
  for (uint8_t addr = 1; addr < 127; addr++) {
    I2C_1.beginTransmission(addr);
    if (I2C_1.endTransmission() == 0) {
      Serial.print(" Found @0x"); Serial.println(addr, HEX);
    }
  }
  if (!lsm6ds3.begin_I2C(0x6A, &I2C_1)) {Serial.println("! lsm6ds3 missing");}          //checking for the accelerometer and gyrometer
  if (!lis3mdl.begin_I2C(0x1C, &I2C_1)) {Serial.println("! lis3mdl missing");}          //checking for the magnometer
  if (!lsm6ds3_2.begin_I2C(0x6B, &I2C_1)) {Serial.println("! lsm6ds3_2 missing");}      //checking for the accelerometer and gyrometer
  if (!lis3mdl_2.begin_I2C(0x1E, &I2C_1)) {Serial.println("! lis3mdl_2 missing");}      //checking for the magnometer
  Serial.println("All sensors initiated!");
 
 
  lsm6ds3.setAccelRange(ACCEL_RANGE);                 //setting range of accelerometer
  lsm6ds3.setGyroRange(GYRO_RANGE);                   //setting range of gyrometer
  lsm6ds3.setAccelDataRate(LSM6DS_RATE_26_HZ);
  lsm6ds3.setGyroDataRate(LSM6DS_RATE_26_HZ);
  lis3mdl.setRange(MAG_RANGE);                        //setting range of magnometer

  lsm6ds3_2.setAccelRange(ACCEL_RANGE);               //setting range of second accelerometer
  lsm6ds3_2.setGyroRange(GYRO_RANGE);                 //setting range of second gyrometer
  lsm6ds3_2.setAccelDataRate(LSM6DS_RATE_26_HZ);
  lsm6ds3_2.setGyroDataRate(LSM6DS_RATE_26_HZ);
  lis3mdl_2.setRange(MAG_RANGE);                      //setting range of second magnometer
  Serial.println();
 
 
  for (int i = 100; i < 2000; i++)                    //filling the array with the angles 
  {
    listb[i] = 103.1004*log(0.00326145 * i - 0.320527) + 
    -12.20153 * cos(0.0201778 * i + 2.97212) +
    1.61817 * cos(0.0302185 * i - 0.222821) +
    -0.222821 * cos(0.00297744 * i -23.88627) +
    -1.74187 * cos(0.0824802 * i + 2.8118) +
    2.8118 * cos(0.0674563 * i - 4.6551) +
    -317.21621 * cos(0.0425672 * i -23.51092) +
    316.51257 * cos(0.0425325 * i + 1.64691) +
    8.9505 * cos(0.0220089 * i + 1.66444);
  }
  strip.begin();                                      //starting the strip
  strip.setBrightness(100);                           //dimming the lights
  for(int i = 0; i < 16; i++) {                       //one run for each light
    strip.setPixelColor(i, 0, 255, 0);}               //setting all to base green
  strip.show();                                       //showing the green
}
void loop() {
  io.run();                                               //Starting the website
  sensors_event_t accel, gyro, temp;                      //setting the events of accelerometer and gyrometer
  lsm6ds3.getEvent(&accel, &gyro, &temp);                 //getting the events of accelerometer and gyrometer
  sensors_event_t accel2, gyro2, temp2;                   //setting the events of second accelerometer and gyrometer
  lsm6ds3_2.getEvent(&accel2, &gyro2, &temp2);            //getting the events of second accelerometer and gyrometer
  sensors_event_t mag;                                    //setting the events of magnometer
  lis3mdl.getEvent(&mag);                                 //getting the events of magnometer
  sensors_event_t mag2;                                   //setting the events of second magnometer
  lis3mdl_2.getEvent(&mag2);                              //getting the events of second magnometer
 
 
  ax = accel.acceleration.x / 9.80665;                    //getting the acceleration's X in terms of Gs
  ay = accel.acceleration.y / 9.80665;                    //getting the acceleration's Y in terms of Gs
  az = accel.acceleration.z / 9.80665;                    //getting the acceleration's Z in terms of Gs
  gx = gyro.gyro.x * 180/3.145192653;                     //getting the gyrometer's X
  gy = gyro.gyro.y * 180/3.145192653;                     //getting the gyrometer's Y
  gz = gyro.gyro.z * 180/3.145192653;                     //getting the gyrometer's Z
  mx = mag.magnetic.x;                                    //getting the magnometer's X
  my = mag.magnetic.y;                                    //getting the magnometer's Y
  mz = mag.magnetic.z;                                    //getting the magnometer's Z
  ax_2 = accel2.acceleration.x / 9.80665;                 //getting the second acceleration's X in terms of Gs
  ay_2 = accel2.acceleration.y / 9.80665;                 //getting the second acceleration's Y in terms of Gs
  az_2 = accel2.acceleration.z / 9.80665;                 //getting the second acceleration's Z in terms of Gs
  gx_2 = gyro2.gyro.x * 180/3.141592653;                  //getting the second gyrometer's X
  gy_2 = gyro2.gyro.y * 180/3.141592653;                  //getting the second gyrometer's Y
  gz_2 = gyro2.gyro.z * 180/3.141592653;                  //getting the second gyrometer's Z
  mx_2 = mag2.magnetic.x;                                 //getting the second magnometer's X
  my_2 = mag2.magnetic.y;                                 //getting the second magnometer's Y
  mz_2 = mag2.magnetic.z;                                 //getting the second magnometer's Z
 

  filter.update(gx, gy, gz, ax, ay, az, mx, my, mz);              //updating the filter with the first values
  if (millis() >= var * period){                                  //checking if its time to send the values to the website
    Roll->save(filter.getRoll());                                 //sending the roll
    Pitch->save(filter.getPitch());                               //sending the pitch
    Yaw->save(filter.getYaw());}                                  //sending the yaw
  Serial.print("Roll: ");  Serial.print(filter.getRoll());        //printing the roll in the serial monitor
  Serial.print(" Pitch: "); Serial.print(filter.getPitch());      //printing the pitch in the serial monitor
  Serial.print(" Yaw: ");   Serial.print(filter.getYaw());        //printing the yaw in the serial monitor


  filter2.update(gx_2, gy_2, gz_2, ax_2, ay_2, az_2, mx, my, mz);                     //updating the filter with the second values
  if (millis() >= var * period){                                                      //checking if its time to send the values to the website  
    Roll2->save(filter2.getRoll());                                                   //sending the second roll
    Pitch2->save(filter2.getPitch());                                                 //sending the second pitch
    Yaw2->save(filter2.getYaw());}                                                    //sending the second yaw
  Serial.print("      Roll2: ");  Serial.print(filter2.getRoll());                    //printing the second roll in the serial monitor
  Serial.print(" Pitch2: "); Serial.print(filter2.getPitch());                        //printing the second pitch in the serial monitor
  Serial.print(" Yaw2: ");   Serial.print(filter2.getYaw());                          //printing the second yaw in the serial monitor
  num = listb[min((int)analogRead(34),1999)] + bias;                                  //retrieving the angle value


  if (millis() >= var * period){                                                      //checking if its time to send the values to the website  
    if (filter.getRoll() > filter2.getRoll()){RollDiff->save(abs(filter.getRoll() - filter2.getRoll()));}                                     //sending the difference in roll
    else{RollDiff->save(abs(filter2.getRoll() - filter.getRoll()));}
    if (filter.getPitch() > filter2.getPitch()){PitchDiff->save(abs(filter.getPitch() - filter2.getPitch()));}                                //sending the difference in pitch
    else{PitchDiff->save(abs(filter2.getPitch() - filter.getPitch()));}
    if (filter.getYaw() > filter2.getYaw()){YawDiff->save(abs(abs(filter.getYaw() - filter2.getYaw())-10));}                                  //sending the difference in yaw
    else{YawDiff->save(abs(abs(filter2.getYaw() - filter.getYaw())-10));}}
  if (filter.getRoll() > filter2.getRoll()){Serial.print("      RollDiff: ");  Serial.print(abs(filter.getRoll() - filter2.getRoll()));}      //printing the difference in roll
  else{Serial.print("      RollDiff: ");  Serial.print(abs(filter2.getRoll() - filter.getRoll()));}
  if (filter.getPitch() > filter2.getPitch()){Serial.print(" PitchDiff: "); Serial.print(abs(filter.getPitch() - filter2.getPitch()));}       //printing the difference in pitch
  else{Serial.print(" PitchDiff: "); Serial.print(abs(filter2.getPitch() - filter.getPitch()));}
  if (filter.getYaw() > filter2.getYaw()){Serial.print(" YawDiff: ");   Serial.print(abs(abs(filter.getYaw() - filter2.getYaw())-10));}       //printing the difference in yaw
  else{Serial.print(" YawDiff: ");   Serial.print(abs(abs(filter2.getYaw() - filter.getYaw())-10));}


  int ave = 0;                                                      //average of the angle's 10 last values
  for (int i = 1; i < 10; i++){                                     //shifting the values to the left
    list[i-1] = list[i];}
  list[9] = num;                                                    //adding the new value
  for (int i = 0; i < 10; i++){                                     //adding up all the values
    ave += list[i];} 
  ave = ave/10;                                                     //dividing the sum by the amount to get the average
  if (millis() >= var * period){                                    //checking if its time to send the values to the website  
    Angle->save(ave);}                                              //sending the value of the angle
  Serial.print("    Angle: ");  Serial.println(ave);                //printing the value of the angle
  if (millis() >= var * period){                                    //checking if its time to restart the cycle
    var += 1;}                                                      //restarting the cycle
  

  for(int i = 0; i < 16; i++) {                         //one run for each light
    if (flashing == true && i == flash-2){}             //keeping edge light
    else if (flashing == true && i == flash-1){}        //keeping middle light
    else if (flashing == true && i == flash){}          //keeping center light
    else if (flashing == true && i == flash+1){}        //keeping middle light
    else if (flashing == true && i == flash+2){}        //keeping edge light
    else if (flashing == true && i == (flash+2) % 16){} //keeping edge light
    else
    {strip.setPixelColor(i, 0, 255, 0);}                //resetting to green
    }
    strip.show();                                       //showing the green
  if (millis() - lastLEDUpdate1 >= LEDInterval && flashing == true && LED == true)     //checking if it should be printed and what cycle
  {
    if(j > 10){                                     //checking if it should keep decreasing
      strip.setPixelColor(flash-2, j / 2, 0, 0);    //Edge light
      strip.setPixelColor(flash-1, j, 0, 0);        //Middle of middle light
      strip.setPixelColor(flash, j * 5, 0, 0);      //Center light
      strip.setPixelColor(flash+1, j, 0, 0);        //Middle of middle light
      if(flash+2 == 16)                             //checking if it rotated in a circle
      {     
        strip.setPixelColor(0, j / 2, 0, 0);        //Edge light
      }
      strip.setPixelColor(flash+2, j / 2, 0, 0);    //Edge light
      strip.show();                                 //Showing these new colors
      j-=4;}                                        //decreasing j
    else{LED = false;}                              //reset and swap
    lastLEDUpdate1 = millis();                      //checking if it rotated in a circle
  }
  else if (millis() - lastLEDUpdate2 >= LEDInterval2 && flashing == true && LED == false)         //checking if it should be printed and what cycle
  {                                                 //Brightening for loop
    if(j < 50){                                     //checking if it should keep increasing
      strip.setPixelColor(flash-2, j / 2, 0, 0);    //Edge light
      strip.setPixelColor(flash-1, j, 0, 0);        //Middle of middle light
      strip.setPixelColor(flash, j * 5, 0, 0);      //Center light
      strip.setPixelColor(flash+1, j, 0, 0);        //Middle of middle light
      if(flash+2 == 16)                             //checking if it rotated in a circle
      {
        strip.setPixelColor(0, j / 2, 0, 0);        //Edge light
      }
      strip.setPixelColor(flash+2, j / 2, 0, 0);    //Edge light
      strip.show();                                 //Showing these new colors
      j+=4;}                                        //decreasing j
    else{LED = true;}                               //reset and swap
    lastLEDUpdate2 = millis();                      //finding last LED update
  }    
  

  if (filter.getPitch() < filter2.getPitch())                                                                       //checking if up or down
  { if (abs(filter2.getPitch() - filter.getPitch())  >= 33){digitalWrite(Vibra3, HIGH); flash_vibra3 = true;}       //checking if threshold is passed
    else{digitalWrite(Vibra3, LOW); flash_vibra3 = false;}}                                                         //toggling on or off the third vibrator based on pitch
  else
  { if (abs(filter2.getPitch() - filter.getPitch()) >= 40){digitalWrite(Vibra4, HIGH); flash_vibra4 = true;}        //checking if threshold is passed
    else{digitalWrite(Vibra4, LOW); flash_vibra4 = false;}}                                                         //toggling on or off the second vibrator based on yaw


  if (filter.getYaw() < filter2.getYaw())                                                                           //checking if left or right
  { if (abs(abs(filter2.getYaw() - filter.getYaw()) - 10) >= 10){digitalWrite(Vibra2, HIGH); flash_vibra1 = true;}  //checking if threshold is passed
    else{digitalWrite(Vibra2, LOW); flash_vibra1 = false;}}                                                         //toggling on or off the first vibrator based on yaw
  else
  { if (abs(abs(filter2.getYaw() - filter.getYaw()) -10) >= 30){digitalWrite(Vibra1, HIGH); flash_vibra2 = true;}   //checking if threshold is passed
    else{digitalWrite(Vibra1, LOW); flash_vibra2 = false;}}                                                         //toggling on or off the second vibrator based on yaw


  if (flash_vibra4) { flash = 6; flashing = true;}                                        //setting it to fourth LED order
  else if (flash_vibra3) { flash = 14; flashing = true;}                                  //setting it to third LED order
  else if (flash_vibra2) { flash = 10; flashing = true;}                                  //setting it to second LED order
  else if (flash_vibra1) {flash = 2; flashing = true;}                                    //setting it to first LED order
  else { flashing = false;}                                                               //setting it off
}
