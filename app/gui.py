import tkinter as tk
import threading
import time
import serial

PORT = '/dev/cu.usbserial-2120'
BAUD = 115200

ser = serial.Serial(PORT, BAUD, timeout=1)
time.sleep(2)


def send(cmd: str):
    ser.write((cmd + '\n').encode('utf-8'))


class BedAlarmApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Bed Alarm")

        self.baseline = 0.0
        self.threshold = 20000
        self.state = "IDLE"
        self.alarm_start = None
        self.lockout_start = None
        self.ALARM_BLOCK = 30.0
        self.LOCKOUT_TIME = 180.0
        self.enabled = True

        self.status_label = tk.Label(root, text="Status: starting...")
        self.status_label.pack(padx=10, pady=5)

        self.weight_label = tk.Label(root, text="Weight: ?")
        self.weight_label.pack(padx=10, pady=5)

        self.toggle_btn = tk.Button(
            root, text="Disable Alarm", command=self.toggle_alarm
        )
        self.toggle_btn.pack(padx=10, pady=5)

        self.root.after(100, self.loop)

    def toggle_alarm(self):
        self.enabled = not self.enabled
        if not self.enabled:
            send("BUZZER_OFF")
            send("LED_ON")
            self.state = "IDLE"
            self.status_label.config(text="Status: DISABLED")
            self.toggle_btn.config(text="Enable Alarm")
        else:
            self.status_label.config(text="Status: IDLE")
            self.toggle_btn.config(text="Disable Alarm")

    def loop(self):
        try:
            line = ser.readline().decode(errors='ignore').strip()
            if line.startswith("W:"):
                value = float(line[2:])
                if self.baseline == 0:
                    # quick baseline on first good reading
                    self.baseline = value
                delta = value - self.baseline
                on_plank = delta > self.threshold
                now = time.time()

                if not self.enabled:
                    send("BUZZER_OFF")
                    send("LED_ON")
                    self.state = "IDLE"
                else:
                    if self.state == "IDLE":
                        send("LED_ON")
                        send("BUZZER_OFF")
                        if on_plank:
                            self.state = "ALARM_RUNNING"
                            self.alarm_start = now
                            send("LED_OFF")
                            send("BUZZER_ON")

                    elif self.state == "ALARM_RUNNING":
                        send("LED_OFF")
                        if not on_plank:
                            send("BUZZER_OFF")
                            self.state = "LOCKOUT"
                            self.lockout_start = now
                        elif now - self.alarm_start >= self.ALARM_BLOCK:
                            self.alarm_start = now

                    elif self.state == "LOCKOUT":
                        send("BUZZER_OFF")
                        send("LED_OFF")
                        elapsed = now - self.lockout_start
                        if elapsed >= self.LOCKOUT_TIME:
                            if not on_plank:
                                self.state = "IDLE"
                            else:
                                self.state = "ALARM_RUNNING"
                                self.alarm_start = now
                                send("BUZZER_ON")
                        else:
                            if on_plank:
                                self.state = "ALARM_RUNNING"
                                self.alarm_start = now
                                send("BUZZER_ON")

                self.weight_label.config(
                    text=f"Weight: {value:.0f} (Δ {delta:.0f})"
                )
                self.status_label.config(text=f"Status: {self.state}")

        except Exception:
            pass

        self.root.after(50, self.loop)


def main():
    root = tk.Tk()
    app = BedAlarmApp(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (send("BUZZER_OFF"), send("LED_OFF"), ser.close(), root.destroy()))
    root.mainloop()


if __name__ == "__main__":
    main()
