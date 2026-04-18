#!/usr/bin/env python3
import socket, threading, sys, time
import serial
import RPi.GPIO as GPIO
from collections import deque

# ---- Adjust these values if necessary. ----
SERIAL_PORT = '/dev/ttyACM0'
SERIAL_BAUD = 115200
TCP_HOST = '0.0.0.0'

COMMAND_PORT = 8765   
SENSOR_PORT  = 8766   # command_port + 1

# ---------------------------------------------
TRIG1 = 23
ECHO1 = 24

GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG1, GPIO.OUT)
GPIO.setup(ECHO1, GPIO.IN)

def get_distance(TRIG, ECHO):
    GPIO.output(TRIG, False)
    time.sleep(0.002)

    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    start = time.time()
    timeout = start + 0.04

    while GPIO.input(ECHO) == 0:
        start = time.time()
        if start > timeout:
            return 999

    end = time.time()
    while GPIO.input(ECHO) == 1:
        end = time.time()
        if end > timeout:
            return 999

    distance = (end - start) * 17150
    return round(distance, 2)

safe_distance = 20
auto_mode_button = False
parallel_button = False
running = True

cmd_history = deque(maxlen=100)
file_lock = threading.Lock()

# Sockets
command_conn = None
command_lock = threading.Lock()

sensor_conn = None
sensor_lock = threading.Lock()

def save_history():
    file_path = "/home/pi/Desktop/Landbot_codes/small_rover/data.bin" #modify the path
    with file_lock:
        with open(file_path, "wb") as f:
            for c in cmd_history:
                f.write((c + "\n").encode("utf-8"))

def auto_mode(ser):
    global auto_mode_button, safe_distance, running
    last_action = None

    while running:
        try:
            if auto_mode_button:
                d1 = get_distance(TRIG1, ECHO1)
                print(f"[Auto Mode] Distance1: {d1} cm")

                if d1 < safe_distance:
                    if last_action != "right":
                        ser.write(b"stop\n")
                        time.sleep(0.01)

                        if not auto_mode_button:
                            continue

                        cmd = "V -1.00 -1.00"
                        ser.write((cmd + "\n").encode("utf-8"))
                        time.sleep(2)

                        if not auto_mode_button:
                            continue

                        cmd = "V 1.00 -1.00"
                        ser.write((cmd + "\n").encode("utf-8"))
                        time.sleep(2)

                        last_action = "right"
                        time.sleep(0.01)
                        last_action = None
                else:
                    cmd = "V 1.00 1.00"
                    ser.write((cmd + "\n").encode("utf-8"))
            else:
                if last_action != "stop":
                    ser.write(b"stop\n")
                    last_action = "stop"

            time.sleep(0.2)
        except Exception as e:
            print("Error in auto_mode:", e)
            time.sleep(1)

def parallel(ser):
    global parallel_button, running
    while running:
        try:
            if parallel_button:
                seq = [
                    ("V 1.00 1.00", 1),
                    ("V -0.50 -0.50", 1),
                    ("V -0.50 0.50", 1),
                    ("V 0.50 0.50", 1),
                    ("V 0.50 -0.50", 1),
                    ("V -0.50 -0.50", 1),
                ]
                for cmd, t in seq:
                    if not parallel_button:
                        ser.write(b"V 0.00 0.00\n")
                        break
                    ser.write((cmd + "\n").encode("utf-8"))
                    time.sleep(t)

                ser.write(b"V 0.00 0.00\n")
                parallel_button = False
        except Exception as e:
            print("Error in parallel_button:", e)

def serial_reader(ser):
    """If you want to forward Arduino serial back to the command client, you can extend this."""
    global running
    while running:
        try:
            line = ser.readline()
            if not line:
                time.sleep(0.005)
                continue
            # If you want to forward serial to command client:
            with command_lock:
                if command_conn:
                    try:
                        command_conn.sendall(line)
                    except Exception:
                        pass
        except Exception as e:
            print("Serial reader stopped:", e)
            time.sleep(0.5)

