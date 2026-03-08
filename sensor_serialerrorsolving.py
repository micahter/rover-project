#!/usr/bin/env python3

import socket, threading, sys, time
import serial
import RPi.GPIO as GPIO #controlling GPIo pins

# ---- Ajusta estos valores si es necesario ----
SERIAL_PORT = '/dev/ttyACM0'   # o /dev/ttyUSB0
SERIAL_BAUD = 115200
TCP_HOST    = '172.20.10.4'
TCP_PORT    = 8765
# ---------------------------------------------



TRIG = 23
ECHO = 24

GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

def get_distance():
    GPIO.output(TRIG, False) #ensure TRIG is low
    time.sleep(0.05)

    GPIO.output(TRIG, True)
    time.sleep(0.01)
    GPIO.output(TRIG, False)

    start = time.time() #record start time
    while GPIO.input(ECHO) == 0: #wait for the acho to start
        start = time.time()
    timeout = time.time() + 1  #timeout after 1 second
    while GPIO.input(ECHO) == 1 and time.time() < timeout: #wait for ECHO to end
        end = time.time()

    duration = end - start
    distance = duration * 17150 #convert to cm
    return round(distance, 2)

# Variables globales
safe_distance = 20

#change the number for distance
auto_mode_button = False  # "False" It will be controlled for GUI
current_conn = None       #storesactive TCP connection
conn_Lock = threading.Lock()
#to make sure only one thread at a time touches current_conn
running = True


def auto_mode(ser):
    """Auto Mode: Go forward and backward depending on the sensor"""

    global auto_mode_button, safe_distance

    last_action = None #tracks last movement command

    while running: #while auto_mode is "On"
        try:
            if auto_mode_button:
                dist = get_distance() #calling the get distance function
                print(f"[Auto Mode] Distance: {dist} cm")

                if dist < safe_distance: #obstacle detected
                    if last_action != "right": # Gui is sending the "back" from "controls"
                        #print("Obstacle detected! Distance below safe_distance")
                        #print("[AUTO MODE] Sending -> stop")
                        ser.write(b"stop\n") # sending "Stop"
                        time.sleep(0.01)

                        if not auto_mode_button:
                            continue

                        #print("[AUTO MODE] Sending -> s (back)")
                        cmd= "V -1.00 -1.00"
                        ser.write((cmd + "\n").encode("utf-8")) #sending "back"
                        ser.write((cmd + "\n").encode("utf-8"))
                        time.sleep(2) #wait for 2 seconds to let the robot move backward

                        if not auto_mode_button:
                            continue


                        #print("[AUTO MODE] sending -> turn (after back and stop)")
                        cmd= "V 2.50 -2.50"
                        ser.write((cmd + "\n").encode("utf-8")) #to turn right
                        ser.write((cmd + "\n").encode("utf-8"))
                        time.sleep(3)



                        #print("Backed up safely. Waiting to resume forward...")
                        last_action = "right"
                        time.sleep(0.01)
                        last_action = None

                else:       #If distance > safe_distance
                    #print("Path clear — continuing forward")
                    #print("[AUTO MODE] Sending -> w (forward)")
                    #sending "forward"
                    cmd= "V 1.00 1.00"
                    ser.write((cmd + "\n").encode("utf-8"))
                    #time.sleep(0.5)

            else:
                if last_action != "stop":  #stop if auto_mode is off
                    #print("[AutoMode] Auto disable -> sending stop")
                    ser.write(b"stop\n")   #DON'T MODIFY
                    last_action = "stop"

            time.sleep(0.2) #sleep

        except Exception as e:
            print("Error in auto_mode:", e)
            time.sleep(1)

def serial_reader(ser, conn):
    """Read data from Arduino and resent to the TCP client."""
    try:
        while running:
            line = ser.readline() #read from Arduino
            if not line:
                time.sleep(0.005)
                continue
            try:
                if conn:
                    conn.sendall(line) #send to TCP client
            except Exception:
                pass
    except Exception as e:
        print("Serial reader stopped:", e)

def tcp_client_thread(conn, addr, ser):
    """Handles TCP client communication"""
    global auto_mode_button, current_conn  #using global variables

    print(f"Client connected: {addr}")

    with conn_Lock: #lock access to current_conn, make the change, then unlock it
        current_conn = conn  #Store active connection

    pump = threading.Thread(target=serial_reader, args=(ser, conn), daemon=True)
    pump.start()

    try:
        buf = b''
        while True:
            data = conn.recv(4096) #Receive data from client
            if not data:
                break
            buf += data
            while b'\n' in buf:
                line, buf = buf.split(b'\n', 1)
                cmd = line.strip().decode("utf-8") #decodes each line from byte to string

                if cmd.lower() == "auto on":
                    auto_mode_button = True
                    print("Auto mode ACTIVATED!")
                elif cmd.lower() == "auto off":
                    auto_mode_button = False
                    print("Auto mode DEACTIVATED!")
                elif cmd == "stop_button":
                    auto_mode_button = False
                    time.sleep(0.1)
                    ser.write(b"stop\n")
                    #time.sleep(0.1)

                    print("Function stop 3")
                elif cmd.lower() == "quit":
                    auto_mode_button = False
                    print("Quit received")
                    break

                else:
                    print(f"[TCP->SERIAL] Forwarding to Arduino: '{cmd}'")
                    ser.write((cmd + "\n").encode("utf-8"))
    except Exception as e:
        print("Client error:", e)
    finally:
        try:
            conn.close()
        except:
            pass
        with conn_Lock:
            current_conn = None
        print("Client disconnected")
def main():

    # Serial Connection with Arduino
    try:
        ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=0.02)
    except Exception as e:
        print("Failed to open serial:", e)
        sys.exit(1)

    # Thread that sends distance every 0.5 sec
    def sensor_loop(ser):
        global current_conn
        while running:
            try:
                dist = get_distance()  #calling the function
                msg = f"Distance:{dist}cm\n"

                try:
                    with conn_Lock: # in a loop , it ensures the sensor thread doesn't try to send data
                        if current_conn:
                            current_conn.sendall(msg.encode("utf-8"))
                except Exception:
                    pass
                time.sleep(0.5)
            except Exception as e:
                print("Error in sensor_loop:", e)
                time.sleep(1)

    threading.Thread(target=sensor_loop, args=(ser,), daemon=True).start() #sensor loop
    threading.Thread(target=auto_mode, args=(ser,), daemon=True).start()   #auto_mode

    # TCP server
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((TCP_HOST, TCP_PORT))
    s.listen(1)     #makes a socket ready for accepting connections

    print(f"Bridge listening on {TCP_HOST}:{TCP_PORT}, forwarding -> {SERIAL_PORT}@{SERIAL_BAUD}")

    try:
        while True:
            conn, addr = s.accept()
            threading.Thread(target=tcp_client_thread, args=(conn, addr, ser), daemon=True).start()
            #daemon runs and exits when the main program ends
    finally:
        global running
        running = False  # 🛑 Tell threads to stop

    try:
        ser.write(b"Quit\n")  # 👋 Let Arduino know we're shutting down
    except:
        pass  # If it fails, no big deal — we're quitting anyway

    s.close()
    ser.close()
    GPIO.cleanup()

if __name__ == "__main__":
    main()
