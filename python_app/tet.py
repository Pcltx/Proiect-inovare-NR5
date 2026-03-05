from gpiozero import DistanceSensor
from time import sleep

# Define pins using BCM (GPIO) numbers
# Physical 16 = GPIO 23
# Physical 18 = GPIO 24
sensor = DistanceSensor(echo=24, trigger=23)

print("US-100 initialized on Pins 16 & 18 (Trigger/Echo Mode)")

try:
    while True:
        # Distance is returned in meters, we multiply by 100 for cm
        distance_cm = sensor.distance * 100
        
        # The US-100 is accurate up to 450cm
        if distance_cm < 450:
            print(f"Distance: {distance_cm:.2f} cm")
        else:
            print("Out of range")
            
        sleep(0.5)

except KeyboardInterrupt:
    print("\nMeasurement stopped.")