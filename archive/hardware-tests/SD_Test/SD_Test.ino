#include "FS.h"
#include "SD.h"
#include "SPI.h"

void setup() {
  Serial.begin(115200);
  delay(2000); // Give serial time to open
  
  Serial.println("\n\n====================================");
  Serial.println("--- ESP32 SD CARD DIAGNOSTIC ---");
  Serial.println("====================================");

  // Attempt 1: Explicit VSPI with 1MHz and Pullup
  Serial.println("\n[Test 1] Explicit VSPI (SCK=18, MISO=19, MOSI=23, CS=5) at 1 MHz...");
  SPI.end(); 
  SPI.begin(18, 19, 23, 5);
  pinMode(19, INPUT_PULLUP);
  if(SD.begin(5, SPI, 1000000)){
    Serial.println("  ✅ PASSED!");
    printCardInfo();
    return;
  }
  Serial.println("  ❌ FAILED");

  // Attempt 2: Explicit VSPI at Default 4 MHz
  Serial.println("\n[Test 2] Explicit VSPI at Default 4 MHz...");
  if(SD.begin(5, SPI, 4000000)){
    Serial.println("  ✅ PASSED!");
    printCardInfo();
    return;
  }
  Serial.println("  ❌ FAILED");

  // Attempt 3: Standard Default SPI
  Serial.println("\n[Test 3] Default Arduino SPI Configuration...");
  SPI.end();
  SPI.begin();
  if(SD.begin(5)){
    Serial.println("  ✅ PASSED!");
    printCardInfo();
    return;
  }
  Serial.println("  ❌ FAILED");
  
  // Attempt 4: Testing alternate CS pin ([redacted] labeled 5 but requires 15 or 4)
  Serial.println("\n[Test 4] Testing alternate Chip Select pins (15, 4)...");
  if (SD.begin(15) || SD.begin(4)) {
    Serial.println("  ✅ PASSED on alternate CS pin!");
    printCardInfo();
    return;
  }
  Serial.println("  ❌ FAILED");

  Serial.println("\n====================================");
  Serial.println("         ALL TESTS FAILED           ");
  Serial.println("====================================");
  Serial.println("If all 4 tests fail, the software is NOT the issue.");
  Serial.println("Please double check these physical items:");
  Serial.println("  1. Swap the MISO and MOSI wires (this happens 99% of the time).");
  Serial.println("  2. Try moving the VCC wire from 5V to the 3.3V pin (some modules don't have a 5V regulator).");
  Serial.println("  3. Make sure the MicroSD card is fully clicked/locked into the slot.");
  Serial.println("  4. Swap out the 4 jumper wires for new ones (one might be broken internally).");
}

void printCardInfo() {
  uint8_t cardType = SD.cardType();
  if(cardType == CARD_NONE) {
    Serial.println("  ERROR: Card module found, but no SD card inserted!");
    return;
  }
  Serial.print("  Card Type: ");
  if(cardType == CARD_MMC) Serial.println("MMC");
  else if(cardType == CARD_SD) Serial.println("SDSC");
  else if(cardType == CARD_SDHC) Serial.println("SDHC");
  else Serial.println("UNKNOWN");
  Serial.printf("  Card Size: %llu MB\n", SD.cardSize() / (1024 * 1024));
  Serial.println("\n==> HARDWARE IS WORKING PERFECTLY! <==");
}

void loop() {
  // Do nothing
}
