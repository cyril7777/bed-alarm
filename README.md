# bed-alarm
An IoT hardware-software integration that makes sure the user has gotten off the bed after their alarm has rung using Arduino sensor bridges and Python based alarms.

## Tech Stack
* **Hardware and Firmware:** Arduino Uno, C++, Load cell, Piezo Buzzer, Status LEDs
* **Software and Backend:** Python3, Tkinter GUI, PySerial

## Features
* **Real-Time Serial Telemetry:** Streams continuous analog weight sensor readings over serial communication (`115200` baud) with automatic zero-baseline calibration.
* **Smart Alarm Scheduling:** Tkinter-based desktop interface for configuring 24-hour target alarms and manually enabling/disabling monitoring.
* **30-Second / 3-Minute Lockout FSM:** 
  * Triggers hardware actuators (buzzer & status LEDs) upon target time and weight threshold detection.
  * Enforces a 3-minute (180s) lockout period away from the bed to prevent immediate back-to-bed relapse.
* **Graceful Hardware Cleanup:** Automatically resets all hardware pins (`BUZZER_OFF`, `LED_OFF`) and terminates the serial port cleanly on application shutdown.
