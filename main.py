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
<<<<<<< HEAD
tcp_socket = None
current_ip= None
current_port = None
=======
#tcp_socket = None
#current_ip= None
#current_port = None
>>>>>>> 085cae1adad66b63c1ea0a40e0fd8bbed1316178
# This is a global variable that will store 
# the current velocity of the robot.
current_velocity = 1.0

#Endpoints

<<<<<<< HEAD
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
=======
@app.get("/Connect")
def connect(ip:str, port:int):
    #open the serial connection here using the provided IP and port
    #global tcp_socket, current_ip, current_port
    #current_ip = ip
    #current_port = port
    #try:
    #   tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #   tcp_socket.connect((ip, port))
    return {"message": f"Connected to {ip}:{port}"}
    #except Exception as e:
    #   return {"message": f"Failed to connect:{e}"}
>>>>>>> 085cae1adad66b63c1ea0a40e0fd8bbed1316178


@app.get("/velocity")
def velocity(v: float):
    global current_velocity
    current_velocity = v
    return {"message": f"Velocity set to {current_velocity}"}


<<<<<<< HEAD
@app.get("/stop")
def stop():
    global tcp_socket
    tcp_socket.sendall(b"stop_button\n") or stop
=======
@app.get("/Stop")
def Stop():
    #global tcp_socket
    #tcp_socket.sendall(b"stop\n")
>>>>>>> 085cae1adad66b63c1ea0a40e0fd8bbed1316178
    return{"message": "Robot Stopped"}


@app.get("/quit")
def quit():
<<<<<<< HEAD
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

@app.get("/left")
def left():
    global tcp_socket, current_velocity
    try:
        cmd=f"V -{current_velocity:.2f} {current_velocity:.2f}\n"
        tcp_socket.sendall(cmd.encode())
        return{"message": f"Moving left with velocity {current_velocity}"}
    except Exception as e:
        return {"error": str(e)}

@app.get("/right")
def right():
    global tcp_socket, current_velocity
    try:
        cmd=f"V {current_velocity:.2f} -{current_velocity:.2f}\n"
        tcp_socket.sendall(cmd.encode())
        return{"message": f"Moving right with velocity {current_velocity}"}
    except Exception as e:
        return {"error": str(e)}



=======
    #global tcp_socket
    #tcp_socket.sendall(b"quit\n")
    return {"message": "Quit command sent"}


# @app.get("/forward")
# def forward():
#     #global tcp_socket, current_velocity
#     #cmd=f"V {current_velocity:.2f} {current_velocity:.2f}\n"
#     #tcp_socket.sendall(cmd.encode())
#     return{"message": "This is the forward endpoint."}
>>>>>>> 085cae1adad66b63c1ea0a40e0fd8bbed1316178





