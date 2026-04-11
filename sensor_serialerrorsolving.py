#!/usr/bin/env python3
# This was modified on 3/7/2026
import socket, threading, sys, time
import serial
import RPi.GPIO as GPIO #controlling GPIo pins
from collections import deque  


# ---- Adjust these values if necessary. ----
SERIAL_PORT = '/dev/ttyACM0'   # o /dev/ttyUSB0   or /dev/ttyACM0
SERIAL_BAUD = 115200
TCP_HOST    = '0.0.0.0' #174.234.241.63
TCP_PORT    = 8765

# ---------------------------------------------

#Front Sensor
TRIG1 = 21
ECHO1 = 16

GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG1, GPIO.OUT)
GPIO.setup(ECHO1, GPIO.IN)

#Side Sensor
TRIG2 = 20
ECHO2 = 12

GPIO.setup(TRIG2, GPIO.OUT)
GPIO.setup(ECHO2, GPIO.IN)

def get_distance(TRIG, ECHO):
    GPIO.output(TRIG, False)
    time.sleep(0.002)

    # 10 microsecond pulse
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    start = time.time()
    timeout = start + 0.04  # 40ms max wait

    # Wait for echo HIGH
    while GPIO.input(ECHO) == 0:
        start = time.time()
        if start > timeout:
            return 999  # no echo

    # Wait for echo LOW
    end = time.time()
    while GPIO.input(ECHO) == 1:
        end = time.time()
        if end > timeout:
            return 999  # stuck high

    distance = (end - start) * 17150
    return round(distance, 2)


# Variables globales
safe_distance = 20

#change the number for distance
auto_mode_button = False  # "False" It will be controlled for GUI
current_conn = None       #storesactive TCP connection
conn_lock = threading.Lock()
#to make sure only one thread at a time touches current_conn
running = True

cmd_history= deque(maxlen=100)  #automatically removes the oldest entry when full
file_lock = threading.Lock()  #Lock to prevent FastApi and the TCP from writing/reading at the same time


def auto_mode(ser):
    """Auto Mode: Go forward and backward depending on the sensor"""

    global auto_mode_button, safe_distance

    last_action = None #tracks last movement command

    while running: #while auto_mode is "On"
        try:
            if auto_mode_button:
                d1 = get_distance(TRIG1, ECHO1) #calling the get distance function
                print(f"[Auto Mode] Distance1: {d1} cm")

                if d1 < safe_distance: #obstacle detected
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
                        time.sleep(2) #wait for 2 seconds to let the robot move backward

                        if not auto_mode_button:
                            continue


                        #print("[AUTO MODE] sending -> turn (after back and stop)")
                        cmd= "V 1.00 -1.00"
                        ser.write((cmd + "\n").encode("utf-8")) #to turn right
                        time.sleep(2)



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
            
def save_history():
    """ Writes the last 100 commands to data.bin in a safe, atomic way,
        using a lock so only one thread writes at a time.
    """ 
    file_path = "data_bin"
    with file_lock:
        with open (file_path,"wb") as f:
            for c in cmd_history:
                f.write((c + "\n").encode("utf-8"))

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

    with conn_lock: #lock access to current_conn, make the change, then unlock it
        current_conn = conn  #Store active connection

    pump = threading.Thread(target=serial_reader, args=(ser, conn), daemon=True)
    pump.start()

    try:
        buf = b''
        while running:
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
                    #global running
                    auto_mode_button = False
                    #running = False
                    print("Quit received - shutting down.")
                    try:
                        ser.write(b"Quit\n") #Tell Arduino to Stop
                    except:
                        pass

                    try:
                        conn.close() #Close TCP connection
                    except:
                        pass
                    with conn_lock:
                        current_conn = None
                    return
                    #break

                else:
                    print(f"[TCP->SERIAL] Forwarding to Arduino: '{cmd}'")
                    ser.write((cmd + "\n").encode("utf-8"))
                    cmd_history.append(cmd)   # Stores the command in the history
                    save_history() 

    except Exception as e:
        print("Client error:", e)
    finally:
        try:
            conn.close()
        except:
            pass
        with conn_lock:
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
                # Read sensor 1
                d1 = get_distance(TRIG1, ECHO1) # d1 is always read first for auto_mode

                # Prevent interference
                time.sleep(0.03) #30ms 

                # Read sensor 2
                d2 = get_distance(TRIG2, ECHO2)

                msg = f"D1:{d1}cm D2:{d2}cm\n"

                try:
                    with conn_lock:
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

    s.settimeout(1.0) #timeout for accepting connections, allows to check "running" periodically


    print(f"Bridge listening on {TCP_HOST}:{TCP_PORT}, forwarding -> {SERIAL_PORT}@{SERIAL_BAUD}")

    try:
        global running
        while running:

            try:
                conn, addr = s.accept()
                threading.Thread(target=tcp_client_thread, args=(conn, addr, ser), daemon=True).start()
                #daemon runs and exits when the main program ends
            except socket.timeout: #for periodically checking the "running" variable
                continue

    #global running
    finally:
        #global running

        running = False  #Tell threads to stop

    try:
        ser.write(b"Quit\n")  #Let Arduino know we're shutting down
    except:
        pass

    s.close()
    ser.close()
    GPIO.cleanup()

if __name__ == "__main__":
    main()