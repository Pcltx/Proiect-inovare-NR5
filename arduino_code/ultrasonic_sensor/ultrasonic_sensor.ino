/*
  ESP32-S3 - US-100 Ultrasonic Sensor (Trigger/Echo Mode)
  Note: Keep the jumper ON at the back of the US-100.
*/

// Updated Pins for ESP32-S3
const int trigPin = 1;  
const int echoPin = 2;  
const int ledPin  = 38; // Most ESP32-S3 DevBoards use GPIO 38 or 48 for the system LED

int previousDistance = 0;
const int changeThreshold = 5; 

void setup() {
  // S3 boards need a delay to initialize USB Serial
  Serial.begin(115200);
  while (!Serial) {
    delay(10);
  }

  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT); 
  pinMode(ledPin, OUTPUT);
  
  digitalWrite(ledPin, LOW);
  Serial.println("US-100 Initialized on ESP32-S3...");
}

void loop() {
  // Clear the trigPin
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  
  // Trigger the sensor with a 10us pulse
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  // Read the echoPin (returns travel time in microseconds)
  // US-100 works perfectly at 3.3V, so no voltage divider is needed
  long duration = pulseIn(echoPin, HIGH, 30000); 

  // Calculate distance: (time * speed of sound) / 2
  int distance = duration * 0.0343 / 2;

  // Filter out 0 (timeout) or out of range readings
  if (distance > 2 && distance < 450) {
    
    // Only print if there is a significant change to avoid Serial spam
    if (abs(distance - previousDistance) >= changeThreshold) {
      Serial.print("Distance changed: ");
      Serial.print(distance);
      Serial.println(" cm");

      // Visual feedback
      digitalWrite(ledPin, HIGH);
      delay(50);
      digitalWrite(ledPin, LOW);
      
      previousDistance = distance;
    }
  }

  delay(60); // Small delay between pings
}