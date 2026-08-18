import time
import datetime
import serial
import tkinter as tk

# ---------- CONFIGURE THIS ----------
PORT = '/dev/cu.usbserial-2120'   # <-- your Arduino Uno port
BAUD = 115200
THRESHOLD = 20000                 # adjust after seeing readings
ALARM_BLOCK = 30.0                # 30 seconds alarm chunk
LOCKOUT_TIME = 180.0              # 3 minutes lockout
# -----------------------------------


class BedAlarmApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Bed Alarm")

        # Serial connection to Arduino
        self.ser = serial.Serial(PORT, BAUD, timeout=1)
        time.sleep(2)  # wait for Uno reset

        # Logic variables
        self.baseline = 0.0
        self.threshold = THRESHOLD
        self.state = "IDLE"
        self.alarm_start = None
        self.lockout_start = None
        self.enabled = True

        # Alarm time (24h)
        self.alarm_hour = tk.StringVar(value="07")
        self.alarm_min = tk.StringVar(value="00")
        self.alarm_set = False

        # ---------- GUI WIDGETS ----------

        # Alarm time input
        time_frame = tk.Frame(root)
        time_frame.pack(padx=10, pady=5)

        tk.Label(time_frame, text="Alarm time (HH:MM):").pack(side=tk.LEFT)

        tk.Entry(time_frame, width=3, textvariable=self.alarm_hour).pack(side=tk.LEFT)
        tk.Label(time_frame, text=":").pack(side=tk.LEFT)
        tk.Entry(time_frame, width=3, textvariable=self.alarm_min).pack(side=tk.LEFT)

        self.set_btn = tk.Button(
            time_frame, text="Set Alarm", command=self.set_alarm_time
        )
        self.set_btn.pack(side=tk.LEFT, padx=5)

        self.alarm_info = tk.Label(root, text="Alarm not set")
        self.alarm_info.pack(padx=10, pady=2)

        # Status + weight
        self.status_label = tk.Label(root, text="Status: starting...")
        self.status_label.pack(padx=10, pady=5)

        self.weight_label = tk.Label(root, text="Weight: ?")
        self.weight_label.pack(padx=10, pady=5)

        # Enable/disable alarm
        self.toggle_btn = tk.Button(
            root, text="Disable Alarm", command=self.toggle_alarm
        )
        self.toggle_btn.pack(padx=10, pady=5)

        # Start periodic loop
        self.root.after(100, self.loop)

    # ---------- SERIAL SEND ----------

    def send(self, cmd: str):
        """Send a command string to Arduino, e.g. BUZZER_ON."""
        try:
            self.ser.write((cmd + '\n').encode('utf-8'))
        except Exception:
            pass

    # ---------- ALARM TIME ----------

    def set_alarm_time(self):
        """Read hour/minute from GUI and mark alarm as set."""
        try:
            h = int(self.alarm_hour.get())
            m = int(self.alarm_min.get())
            if not (0 <= h <= 23 and 0 <= m <= 59):
                raise ValueError
        except ValueError:
            self.alarm_set = False
            self.alarm_info.config(text="Invalid time (00–23 : 00–59)")
            return

        self.alarm_set = True
        self.alarm_info.config(text=f"Alarm set for {h:02d}:{m:02d}")

    # ---------- ENABLE / DISABLE ----------

    def toggle_alarm(self):
        self.enabled = not self.enabled
        if not self.enabled:
            self.send("BUZZER_OFF")
            self.send("LED_ON")
            self.state = "IDLE"
            self.status_label.config(text="Status: DISABLED")
            self.toggle_btn.config(text="Enable Alarm")
        else:
            self.status_label.config(text="Status: IDLE")
            self.toggle_btn.config(text="Disable Alarm")

    # ---------- CORE STATE MACHINE ----------

    def update_logic(self, value: float, now: float):
        """30 s + 3 min logic, assumes alarm is active and enabled."""
        if self.baseline == 0.0:
            self.baseline = value

        delta = value - self.baseline
        on_plank = delta > self.threshold

        if self.state == "IDLE":
            buzzer_on = False
            led_on = True
            if on_plank:
                self.state = "ALARM_RUNNING"
                self.alarm_start = now
                buzzer_on = True
                led_on = False
            return self.state, buzzer_on, led_on, delta

        elif self.state == "ALARM_RUNNING":
            buzzer_on = True
            led_on = False
            if not on_plank:
                self.state = "LOCKOUT"
                self.lockout_start = now
                buzzer_on = False
            elif now - self.alarm_start >= ALARM_BLOCK:
                # 30 s passed, start another block
                self.alarm_start = now
            return self.state, buzzer_on, led_on, delta

        elif self.state == "LOCKOUT":
            buzzer_on = False
            led_on = False
            elapsed = now - self.lockout_start
            if elapsed >= LOCKOUT_TIME:
                if not on_plank:
                    self.state = "IDLE"
                    led_on = True
                else:
                    self.state = "ALARM_RUNNING"
                    self.alarm_start = now
                    buzzer_on = True
            else:
                if on_plank:
                    self.state = "ALARM_RUNNING"
                    self.alarm_start = now
                    buzzer_on = True
            return self.state, buzzer_on, led_on, delta

    # ---------- MAIN LOOP ----------

    def loop(self):
        try:
            line = self.ser.readline().decode(errors='ignore').strip()
            if line.startswith("W:"):
                value = float(line[2:])
                now = time.time()

                # Alarm time check
                alarm_active = False
                if self.alarm_set:
                    current = datetime.datetime.now().strftime("%H:%M")
                    target = f"{int(self.alarm_hour.get()):02d}:{int(self.alarm_min.get()):02d}"
                    if current >= target:
                        alarm_active = True

                # Before alarm time (or alarm disabled): just idle
                if not alarm_active or not self.enabled:
                    self.state = "IDLE"
                    self.send("BUZZER_OFF")
                    self.send("LED_ON")
                    if self.baseline == 0.0:
                        self.baseline = value
                    delta = value - self.baseline
                    self.weight_label.config(
                        text=f"Weight: {value:.0f} (Δ {delta:.0f})"
                    )
                    if not self.enabled:
                        self.status_label.config(text="Status: DISABLED")
                    else:
                        self.status_label.config(text="Status: WAITING FOR ALARM")
                    self.root.after(50, self.loop)
                    return

                # Alarm time reached and enabled -> run bed logic
                state, buzzer_on, led_on, delta = self.update_logic(value, now)

                # Send commands
                self.send("BUZZER_ON" if buzzer_on else "BUZZER_OFF")
                self.send("LED_ON" if led_on else "LED_OFF")

                # Update GUI
                self.weight_label.config(
                    text=f"Weight: {value:.0f} (Δ {delta:.0f})"
                )
                self.status_label.config(text=f"Status: {state}")

        except Exception:
            # keep GUI alive
            pass

        self.root.after(50, self.loop)

    # ---------- CLEANUP ----------

    def close(self):
        try:
            self.send("BUZZER_OFF")
            self.send("LED_OFF")
        except Exception:
            pass
        try:
            self.ser.close()
        except Exception:
            pass
        self.root.destroy()


def main():
    root = tk.Tk()
    app = BedAlarmApp(root)
    root.protocol("WM_DELETE_WINDOW", app.close)
    root.mainloop()


if __name__ == "__main__":
    main()
