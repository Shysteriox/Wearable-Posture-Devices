#include <ESP32Servo.h>

Servo myServo;
int servoPin = 18;
void setup()
{
  myServo.attach(servoPin);
  myServo.write(0);
}

void loop()
{
  
}