def handle_command_client(conn, addr, ser):
    global auto_mode_button, parallel_button, running, command_conn
    print(f"[COMMAND] Client connected: {addr}")

    with command_lock:
        command_conn = conn

    try:
        buf = b""
        while running:
            data = conn.recv(4096)
            if not data:
                break
            buf += data
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                cmd = line.strip().decode("utf-8")

                if cmd.lower() == "auto on":
                    auto_mode_button = True
                    print("Auto mode ACTIVATED!")
                elif cmd.lower() == "auto off":
                    auto_mode_button = False
                    print("Auto mode DEACTIVATED!")
                elif cmd.lower() == "parallel_button":
                    parallel_button = True
                    print("Parallel parking ACTIVATED!")
                elif cmd == "stop_button":
                    auto_mode_button = False
                    time.sleep(0.1)
                    ser.write(b"stop\n")
                    print("STOP button pressed")
                elif cmd.lower() == "get_history":
                    with file_lock:
                        try:
                            file_path = "/home/pi/Desktop/Landbot_codes/small_rover/data.bin"
                            with open(file_path, "rb") as f:
                                data = f.read()
                            conn.sendall(data + b"\nEND_OF_HISTORY\n")
                        except Exception as e:
                            print("Error sending history:", e)
                            conn.sendall(b"ERROR\n")
                elif cmd.lower() == "quit":
                    auto_mode_button = False
                    print("Quit received - shutting down.")
                    try:
                        ser.write(b"Quit\n")
                    except:
                        pass
                    try:
                        conn.close()
                    except:
                        pass
                    with command_lock:
                        command_conn = None
                    return
                else:
                    print(f"[TCP->SERIAL] '{cmd}'")
                    ser.write((cmd + "\n").encode("utf-8"))
                    cmd_history.append(cmd)
                    save_history()
    except Exception as e:
        print("Command client error:", e)
    finally:
        try:
            conn.close()
        except:
            pass
        with command_lock:
            command_conn = None
        print("[COMMAND] Client disconnected")

def sensor_loop(ser):
    global sensor_conn, running
    while running:
        try:
            d1 = get_distance(TRIG1, ECHO1)
            msg = f"D1:{d1}cm\n"

            with sensor_lock:
                if sensor_conn:
                    try:
                        sensor_conn.sendall(msg.encode("utf-8"))
                    except Exception:
                        pass

            time.sleep(0.5)
        except Exception as e:
            print("Error in sensor_loop:", e)
            time.sleep(1)

def main():
    global running, sensor_conn

    try:
        ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=0.02)
    except Exception as e:
        print("Failed to open serial:", e)
        sys.exit(1)

    threading.Thread(target=auto_mode, args=(ser,), daemon=True).start()
    threading.Thread(target=parallel, args=(ser,), daemon=True).start()
    threading.Thread(target=sensor_loop, args=(ser,), daemon=True).start()
    threading.Thread(target=serial_reader, args=(ser,), daemon=True).start()

    # Command server
    cmd_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    cmd_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    cmd_server.bind((TCP_HOST, COMMAND_PORT))
    cmd_server.listen(1)
    cmd_server.settimeout(1.0)

    # Sensor server
    sensor_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sensor_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sensor_server.bind((TCP_HOST, SENSOR_PORT))
    sensor_server.listen(1)
    sensor_server.settimeout(1.0)

    print(f"[PI] Command server on {TCP_HOST}:{COMMAND_PORT}")
    print(f"[PI] Sensor server  on {TCP_HOST}:{SENSOR_PORT}")

    try:
        while running:
            # Accept command client
            try:
                conn, addr = cmd_server.accept()
                threading.Thread(target=handle_command_client,
                                 args=(conn, addr, ser),
                                 daemon=True).start()
            except socket.timeout:
                pass

            # Accept sensor client
            try:
                sconn, saddr = sensor_server.accept()
                print(f"[SENSOR] Client connected: {saddr}")
                with sensor_lock:
                    sensor_conn = sconn
            except socket.timeout:
                pass

    finally:
        running = False
        try:
            ser.write(b"Quit\n")
        except:
            pass
        cmd_server.close()
        sensor_server.close()
        ser.close()
        GPIO.cleanup()

if __name__ == "__main__":
    main()