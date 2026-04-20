from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import socket
import threading
import time
#import paramiko        #for arm connection through raspberry pi
import serial          #for connection through USB[use COM##]

import math

app = FastAPI()

# -------------------------------------------------------
#  FILES ALLOWED 
# -------------------------------------------------------
ALLOWED_FILES = ["testcon.json", "motion1.py", "motion2.py", "drag_teach.json"]     #This files will be changed in the future

# -------------------------------------------------------
#  CORS CONFIGURATION
# -------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------
#  GLOBAL VARIABLES
# -------------------------------------------------------
sensor_socket = None
command_socket = None

current_ip = None
current_port = None  # command port from UI

current_velocity = 1.0
current_turn = 1.0
latest_distance = "D1:999cm"


# Arm Info
ARM_IP = "192.168.4.1"       # CHECK IP ADDRESS OF ARM || RASPBERRY PI IP
ARM_USER = "pi"
ARM_PASS = "pi"



# -------------------------------------------------------
#  ARM CONNECTION // The one commented needs to be tested 
# -------------------------------------------------------
#def run_arm_logic(filename: str):
#    try: 
#        client = paramiko.SSHClient()
#        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#        client.connect(ARM_IP, port="COM14", username=ARM_USER, password=ARM_PASS)
#        if filename.endswith(".py"):
#            command = f"python3 {filename}"
#        elif filename.endswith(".json"):
#            """CHECK IF THE main.py EXISTS IN THE PI TO PROCESS THE JSON"""
#            command = f"python3 main.py {filename}"
#        else:
#            return {"error": "Unsupported file format"}
#        
#        stdin, stdout, stderr = client.exec_command(command)
#        output = stdout.read().decode('utf-8')
#        error = stderr.read().decode('utf-8')

#        client.close()
#        return {"output": output, "error": error}
#    except Exception as e:
#        return {"error": str(e)}


def run_arm_logic(filename: str):
    SERIAL_PORT = "COM14"  
    BAUD_RATE = 115200      
    
    try:
        with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2) as ser:
            if filename.endswith(".json"):
                with open(f"./armcontroller/waveshare_roarm_sdk-main/waveshare_roarm_sdk-main/demo/{filename}", "r") as f:
                    command = f.read()
                
                ser.write(command.encode('utf-8'))
                
                response = ser.readline().decode('utf-8')
                return {"output": response, "error": ""}
            
            else:
                return {"error": "For now we only allow documents .json through USB"}
                
    except Exception as e:
        return {"error": f"Serial connection Error: {str(e)}"}

# -------------------------------------------------------
#  BACKGROUND LISTENER (Distance updates)
# -------------------------------------------------------
def listen_to_sensors():
    global sensor_socket, latest_distance
    buffer = b""   
    while True:
        try:
            if sensor_socket is None:
                time.sleep(0.1)
                continue

            data = sensor_socket.recv(1024)
            if not data:
                time.sleep(0.1)
                continue

            buffer += data
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                decoded = line.decode("utf-8", errors="ignore").strip()
                if decoded.startswith("D1:"):
                    latest_distance = decoded
                    print(f"[Distance] {decoded}")
        except Exception:
            time.sleep(0.1)




# -------------------------------------------------------
#  ARM ENDPOINT
# -------------------------------------------------------

@app.get("/arm/execute/{name}")
async def execute_arm_command(name: str):
    if name not in ALLOWED_FILES:
        raise HTTPException(status_code=400, detail="UNAUTHORIZE FILE")
    
    result = run_arm_logic(name)

    if "error" in result and result["error"]:
        return {"status": "error", "details": result["error"]}
    
    return {"status": "Success", "file": name, "output": result["output"]}

# -------------------------------------------------------
#  ENDPOINTS
# -------------------------------------------------------

@app.get("/connect")
def connect(ip: str, port: int):
    """Connects to Raspberry Pi TCP servers (command + sensor)."""
    global sensor_socket, command_socket, current_ip, current_port

    current_ip = ip
    current_port = port

    # Close old sockets if any
    try:
        if command_socket:
            command_socket.close()
    except:
        pass
    try:
        if sensor_socket:
            sensor_socket.close()
    except:
        pass

    try:
        # Command socket (UI port, e.g. 8765)
        cmd_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cmd_sock.connect((ip, port))

        # Sensor socket (port + 1, e.g. 8766)
        sens_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sens_sock.connect((ip, port + 1))

        command_socket = cmd_sock
        sensor_socket = sens_sock

        threading.Thread(target=listen_to_sensors, daemon=True).start()

        return {"message": f"Connected to {ip}:{port} (cmd) and {ip}:{port+1} (sensor)"}
    except Exception as e:
        command_socket = None
        sensor_socket = None
        return {"message": f"Failed to connect: {e}"}


