// Template for the config.h that AllTogetherNow.ino includes.
// The real config.h holds a WiFi password and an Adafruit IO key, so it is
// not in this repository (see .gitignore). This file is the standard Adafruit IO
// WiFi template with placeholders; copy it to config.h and fill in your own values.

#define IO_USERNAME  "your_adafruit_io_username"
#define IO_KEY       "your_adafruit_io_key"

#define WIFI_SSID    "your_wifi_name"
#define WIFI_PASS    "your_wifi_password"

#include "AdafruitIO_WiFi.h"
AdafruitIO_WiFi io(IO_USERNAME, IO_KEY, WIFI_SSID, WIFI_PASS);
