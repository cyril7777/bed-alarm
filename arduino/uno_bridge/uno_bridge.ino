#include "HX711.h"

const int LOADCELL_DOUT_PIN = 2;
const int LOADCELL_SCK_PIN  = 3;

const int BUZZER_PIN = 8;
const int LED_PIN    = 9;

HX711 scale;

void setup() {
  Serial.begin(115200);
  scale.begin(LOADCELL_DOUT_PIN, LOADCELL_SCK_PIN);
  delay(500);
  scale.tare();

  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(LED_PIN, OUTPUT);
}

void loop() {
  long reading = scale.get_units(5);
  Serial.print("W:");
  Serial.println(reading);

  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');

    if (cmd == "BUZZER_ON")  digitalWrite(BUZZER_PIN, HIGH);
    if (cmd == "BUZZER_OFF") digitalWrite(BUZZER_PIN, LOW);
    if (cmd == "LED_ON")     digitalWrite(LED_PIN, HIGH);
    if (cmd == "LED_OFF")    digitalWrite(LED_PIN, LOW);
  }

  delay(50);
}
