from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import socket
import threading
import time
#import paramiko        #for arm connection through raspberry pi
import serial          #for connection through USB[use COM##]

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
tcp_socket = None
current_ip = None
current_port = None
current_velocity = 1.0
current_turn = 1.0
latest_distance = "No data"

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
def listen_to_pi():
    global tcp_socket, latest_distance
    buffer = b""

    while True:
        try:
            if tcp_socket is None:
                time.sleep(0.1)
                continue

            data = tcp_socket.recv(1024)
            if not data:
                time.sleep(0.1)
                continue

            buffer += data
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                decoded = line.decode("utf-8", errors="ignore").strip()

                # Accept new two-sensor format
                if decoded.startswith("D1:"):
                    latest_distance = decoded
                    print(f"[Distance] {decoded}")
                    # print to console for live monitoring
        except Exception as e:
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
    """Connects to Raspberry Pi TCP server."""
    global tcp_socket, current_ip, current_port
    current_ip = ip
    current_port = port
    try:
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.connect((ip, port))

        # Start background listener
        threading.Thread(target=listen_to_pi, daemon=True).start()

        return {"message": f"Connected to {ip}:{port}"}
    except Exception as e:
        tcp_socket = None
        return {"message": f"Failed to connect: {e}"}


@app.get("/distance")
def get_distance():
    try:
        parts = latest_distance.split()

        d1 = float(parts[0].split(":")[1].replace("cm", "").strip())
        d2 = float(parts[1].split(":")[1].replace("cm", "").strip())
        d3 = float(parts[2].split(":")[1].replace("cm", "").strip())

        return {"d1": d1, "d2": d2, "d3": d3}

    except Exception as e:
        print("Parsing error:", e)
        return {"d1": 0.0, "d2": 0.0, "d3": 0.0}


@app.get("/velocity")
def velocity(v: float):
    """Sets forward/back speed scaling."""
    global current_velocity
    current_velocity = v
    return {"message": f"Velocity set to {current_velocity:.2f}"}



@app.get("/stop")
def stop():
    """Stops the robot."""
    global tcp_socket
    if not tcp_socket:
        return {"message": "Robot not connected"}
    try:
        tcp_socket.sendall(b"stop_button\n")
        return {"message": "Robot Stopped"}
    except Exception as e:
        return {"message": f"Failed to stop: {e}"}


@app.get("/quit")
def quit():
    """Quits and closes the socket."""
    global tcp_socket
    try:
        if tcp_socket:
            tcp_socket.sendall(b"quit\n")
            tcp_socket.close()
            tcp_socket = None
            return {"message": "Connection closed and quit command sent"}
        return {"message": "No active connection to close"}
    except Exception as e:
        return {"message": f"Failed to close connection: {e}"}


@app.get("/auto_on")
def auto_on():
    """Turns auto mode on."""
    global tcp_socket
    if not tcp_socket:
        return {"message": "Robot not connected"}
    
    tcp_socket.sendall(b"auto on\n")
    return {"message": "Auto mode ON"}


@app.get("/auto_off")
def auto_off():
    """Turns auto mode off."""
    global tcp_socket
    if not tcp_socket:
        return {"message": "Robot not connected"}
    
    tcp_socket.sendall(b"auto off\n")
    return {"message": "Auto mode OFF"}



@app.get("/velocity_drive")
def velocity_drive(l: float, r: float):
    """Direct velocity control: used for 20 Hz continuous driving."""
    global tcp_socket
    if not tcp_socket:
        return {"message": "Robot not connected"}
    try:
        cmd = f"V {l:.3f} {r:.3f}\n"
        tcp_socket.sendall(cmd.encode())
        return {"message": cmd.strip()}
    except Exception as e:
        return {"error": str(e)}