@app.get("/distance")
def get_distance():
    try:
        # Expected format: "D1:10cm D2:15cm D3:20cm"
        # If your sensor only sends D1, we provide defaults for the others.
        parts = latest_distance.split()
        
        d1 = 0.0
        d2 = 0.0
        d3 = 0.0

        for p in parts:
            if "D1:" in p:
                d1 = float(p.split(":")[1].replace("cm", "").strip())
            elif "D2:" in p:
                d2 = float(p.split(":")[1].replace("cm", "").strip())
            elif "D3:" in p:
                d3 = float(p.split(":")[1].replace("cm", "").strip())

        return {"d1": d1, "d2": d2, "d3": d3}
    except Exception as e:
        print(f"Parsing error: {e}")
        return {"d1": 0.0, "d2": 0.0, "d3": 0.0}
    

@app.get("/velocity")
def velocity(v: float):
    global current_velocity
    current_velocity = v
    return {"message": f"Velocity set to {current_velocity:.2f}"}

@app.get("/stop")
def stop():
    global command_socket
    if not command_socket:
        return {"message": "Robot not connected"}
    try:
        command_socket.sendall(b"stop_button\n")
        return {"message": "Robot Stopped"}
    except Exception as e:
        return {"message": f"Failed to stop: {e}"}

@app.get("/quit")
def quit():
    global command_socket, sensor_socket
    try:
        if command_socket:
            command_socket.sendall(b"quit\n")
            command_socket.close()
            command_socket = None
        if sensor_socket:
            sensor_socket.close()
            sensor_socket = None
        return {"message": "Connection closed and quit command sent"}
    except Exception as e:
        return {"message": f"Failed to close connection: {e}"}

@app.get("/parallel_button")
def parallel():
    global command_socket
    if not command_socket:
        return {"message": "Parallel Parking Error"}
    try:
        command_socket.sendall(b"parallel_button\n") # This sends the string to the Pi
        return {"message": "Starting autonomous parking"}
    except Exception as e:
        return {"message": f"Failed to start parallel: {e}"}

@app.get("/auto_on")
def auto_on():
    global command_socket
    if not command_socket:
        return {"message": "Robot not connected"}
    try:
        command_socket.sendall(b"auto on\n")
        return {"message": "Auto mode ON"}
    except Exception as e:
        return {"message": f"Failed to enable auto: {e}"}

@app.get("/auto_off")
def auto_off():
    global command_socket
    if not command_socket:
        return {"message": "Robot not connected"}
    try:
        command_socket.sendall(b"auto off\n")
        return {"message": "Auto mode OFF"}
    except Exception as e:
        return {"message": f"Failed to disable auto: {e}"}

@app.get("/velocity_drive")
def velocity_drive(l: float, r: float):
    global command_socket
    if not command_socket:
        return {"message": "Robot not connected"}
    try:
        cmd = f"V {l:.3f} {r:.3f}\n"
        command_socket.sendall(cmd.encode())
        return {"message": cmd.strip()}
    except Exception as e:
        return {"error": str(e)}
    


# Initialize turtle but don't start the loop yet
def init_turtle():
    try:
        t = turtle.Turtle()
        t.speed(0)
        t.hideturtle() # Faster drawing
        return t
    except:
        return None

t = None # Global turtle instance

def translate_command(cmd: str, turtle_instance):
    if not turtle_instance: return
    parts = cmd.strip().split()
    if len(parts) != 3 or parts[0] != "V":
        return

    try:
        left = float(parts[1])
        right = float(parts[2])

        # Differential drive math
        forward = (left + right) / 2
        # Calculate rotation: if right > left, turn left (positive angle)
        turn = (right - left) * 45  # Adjusted sensitivity

        turtle_instance.forward(forward * 20) # Scaling for visibility
        turtle_instance.left(turn) 
    except ValueError:
        pass



@app.get("/history")
def get_history():
    global command_socket
    if not command_socket:
        return {"error": "Robot not connected"}

    try:
        command_socket.sendall(b"get_history\n")
        
        buffer = b""
        # Set a small timeout so we don't hang if END_OF_HISTORY is missed
        command_socket.settimeout(2.0) 
        while b"END_OF_HISTORY" not in buffer:
            chunk = command_socket.recv(4096)
            if not chunk: break
            buffer += chunk
        
        data = buffer.replace(b"END_OF_HISTORY", b"").strip()
        text = data.decode("utf-8").replace("\r", "")
        commands = [c for c in text.split("\n") if c.strip()] # Filter empty lines
        
        return {"commands": commands}
    except Exception as e:
        return {"error": str(e)}
    finally:
        command_socket.settimeout(None)