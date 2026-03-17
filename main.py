from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import socket
import threading
import time

app = FastAPI()

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

                if decoded.startswith("Distance:"):
                    latest_distance = decoded
                    print(f"[Distance] {decoded}")  # print to console for live monitoring
        except Exception as e:
            time.sleep(0.1)


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
    """Gets the latest distance reading."""
    return {"distance": latest_distance}


@app.get("/velocity")
def velocity(v: float):
    """Sets forward/back speed scaling."""
    global current_velocity
    current_velocity = v
    return {"message": f"Velocity set to {current_velocity:.2f}"}


@app.get("/turn")
def turn(w: float):
    """Sets turning rate scaling."""
    global current_turn
    current_turn = w
    return {"message": f"Turn strength set to {current_turn:.2f}"}


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


@app.get("/forward")
def forward():
    """Moves forward."""
    global tcp_socket, current_velocity
    if not tcp_socket:
        return {"message": "Robot not connected"}
    try:
        cmd = f"V {current_velocity:.2f} {current_velocity:.2f}\n"
        tcp_socket.sendall(cmd.encode())
        return {"message": f"Moving forward with velocity {current_velocity:.2f}"}
    except Exception as e:
        return {"error": str(e)}


@app.get("/backward")
def backward():
    """Moves backward."""
    global tcp_socket, current_velocity
    if not tcp_socket:
        return {"message": "Robot not connected"}
    try:
        cmd = f"V -{current_velocity:.2f} -{current_velocity:.2f}\n"
        tcp_socket.sendall(cmd.encode())
        return {"message": f"Moving backward with velocity {current_velocity:.2f}"}
    except Exception as e:
        return {"error": str(e)}


@app.get("/left")
def left():
    """Turns left."""
    global tcp_socket, current_velocity, current_turn
    
    try:
        left_speed = current_velocity - current_turn
        right_speed = current_velocity + current_turn
        cmd = f"V {left_speed:.2f} {right_speed:.2f}\n"
        tcp_socket.sendall(cmd.encode())
        return {"message": f"Turning left at velocity {current_velocity:.2f}, turn {current_turn:.2f}"}
    except Exception as e:
        return {"error": str(e)}


@app.get("/right")
def right():
    """Turns right."""
    global tcp_socket, current_velocity, current_turn
    if not tcp_socket:
        return {"message": "Robot not connected"}
    try:
        left_speed = current_velocity + current_turn
        right_speed = current_velocity - current_turn
        cmd = f"V {left_speed:.2f} {right_speed:.2f}\n"
        tcp_socket.sendall(cmd.encode())
        return {"message": f"Turning right at velocity {current_velocity:.2f}, turn {current_turn:.2f}"}
    except Exception as e:
        return {"error": str(e)}


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
