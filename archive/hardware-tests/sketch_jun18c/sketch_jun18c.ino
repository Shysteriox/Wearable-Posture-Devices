#include <math.h>
int listb[2000];
int list[20];
int num = 0;
int bias = -14;
void setup() {
  // put your setup code here, to run once:
  Serial.begin(115200);
  for (int i = 100; i < 2000; i++)
  {
    listb[i] = 103.1004*log(0.00326145*i - 0.320527) + 
    -12.20153 * cos(0.0201778 * i + 2.97212) +
    1.61817 * cos(0.0302185 * i - 0.222821) +
    -0.222821 * cos(0.00297744 * i -23.88627) +
    -1.74187 * cos(0.0824802 * i + 2.8118) +
    2.8118 * cos(0.0674563 * i - 4.6551) +
    -317.21621 * cos(0.0425672 * i -23.51092) +
    316.51257 * cos(0.0425325 * i + 1.64691) +
    8.9505 * cos(0.0220089 * i + 1.66444);
  }
}
void loop() {
  delay(50);
  num = listb[analogRead(34)] + bias;
  int ave = 0;
  for (int i = 1; i < 10; i++)
  {
    list[i-1] = list[i];
  }
  list[9] = num;
  for (int i = 0; i < 10; i++)
  {
    ave += list[i];
  }
  ave = ave/10;
  Serial.print("Average: "); 
  Serial.println(ave);
}
