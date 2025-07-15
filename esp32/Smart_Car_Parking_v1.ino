#include <Wire.h> 
#include <LiquidCrystal_I2C.h>
LiquidCrystal_I2C lcd(0x27,16,2);
#include <ESP32Servo.h>
#define servo1Pin 18
#define servo2Pin 19
Servo servo1;
Servo servo2;
int pos1=0;
int pos2=0;
#define posClose 0
#define posOpen  90

#define inPos 32
#define outPos 13
bool inPosState=HIGH;
bool outPosState=HIGH;

#define TIMEWAIT 1000
unsigned long timeWait=millis();

const int slots[5]={14,27,26,25,33};
int carNum=0;

#define buzzer 15

void setup() {
  Serial.begin(115200);
  lcd.init();   /// khác cũ 
  lcd.backlight();
  lcd.setCursor(4,0);
  lcd.print("Welcome!");
  delay(1000);
  lcd.clear();
  
  pinMode(buzzer,OUTPUT);
  pinMode(inPos,INPUT_PULLUP);
  pinMode(outPos,INPUT_PULLUP);
  for(int n=0;n<5;n++){
    pinMode(slots[n],INPUT_PULLUP);
  }
  ESP32PWM::allocateTimer(0);
	ESP32PWM::allocateTimer(1);
	ESP32PWM::allocateTimer(2);
	ESP32PWM::allocateTimer(3);
  servo1.setPeriodHertz(50);
  servo2.setPeriodHertz(50);
  servo1.attach(servo1Pin,500,2400);
  servo2.attach(servo2Pin,500,2400);

  showLCD();
}

void loop() {
  if(pos1!=posOpen&&digitalRead(inPos)!=LOW&&digitalRead(outPos)!=LOW)showLCD();
  //xử lý xe vào
  if(digitalRead(inPos)==LOW){
    if(inPosState==HIGH){
      timeWait=millis();
      if(carNum>=5){
        lcd.clear();
        lcd.print("Car Full");
        lcd.setCursor(0,1);
        lcd.print("Slot Unavailable");
        beep(800,2);
      }
      inPosState=LOW;
    }
    if(carNum<5){
      if(millis()-timeWait>TIMEWAIT){
        if(pos1==posClose){
          for(int i=posClose;i<posOpen;i+=5){
            servo2.write(i);
            delay(15);
          }
          servo2.write(posOpen);
          pos1=posOpen;
          lcd.clear();
          lcd.print("Car Entered");
          beep(500,1);
        }
      }
    }
  }else{
    if(inPosState==LOW){
      timeWait=millis();
      lcd.clear();
      showLCD();
      inPosState=HIGH;
    }
    if(millis()-timeWait>TIMEWAIT){
      if(pos1==posOpen){
        for(int i=posOpen;i>posClose;i-=5){
          servo2.write(i);
          delay(15);
        }
        servo2.write(posClose);
        pos1=posClose;
      }
    }
  }
  //xử lý xe ra
  if(digitalRead(outPos)==LOW){
    if(outPosState==HIGH){
      timeWait=millis();
      outPosState=LOW;
    }
    if(millis()-timeWait>TIMEWAIT){
      if(pos2==posClose){
        for(int i=posClose;i<posOpen;i+=5){
          servo1.write(i);
          delay(15);
        }
        servo1.write(posOpen);
        pos2=posOpen;
        lcd.clear();
        lcd.print("Car is out");
        beep(500,1);
      }
    }
  }else{
    if(outPosState==LOW){
      timeWait=millis();
      lcd.clear();
      showLCD();
      outPosState=HIGH;
    }
    if(millis()-timeWait>TIMEWAIT){
      if(pos2==posOpen){
        for(int i=posOpen;i>posClose;i-=5){
          servo1.write(i);
          delay(15);
        }
        servo1.write(posClose);
        pos2=posClose;
      }
    }
  }
}
void beep(int d, int num){
  for(int i=0;i<num;i++){
    digitalWrite(buzzer,HIGH);
    delay(d);
    digitalWrite(buzzer,LOW);
    delay(d);
  }
}
void showLCD(){
  carNum=0;
  for(int n=0;n<5;n++){
    if(n==0){
      lcd.setCursor(0,0);
      lcd.print("S1:");
    }
    if(n==1){
      lcd.setCursor(5,0);
      lcd.print("S2:");
    }
    if(n==2){
      lcd.setCursor(10,0);
      lcd.print("S3:");
    }
    if(n==3){
      lcd.setCursor(0,1);
      lcd.print("S4:");
    }
    if(n==4){
      lcd.setCursor(5,1);
      lcd.print("S5:");
    }
    if(digitalRead(slots[n])==LOW){
      lcd.print("F");
      carNum++;
    }else{
      lcd.print("E");
    }
  }
  lcd.setCursor(10,1);
  lcd.print("CARS:");
  lcd.print(carNum);
} 