// PWM pins
#define ENA 3   // Front Left M6
#define ENB 5   // Rear Left M5
#define ENC 4  // Rear Right M2
#define END 2  // Front Right M3

// Direction pins
#define EN1 23  // Front Left M6 

#define EN3 25   // Rear Left M5

#define EN5 22   // Rear Right M2

#define EN7 24  // Front Right M3



bool autoMode = false;   // 
bool parallel = false;

void setup() {
  Serial.begin(115200);

  // Set PWM pins
  pinMode(ENA, OUTPUT);
  pinMode(ENB, OUTPUT);
  pinMode(ENC, OUTPUT);
  pinMode(END, OUTPUT);

  // Set direction pins
  pinMode(EN1, OUTPUT);
  
  pinMode(EN3, OUTPUT);
  
  pinMode(EN5, OUTPUT);
  
  pinMode(EN7, OUTPUT);
  
}

void loop() {
  //  
  while (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    if (cmd == "auto on") {
      autoMode = true;
      Serial.println("Auto mode: ON");
    } 
    else if (cmd == "auto off" or cmd == "Quit") {
      autoMode = false;
      Serial.println("Auto mode: OFF");
      stop();
    }
    else if (cmd == "parallel on") {
      parallel = true;
      Serial.println("Parallel parking: ON");
    }
    else if (cmd == "parallel off"){
      parallel = false;
      Serial.println("Parallel parking: OFF");
    }

    else if (cmd == "stop_button" ) { 
      autoMode = false;
      parallel = false;
      Serial.println("sending from Arduino STOP");
      stop();
      //delay(20000);
    }
    else if (cmd.startsWith("V ")) {
      float right = cmd.substring(2, cmd.indexOf(' ', 2)).toFloat();
      float left = cmd.substring(cmd.indexOf(' ', 2) + 1).toFloat();
      setMotorSpeeds(left, right);
    } 
    
    else {
      setMotor(cmd, 255);
    }
  }

  
}

void stop() {
  analogWrite(ENA, 0);
  analogWrite(ENB, 0);
  analogWrite(ENC, 0);
  analogWrite(END, 0);
}

void setMotor(String dir, int pwm) {
  analogWrite(ENA, pwm);
  analogWrite(ENB, pwm);
  analogWrite(ENC, pwm);
  analogWrite(END, pwm);

  if (dir == "s") { // Backwards  old "w"
    digitalWrite(EN1, HIGH); 
    digitalWrite(EN3, HIGH); 
    digitalWrite(EN5, HIGH); 
    digitalWrite(EN7, HIGH); 
  } else if (dir == "w") { // Forwards  old "s"
    digitalWrite(EN1, LOW); 
    digitalWrite(EN3, LOW); 
    digitalWrite(EN5, LOW); 
    digitalWrite(EN7, LOW); 
  } else if (dir == "d") { // Turn Right  old "a"
    digitalWrite(EN1, LOW); 
    digitalWrite(EN3, LOW); 
    digitalWrite(EN5, HIGH); 
    digitalWrite(EN7, HIGH); 
  } else if (dir == "a") { // Turn Left  old "d"
    digitalWrite(EN1, HIGH); 
    digitalWrite(EN3, HIGH); 
    digitalWrite(EN5, LOW); 
    digitalWrite(EN7, LOW); 
  } else if (dir == "esc" || dir == "stop") {
    stop();
  } else {
    stop();
  }

  Serial.println(dir);
}

void setMotorSpeeds(float left, float right) {
  int pwmL = constrain(abs(left) * 85, 0, 255);
  int pwmR = constrain(abs(right) * 85, 0, 255);

  analogWrite(ENA, pwmL);
  analogWrite(ENB, pwmL);
  analogWrite(ENC, pwmR);
  analogWrite(END, pwmR);

  // Left motors
  digitalWrite(EN1, left >= 0 ? LOW : HIGH);
  
  digitalWrite(EN3, left >= 0 ? LOW : HIGH);
  

  // Right motors
  digitalWrite(EN5, right >= 0 ? LOW : HIGH);
  
  digitalWrite(EN7, right >= 0 ? LOW : HIGH);
 

  Serial.print("V ");
  Serial.print(left);
  Serial.print(" ");
  Serial.println(right);
}
