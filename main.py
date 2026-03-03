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
#tcp_socket = None
#current_ip= None
#current_port = None
# This is a global variable that will store 
# the current velocity of the robot.
current_velocity = 1.0

#Endpoints

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


@app.get("/velocity")
def velocity(v: float):
    global current_velocity
    current_velocity = v
    return {"message": f"Velocity set to {current_velocity}"}


@app.get("/Stop")
def Stop():
    #global tcp_socket
    #tcp_socket.sendall(b"stop\n")
    return{"message": "Robot Stopped"}


@app.get("/quit")
def quit():
    #global tcp_socket
    #tcp_socket.sendall(b"quit\n")
    return {"message": "Quit command sent"}


# @app.get("/forward")
# def forward():
#     #global tcp_socket, current_velocity
#     #cmd=f"V {current_velocity:.2f} {current_velocity:.2f}\n"
#     #tcp_socket.sendall(cmd.encode())
#     return{"message": "This is the forward endpoint."}





