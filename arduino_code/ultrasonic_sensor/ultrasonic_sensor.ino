/*
  ESP32-S3-N16R8 - Senzor Ultrasonic HC-SR04
  
  Pinout:
    VCC  = 5V (sau 3.3V dacă senzorul suportă)
    GND  = GND
    Trig = GPIO 4
    Echo = GPIO 5

  Notă: ESP32-S3 are USB nativ (CDC).
        În Arduino IDE, selectează:
        - Board: "ESP32S3 Dev Module"
        - USB CDC On Boot: "Enabled"
*/

const int trigPin = 4;
const int echoPin = 5;

void setup() {
  Serial.begin(115200);  // Viteză mai mare pe ESP32
  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);

  // Așteaptă conexiunea USB serial
  while (!Serial) {
    delay(10);
  }
  delay(500);  // Stabilizare la pornire
}

void loop() {
  // Trimite puls trigger
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  // Citește ecoul
  long duration = pulseIn(echoPin, HIGH, 30000);  // Timeout 30ms (~5m max)

  // Calculează distanța în cm
  int distance = duration * 0.0343 / 2;

  if (distance > 0 && distance < 400) {
    Serial.println(distance);
  }

  delay(50);
}
