from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import socket
import threading
import time

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sockets
sensor_socket = None
command_socket = None

current_ip = None
current_port = None  # command port from UI

current_velocity = 1.0
current_turn = 1.0
latest_distance = "D1:999cm"

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
        command_socket.sendall(b"parallel_button\n")
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

@app.get("/history")
def get_history():
    global command_socket
    if not command_socket:
        return {"error": "Robot not connected"}

    command_socket.sendall(b"get_history\n")

    buffer = b""
    while b"END_OF_HISTORY" not in buffer:
        chunk = command_socket.recv(4096)
        if not chunk:
            break
        buffer += chunk

    data = buffer.replace(b"END_OF_HISTORY", b"").strip()

    # CLEAN HERE
    text = data.decode("utf-8").replace("\r", "")
    commands = text.split("\n")

    return {"commands": commands}


