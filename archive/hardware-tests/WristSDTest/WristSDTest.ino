#include <SPI.h>
#include <SdFat.h>

// Define the Chip Select pin
const uint8_t SD_CS_PIN = 5;

// Create the SdFat object
// We use SdFat32 to specifically target the FAT32 formatting we applied earlier
SdFat32 sd;
File32 testFile;

void setup() {
  Serial.begin(115200);
  delay(3000); // Give the serial monitor time to open
  
  Serial.println("\n\n====================================");
  Serial.println("--- SDFAT LIBRARY HARDWARE TEST ---");
  Serial.println("====================================");

  // Initialize the SPI pins exactly as wired on your wrist device
  SPI.begin(18, 19, 23, SD_CS_PIN); // SCK=18, MISO=19, MOSI=23, CS=5
  pinMode(19, INPUT_PULLUP);        // Pull-up for MISO stability

  Serial.println("Attempting to connect using SdFat (1 MHz)...");
  
  // SdFat allows explicitly specifying the SPI frequency.
  // SD_SCK_MHZ(1) sets it to 1MHz for breadboard stability.
  if (!sd.begin(SD_CS_PIN, SD_SCK_MHZ(1))) {
    Serial.println("\n  ❌ SDFAT INIT FAILED.");
    Serial.println("\n--- HARDWARE ERROR REPORT ---");
    // This is the magic of SdFat: It prints exactly WHY the hardware failed!
    sd.initErrorPrint(&Serial);
    Serial.println("-----------------------------");
    Serial.println("\nIf it says CMD0 or CMD8 timeout, your wires are not communicating.");
    Serial.println("If it says OCR timeout, your card isn't getting enough voltage.");
    return;
  }
  
  Serial.println("  ✅ INIT SUCCESS: SdFat connected to the SD card!");

  // Try to write a file called HELLO.TXT
  Serial.println("\nAttempting to write 'Hello' to HELLO.TXT...");
  
  // O_WRITE | O_CREAT creates the file if it doesn't exist
  if (testFile.open("HELLO.TXT", O_WRITE | O_CREAT | O_AT_END)) {
    testFile.println("Hello from the ESP32 using the SdFat library!");
    testFile.sync(); // Force the save (similar to flush)
    testFile.close(); // Close the file safely
    
    Serial.println("  ✅ WRITE SUCCESS: Wrote to HELLO.TXT");
    Serial.println("\n====================================");
    Serial.println("You can unplug the ESP32 now and check the SD card on your computer!");
  } else {
    Serial.println("  ❌ WRITE FAILED: Connected to card, but could not open file.");
  }
}

void loop() {
  // Do nothing, test only runs once on boot
}
