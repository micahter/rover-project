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

                # Accept new two-sensor format
                if decoded.startswith("D1:"):
                    latest_distance = decoded
                    print(f"[Distance] {decoded}")
                    # print to console for live monitoring
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
    try:
        parts = latest_distance.split()

        d1 = float(parts[0].split(":")[1].replace("cm", "").strip())
        d2 = float(parts[1].split(":")[1].replace("cm", "").strip())

        return {"d1": d1, "d2": d2}

    except Exception as e:
        print("Parsing error:", e)
        return {"d1": 0.0, "d2": 0.0}




 
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

