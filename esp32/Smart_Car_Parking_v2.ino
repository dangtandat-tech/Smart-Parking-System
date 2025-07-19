#include <Wire.h>
#include <LiquidCrystal_I2C.h>
LiquidCrystal_I2C lcd(0x27, 16, 2); // Địa chỉ I2C 0x27, LCD 16x2
#include <ESP32Servo.h>
#define servo1Pin 18
#define servo2Pin 19
Servo servo1;
Servo servo2;
int pos1 = 0;
int pos2 = 0;
#define posClose 0
#define posOpen  90

#define inPos 32
#define outPos 13
bool inPosState = HIGH;
bool outPosState = HIGH;

#define TIMEWAIT 1000
unsigned long timeWait = 0;

const int slots[5] = {14, 27, 26, 25, 33};
int carNum = 0;

#define buzzer 15

void setup() {
  Serial.begin(115200);
  lcd.begin(); // Sử dụng begin() không tham số
  lcd.backlight();
  lcd.setCursor(4, 0);
  lcd.print("Welcome!");
  delay(1000);
  lcd.clear();
  
  pinMode(buzzer, OUTPUT);
  pinMode(inPos, INPUT_PULLUP);
  pinMode(outPos, INPUT_PULLUP);
  for (int n = 0; n < 5; n++) {
    pinMode(slots[n], INPUT_PULLUP);
  }
  
  // Cấu hình servo
  ESP32PWM::allocateTimer(0);
  ESP32PWM::allocateTimer(1);
  ESP32PWM::allocateTimer(2);
  ESP32PWM::allocateTimer(3);
  servo1.setPeriodHertz(50);
  servo2.setPeriodHertz(50);
  servo1.attach(servo1Pin, 500, 2400);
  servo2.attach(servo2Pin, 500, 2400);

  // Đặt servo về vị trí ban đầu
  servo1.write(posClose);
  servo2.write(posClose);
  pos1 = posClose;
  pos2 = posClose;
  
  showLCD();
}

void loop() {
  // Kiểm tra trạng thái cảm biến vào/ra
  bool currentInPos = (digitalRead(inPos) == LOW);
  bool currentOutPos = (digitalRead(outPos) == LOW);
  
  // Xử lý xe vào
  if (currentInPos) {
    if (inPosState == HIGH) {
      timeWait = millis();
      if (carNum >= 5) {
        lcd.clear();
        lcd.print("Car Full");
        lcd.setCursor(0, 1);
        lcd.print("Slot Unavailable");
        beep(800, 2);
      }
      inPosState = LOW;
    }
    
    if (carNum < 5 && (millis() - timeWait > TIMEWAIT)) {
      if (pos1 == posClose) {
        openBarrier(&servo2, &pos1);
        lcd.clear();
        lcd.print("Car Entered");
        beep(500, 1);
        carNum++;
        showLCD();
      }
    }
  } else {
    if (inPosState == LOW) {
      timeWait = millis();
      inPosState = HIGH;
    }
    
    if (pos1 == posOpen && (millis() - timeWait > TIMEWAIT)) {
      closeBarrier(&servo2, &pos1);
    }
  }

  // Xử lý xe ra
  if (currentOutPos) {
    if (outPosState == HIGH) {
      timeWait = millis();
      outPosState = LOW;
    }
    
    if (millis() - timeWait > TIMEWAIT) {
      if (pos2 == posClose) {
        openBarrier(&servo1, &pos2);
        lcd.clear();
        lcd.print("Car is out");
        beep(500, 1);
        carNum = (carNum > 0) ? carNum - 1 : 0;
        showLCD();
      }
    }
  } else {
    if (outPosState == LOW) {
      timeWait = millis();
      outPosState = HIGH;
    }
    
    if (pos2 == posOpen && (millis() - timeWait > TIMEWAIT)) {
      closeBarrier(&servo1, &pos2);
    }
  }
}

void openBarrier(Servo* s, int* pos) {
  for (int i = *pos; i <= posOpen; i += 5) {
    s->write(i);
    delay(15);
  }
  *pos = posOpen;
}

void closeBarrier(Servo* s, int* pos) {
  for (int i = *pos; i >= posClose; i -= 5) {
    s->write(i);
    delay(15);
  }
  *pos = posClose;
}

void beep(int duration, int times) {
  for (int i = 0; i < times; i++) {
    digitalWrite(buzzer, HIGH);
    delay(duration);
    digitalWrite(buzzer, LOW);
    if (i < times - 1) delay(duration);
  }
}

void showLCD() {
  carNum = 0;
  lcd.clear();
  
  // Hiển thị slot 1-3 ở hàng đầu
  lcd.setCursor(0, 0);
  for (int n = 0; n < 3; n++) {
    lcd.print("S");
    lcd.print(n+1);
    lcd.print(":");
    if (digitalRead(slots[n]) == LOW) {
      lcd.print("F ");
      carNum++;
    } else {
      lcd.print("E ");
    }
  }
  
  // Hiển thị slot 4-5 và tổng xe ở hàng dưới
  lcd.setCursor(0, 1);
  for (int n = 3; n < 5; n++) {
    lcd.print("S");
    lcd.print(n+1);
    lcd.print(":");
    if (digitalRead(slots[n]) == LOW) {
      lcd.print("F ");
      carNum++;
    } else {
      lcd.print("E ");
    }
  }
  
  lcd.setCursor(10, 1);
  lcd.print("C:");
  lcd.print(carNum);
}