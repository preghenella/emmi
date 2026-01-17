#! /usr/bin/env python

import serial
import time

# Configuration
port = '/dev/ARDUINO_LM73'  # Change this if your Arduino is on a different port
baud_rate = 9600       # Set the baud rate
output_file = '/tmp/lm73.txt'  # Output file for the last reading

try:
    # Set up serial connection
    with serial.Serial(port, baud_rate, timeout=1) as ser:
#        time.sleep(2)  # Wait for the connection to be established
        
#        print("Reading data from serial port. Press Ctrl+C to stop.")
        
        while True:
#            time.sleep(1)
            if ser.in_waiting > 0:  # Check if data is available to read
                line = ser.readline().decode('utf-8', errors='replace').strip()  # Read a line from the serial port
#                print(f"Received: {line}")  # Print the received line

                # Write the received line to the output file
                with open(output_file, 'w') as f:
                    f.write(f"{line}\n")  # Write the received line to the file

except KeyboardInterrupt:
    print("\nStopped by user.")

except serial.SerialException as e:
    print(f"Error: {e}")

except Exception as e:
    print(f"An unexpected error occurred: {e}")
