from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import socket


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#Global variables
tcp_socket = None
current_ip= None
current_port = None
# This is a global variable that will store 
# the current velocity of the robot.
current_velocity = 1.0
current_turn = 1.0

#Endpoints

@app.get("/connect")
def connect(ip:str, port:int):

    #open the serial connection here using the provided IP and port
    global tcp_socket, current_ip, current_port
    current_ip = ip
    current_port = port
    try:
      tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      tcp_socket.connect((ip, port))
      return {"message": f"Connected to {ip}:{port}"}
    except Exception as e:
        return {"message": f"Failed to connect:{e}"}


@app.get("/velocity")
def velocity(v: float):
    global current_velocity
    current_velocity = v
    return {"message": f"Velocity set to {current_velocity}"}


# For turn strength
@app.get("/turn")
def turn(w: float):
    global current_turn
    current_turn = w
    return {"message": f"Strength turn set to {current_turn}"}



@app.get("/stop")
def stop():
    global tcp_socket
    tcp_socket.sendall(b"stop_button\n") or stop
    return{"message": "Robot Stopped"}


@app.get("/quit")
def quit():
    global tcp_socket
    try:
        tcp_socket.sendall(b"quit\n")
        return {"message": "Quit command sent"}
    except Exception as e:
        return {"message" : f"Failed to send quit command: {e}"}


@app.get("/forward")
def forward():
    global tcp_socket, current_velocity
    try:
        cmd=f"V {current_velocity:.2f} {current_velocity:.2f}\n"
        tcp_socket.sendall(cmd.encode()) 
        return{"message": f"Moving forward with velocity {current_velocity}"}
    except Exception as e:
        return {"error": str(e)}

@app.get("/backward")
def backward():
    global tcp_socket, current_velocity
    try:
        cmd=f"V -{current_velocity:.2f} -{current_velocity:.2f}\n"
        tcp_socket.sendall(cmd.encode()) 
        return{"message": f"Moving backward with velocity {current_velocity}"}
    except Exception as e:
        return {"error": str(e)}

#@app.get("/left")
#def left():
#    global tcp_socket, current_velocity
#    try:
#        cmd=f"V -{current_velocity:.2f} {current_velocity:.2f}\n"
#        tcp_socket.sendall(cmd.encode())
#        return{"message": f"Moving left with velocity {current_velocity}"}
#    except Exception as e:
#        return {"error": str(e)}

#@app.get("/right")
#def right():
#    global tcp_socket, current_velocity
#    try:
#        cmd=f"V {current_velocity:.2f} -{current_velocity:.2f}\n"
#        tcp_socket.sendall(cmd.encode())
#        return{"message": f"Moving right with velocity {current_velocity}"}
#    except Exception as e:
#        return {"error": str(e)}

#! Try this by changing the previous !#

#add the global variables of current_velocity and current_speed,
#variables left and right to make a turn smoothly
@app.get("/left")
def left():
    global tcp_socket, current_velocity, current_turn
    try:
        left = current_velocity - current_turn
        right = current_velocity + current_turn
        cmd=f"V {left:.2f} {right:.2f}\n"
        tcp_socket.sendall(cmd.encode())
        return{"message": f"Moving left {current_turn}"}
    except Exception as e:
        return {"error": str(e)}


@app.get("/right")
def right():
    global tcp_socket, current_velocity, current_turn
    try:
        left = current_velocity + current_turn
        right = current_velocity - current_turn
        cmd=f"V {left:.2f} {right:.2f}\n"
        tcp_socket.sendall(cmd.encode())
        return{"message": f"Moving right {current_turn}"}
    except Exception as e:
        return {"error": str(e)}
