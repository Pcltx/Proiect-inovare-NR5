
 /* 
Pin
VCC=5V
GND=GND
Trig=Pin 9
Echo=Pin 10
 */

const int trigPin = 9;
const int echoPin = 10;

void setup() {
  Serial.begin(9600); 
  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);
}

void loop() {

  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  

  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  
 
  long duration = pulseIn(echoPin, HIGH);
  
  int distance = duration * 0.0343 / 2;
  

  if (distance > 0 && distance < 400) {
    Serial.println(distance);
  } else {
 
  }
  delay(50); 
}
