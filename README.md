# rover-project
Repository for all files related to rover project.
LandBot Project

LandBot is a Raspberry Pi–Arduino powered rover with four motor controls, an ultrasonic sensor for obstacle detection, and a Tkinter GUI for remote operation.
It supports both manual and auto modes, with real‑time telemetry.

*All locations are based off Back (Where Estop button is) and Front (Where the arm is by)*

*PWM -> PWM Pin on Arduino and PWM label for H-Bridge ((slow)0 -> (fast)255)
*DIR -> Direction pin on H-Bridge (HIGH = Forward, LOW = Backwards)

----------------------
 PIN OUTS FOR ARDUINO 
----------------------
-----------------------------------------------------------------------------
Motor 1 - Front Right:

PWM - 2
DIR - 22
-----------------------------------------------------------------------------
Motor 2 - Front Left:

PWM - 3
DIR - 23
-----------------------------------------------------------------------------
Motor 3 - Back Right:

PWM - 4
DIR - 24
-----------------------------------------------------------------------------
Motor 4 - Back Left:

PWM - 5
DIR - 25
-----------------------------------------------------------------------------
-------------------------------------------------------
Pins connected to the sensor on the Raspberry Pi 5
-------------------------------------------------------
-----------------------------------------------------------------------------

TRIG = 23
ECHO = 24

-----------------------------------------------------------------------------

-----------------------------
 Directions to run the rover 
-----------------------------

Step 1) E-Stop button is pushed IN
Step 2) Plug battery in, Positive(RED) wire into (+)Node on battery then Negative(BLACK) wire into (-)Node on Battery
Step 3) Tuck battery under rover on black plastic floor into one of the holders
Step 4) Twist E-Stop to the right to turn rover on.
Step 5) Initial Code Setup: 
	
-->(1) Upload the "controller_automode" IDE code to the Arduino Mega
    - The Arduino Mega’s pins must match the pin assignments declared in the IDE code.
    - Landbot has 4 DIR pins, 1 DIR for each wheel and 1 PWM for each wheel
    - This code takes commands (W, A, S, D, STOP) from the pi via Serial monitor
      and controls the motors on the Landbot.

-->(2) On Raspberry Pi5: Run "Serial_communication.py"
    - Enter the Raspberry Pi’s IP address (find it with "Hostname -I").
    - The Pi and Laptop/PC MUST be on the SAME Wi-Fi network.
    - The sensor pins on the Raspberry Pi must match the pins declared in the Python code.
    - To change the distance, update the global variable  located at line 43.
    
This Python script runs on a Raspberry Pi 5 to control a robot through an Arduino. It uses an ultrasonic sensor to measure distance and avoid obstacles, automatically stopping, reversing, or turning when objects are detected within a safe range. The program also hosts a TCP server, allowing remote clients to send commands and receive sensor data in real time.

-->(3) On Laptop/PC: Run "TankGUI.py"
    - Edit the IP address to match the Pi's hosted IP
    - Must be connected to the same WIFI network

The TankGUI program provides a remote control interface for a Raspberry Pi–Arduino robot. Running on a PC or laptop, it uses a Tkinter‑based GUI to send movement commands (forward, back, left, right) via TCP and display real‑time telemetry from both the Arduino and the distance sensor. Users can adjust speed limits with sliders, toggle auto mode for obstacle avoidance, and issue stop or quit commands for safety. The GUI also supports remote SSH actions, such as triggering a cleaning script, and ensures safe shutdown by closing connections and stopping the robot before exit.






