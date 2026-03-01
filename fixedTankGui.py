# Run on remote PC/laptop

#!/usr/bin/env python3d
import socket
import threading
import time
import paramiko             # For Arm connection
import tkinter as tk
from tkinter import ttk

# -------- Pi connection defaults --------
PI_HOST = "172.20.10.4"   # <<<< your Pi IP
PI_PORT = 8765

#PI_HOST_GUI ="" # set up a listener on GUI pc, waiting for the distance message from PI
#PI_PORT_GUI = 8766
# ----------------------------------------

UPDATE_HZ   = 20          # how often we send commands
DEADMAN_MS  = 600         # stop if quiet for this long
MAX_V_MPS   = 3.0         # forward/back speed scale (GUI slider will change)
MAX_W_RAD   = 2.5         # turn rate scale (GUI slider will change)

class TankGUI(tk.Tk):
    def __init__(self):
        super().__init__()  #Initialize Tkinter window
        self.title("Tank WASD Controller") #window title
        self.geometry("640x420")            #window size
        self.running = True  #self.running
        # state
        self.sock = None    #TCP socket connection
        self.keys = set()   #Set of currently pressed keys
        self.v_cmd = 0.0    #Forward and Backward velocity
        self.w_cmd = 0.0    #Turn rate
        self.last_tx_ms = 0 #timestamp of last command sent

        self._build_ui()   #create GUI layout
        self._bind_keys()   #Set up key listeners

        # periodic loop
        self.safe_after(int(1000/UPDATE_HZ), self._tick) #call tick every 50 ms

        #self.button_clean = True

    # ---------------- UI -----------------
    def _build_ui(self):
        pad = 8
        root = ttk.Frame(self, padding=pad)
        root.pack(fill="both", expand=True)

        # connection row
        row = ttk.Frame(root)
        row.pack(fill="x", pady=(0, pad))
        ttk.Label(row, text="Pi IP:").pack(side="left")
        self.ip_entry = ttk.Entry(row, width=16)
        self.ip_entry.insert(0, PI_HOST)
        self.ip_entry.pack(side="left", padx=(4, 12))
        ttk.Label(row, text="Port:").pack(side="left")
        self.port_entry = ttk.Entry(row, width=7)
        self.port_entry.insert(0, str(PI_PORT))
        self.port_entry.pack(side="left", padx=(4, 12))

        self.connect_btn = ttk.Button(row, text="Connect", command=self.connect)
        self.connect_btn.pack(side="left")
        self.status_var = tk.StringVar(value="Disconnected")
        ttk.Label(row, textvariable=self.status_var, foreground="blue").pack(side="left", padx=12)

        # speed sliders
        grp = ttk.LabelFrame(root, text="Speed Limits")
        grp.pack(fill="x", pady=(0, pad))

        self.v_var = tk.DoubleVar(value=MAX_V_MPS)
        self.w_var = tk.DoubleVar(value=MAX_W_RAD)

        ttk.Label(grp, text="Max V (m/s):").pack(anchor="w")
        self.v_scale = ttk.Scale(grp, from_=0.0, to=6.0, orient="horizontal", variable=self.v_var)
        self.v_scale.pack(fill="x", padx=4, pady=(0, 6))

        ttk.Label(grp, text="Max W (rad/s):").pack(anchor="w")
        self.w_scale = ttk.Scale(grp, from_=0.0, to=6.0, orient="horizontal", variable=self.w_var)
        self.w_scale.pack(fill="x", padx=4, pady=(0, 2))

        # controls
        ctr = ttk.LabelFrame(root, text="Controls — hold keys")
        ctr.pack(fill="x", pady=(0, pad))
        
        #sending controls to the serial communication code as "back"
        ttk.Label(ctr, text="W=forward, S=back, A=left, D=right").pack(anchor="w", padx=4)
        b = ttk.Button(ctr, text="STOP", command=self.send_stop)  #Stop printing
        b.pack(side="left", padx=4, pady=4)

        
        self.button_clean = ttk.Button(ctr, text="Clean", command=self.arm_cleaner)
        self.button_clean.pack(side="right", padx=4, pady=4)      # Arm Button "Clean"
        
        # is_feature_enable = True
        
        #ttk.Button(ctr, text="Quit", command=self.destroy).pack(side="right", padx=4, pady=4)
        ttk.Button(ctr, text="Quit", command=self._quit_cleanly).pack(side="right", padx=4, pady=4)

        # Check Auto box
        self.auto_mode = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            ctr,
            text="Auto",
            variable=self.auto_mode,
            command=self._toggle_auto
        ).pack(side="left", padx=10)

        # debug/telemetry
        self.debug_var = tk.StringVar(value="keys: []   v:0.00 w:0.00")
        ttk.Label(root, textvariable=self.debug_var, font=("Consolas", 10)).pack(anchor="w")

        tele_frame = ttk.Frame(root)                                # ----------Modify so we can get the telemetry and sensor signal
        tele_frame.pack(fill="both", expand=True)

        # Arduino telemetry
        arduino_box = ttk.LabelFrame(tele_frame, text="Arduino Telemetry")
        arduino_box.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        self.tele_arduino = tk.Text(arduino_box, height=10, width=40)
        self.tele_arduino.pack(fill="both", expand=True)

        # Distance sensor
        sensor_box = ttk.LabelFrame(tele_frame, text="Distance Sensor")
        sensor_box.pack(side="right", fill="both", expand=True, padx=5, pady=5)
        self.tele_sensor = tk.Text(sensor_box, height=10, width=40)
        self.tele_sensor.pack(fill="both", expand=True)

    # Checkbox
    def _toggle_auto(self):
        if self.auto_mode.get():
            self.send_line("auto on")
            self.status_var.set("Auto mode: ON")
        else:
            self.send_stop()
            self.send_line("auto off")
            self.status_var.set("Auto mode: OFF")


    def _bind_keys(self):
        # capture keys regardless of which widget is focused
        self.bind_all("<KeyPress>", self._on_key_down)
        self.bind_all("<KeyRelease>", self._on_key_up)
        # ensure the window grabs focus shortly after startup / connect
        self.safe_after(200, self.focus_force)

    # ------------- networking -------------
    def connect(self):
        host = self.ip_entry.get().strip()
        port = int(self.port_entry.get().strip())
        self.status_var.set("Connecting...")
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect((host, port))
            s.settimeout(None)
            self.sock = s
            self.status_var.set(f"Connected to {host}:{port}")
            # start RX thread
            threading.Thread(target=self._rx_loop, daemon=True).start()
            # grab focus so keys go to us after clicking
            self.safe_after(50, self.focus_force)
        except Exception as e:
            self.status_var.set(f"Connect failed: {e}")
            self.sock = None

    def _rx_loop(self):
        while self.running:
            try:
                data = self.sock.recv(4096)
                if not data:
                    break

                text = data.decode("utf-8", errors="ignore")
                for line in text.splitlines():
                    if line.startswith("Distance"):
                        self.safe_after(0, lambda l=line: self.tele_sensor.insert("end", l + "\n"))
                        self.safe_after(0, lambda: self.tele_sensor.see("end"))
                    else:
                        self.safe_after(0, lambda l=line: self.tele_arduino.insert("end", l + "\n"))
                        self.safe_after(0, lambda: self.tele_arduino.see("end"))

            except Exception as e:
                self.safe_after(0, lambda: self.status_var.set(f"RX error: {e}"))
                break

        self.sock = None
        if self.running:   #prevent the 
            
            self.safe_after(0, lambda: self.status_var.set("Disconnected"))

    
    # ------------- key handling -----------
    def _on_key_down(self, e):
        k = e.keysym.lower()
        if k in ("w", "a", "s", "d"):
            self.keys.add(k)

    def _on_key_up(self, e):
        k = e.keysym.lower()
        if k in self.keys:
            self.keys.remove(k)

    # ------------- command loop -----------
    def _tick(self):
        # compute v, w from keys held down
        v = 0.0
        w = 0.0
        if "w" in self.keys: v += 1.0
        if "s" in self.keys: v -= 1.0
        if "a" in self.keys: w += 1.0   # +w = turn left
        if "d" in self.keys: w -= 1.0   # -w = turn right

        # scale by sliders
        v *= float(self.v_var.get())
        w *= float(self.w_var.get())

        self.v_cmd, self.w_cmd = v, w
        self.debug_var.set(f"keys:{sorted(self.keys)}   v:{v:.2f}  w:{w:.2f}")


        left = 0.0
        right = 0.0
        



       # If auto mode is ON, skip sending manual drive commands
        if not self.auto_mode.get():
            # convert (v,w) to left/right simple differential speeds
            left  = v + w
            right = v - w
            
       
        # deadman: if no keys & too long since last send, transmit stop once
        now_ms = int(time.time() * 1000)
        if self.sock:
            if (left != 0.0 or right != 0.0):
                self.send_line(f"V {left:.3f} {right:.3f}")
                self.last_tx_ms = now_ms
            else:
                if now_ms - self.last_tx_ms > DEADMAN_MS:
                    if not self.auto_mode.get():
                        self.send_line("stop...")
                    self.last_tx_ms = now_ms

        # schedule next tick exactly once
        self.safe_after(int(1000/UPDATE_HZ), self._tick)




    def safe_after(self, delay, func):
        #if self.winfo_exists():
        try:
                
            self.after(delay, func)  # Correct method to schedule GUI updates
        except RuntimeError:
            print("Skipped GUI update — window is closing.")

    def arm_cleaner(self):              # Arm Clean Function
        #disable the clean button
        self.button_clean["state"]=tk.DISABLED #"disabled"
        #self.button_clean.config(state="DISABLED")
        print("Perform Cleaning Motion")
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try: #PI_HOST
            client.connect('136.183.81.59', port=22, username='pi', password='pi') # need to adjust IP address
            print("ok")
            ssh_stdin, ssh_stdout, ssh_stderr = client.exec_command("source clean_motion") #python3 testclean.py

            #ssh_stdin, ssh_stdout, ssh_stderr = client.exec_command("python3 clean_arm.py") #python3 testclean.py
            output = ssh_stdout.read().decode('utf-8')
            error = ssh_stderr.read().decode('utf-8')
            if error:
                print("--- Command Error ---")
                print(error)        
            if output:
                print("--- Command Output ---")
                print(output)
        except paramiko.AuthenticationException:
            print("Authentication failed, please verify your credentials.")
            exit()
        except paramiko.SSHException as e:
            print(f"Could not establish SSH connection: {e}")
            exit()
        
        #enable the button
        self.button_clean["state"]=tk.NORMAL #"enable" 



        
    def send_line(self, s: str):
        if not s.endswith("\n"):
            s = s + "\n"
        try:
            if self.sock:
                print("TX:", s.strip())  # debug: see what we’re sending
                self.sock.sendall(s.encode("utf-8"))
        except Exception as e:
            self.status_var.set(f"TX error: {e}")

    def send_stop(self):
        self.keys.clear()
        self.send_line("stop")
        time.sleep(0.1)
        
        if self.auto_mode.get():
            self.send_line("auto off")
            time.sleep(0.1)
        #self.v_cmd = self.w_cmd = 0.0
        #self.send_line("Stop")
        try:    
            self.send_line("stop_button")
            time.sleep(0.1)
        except Exception as e:
            self.safe_after(0, lambda: self.status_var.set(f"Stop error: {e}"))
        
        
    def _quit_cleanly(self):
        self.running = False  #  Tell _rx_loop to stop

        try:
            self.send_stop()  # Stop robot safely
            time.sleep(0.1)
        except Exception as e:
            print("Error during quit:", e)

        try:
            self.send_line("Quit")  # Optional: notify Arduino
        except Exception as e:
            print("Error sending Quit:", e)

        try:
            if self.sock:
                self.sock.close()  # Close socket connection
                self.sock = None
        except Exception as e:
            print("Error closing socket:", e)

        self.safe_after(0, lambda: self.status_var.set("Robot stopped. Goodbye!"))
        self.destroy()  # Close the GUI window

if __name__ == "__main__":
    app = TankGUI()
    app.mainloop()

