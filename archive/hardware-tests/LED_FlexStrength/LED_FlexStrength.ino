int pin = 34;  
void setup() {
  Serial.begin(115200);
  analogSetPinAttenuation(pin, ADC_11db);
  pinMode(35,OUTPUT);
  pinMode(32,OUTPUT);
  pinMode(33,OUTPUT);
  pinMode(25,OUTPUT);
  pinMode(26,OUTPUT);
}

void loop() {
  int num = analogRead(pin);
  Serial.print("Num: "); 
  Serial.println(num);
  delay(400);
  if (num < 160)
  {
    digitalWrite(35,HIGH);
    digitalWrite(32,HIGH);
    digitalWrite(33,HIGH);
    digitalWrite(25,HIGH);
    digitalWrite(26,HIGH);
  }
  else if (num < 180)
  {
    digitalWrite(35,HIGH);
    digitalWrite(32,HIGH);
    digitalWrite(33,HIGH);
    digitalWrite(25,HIGH);
    digitalWrite(26,LOW);
  }
  else if (num < 200)
  {
    digitalWrite(35,HIGH);
    digitalWrite(32,HIGH);
    digitalWrite(33,HIGH);
    digitalWrite(25,LOW);
    digitalWrite(26,LOW);
  }
  else if (num < 300)
  {
    digitalWrite(35,HIGH);
    digitalWrite(32,HIGH);
    digitalWrite(33,LOW);
    digitalWrite(25,LOW);
    digitalWrite(26,LOW);
  }
  else if (num >= 301)
  {
    digitalWrite(35,HIGH);
    digitalWrite(32,LOW);
    digitalWrite(33,LOW);
    digitalWrite(25,LOW);
    digitalWrite(26,LOW);
  }
}