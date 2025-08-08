#include <Wire.h> 
#include <WiFi.h>
#include <PubSubClient.h>
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
const char* slotIDs[5] = {"P1", "P2", "P3", "P4", "P5"}; 
String lastSlotStatus[5]; 
unsigned long lastSlotCheckTime = 0;
int carNum=0;

#define buzzer 15

const char* WIFI_SSID = "SSIoT-01";
const char* WIFI_PASSWORD = "SSIoT-01";

// -- MQTT --
const char* MQTT_BROKER_IP = "172.20.10.12"; // IP của Raspberry Pi (Broker)
const int   MQTT_PORT = 1883;

// --- BIẾN TOÀN CỤC ---
WiFiClient espClient;
PubSubClient client(espClient);

void setup_wifi() {
  delay(10);
  Serial.println("\nConnecting to WiFi...");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected!");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
}

void reconnect_mqtt() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    String clientId = "ESP32-ParkingSystem-";
    clientId += String(random(0xffff), HEX);
    if (client.connect(clientId.c_str())) {
      Serial.println("connected!");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

void checkAndPublishSlotStatus() {
  int currentCarNum = 0;
  
  // Vòng lặp qua 5 ô đỗ
  for (int n = 0; n < 5; n++) {
    String currentStatus;
    // Xác định trạng thái hiện tại
    if (digitalRead(slots[n]) == LOW) { // LOW nghĩa là có xe
      currentStatus = "occupied";
      currentCarNum++;
    } else {
      currentStatus = "free";
    }

    // MQTT: Chỉ gửi tin nhắn nếu trạng thái thay đổi
    if (currentStatus != lastSlotStatus[n]) {
      // Tạo topic động, ví dụ: "parking/spot/S1/status"
      char topic[50];
      snprintf(topic, sizeof(topic), "parking/spot/%s/status", slotIDs[n]);
      
      Serial.printf("Slot %s changed to %s. Publishing to MQTT...\n", slotIDs[n], currentStatus.c_str());
      
      // Gửi tin nhắn lên Broker, retained=true để client mới kết nối cũng nhận được trạng thái
      client.publish(topic, currentStatus.c_str(), true);
      
      // Cập nhật trạng thái cuối cùng
      lastSlotStatus[n] = currentStatus;
    }

  }
  
  // Cập nhật tổng số xe
  if(currentCarNum != carNum) {
    carNum = currentCarNum;
    showLCD(); // Gọi showLCD chỉ khi tổng số xe thay đổi
  }
}

void setup() {
  Serial.begin(115200);
  lcd.begin();   /// khác cũ 
  lcd.backlight();
  lcd.setCursor(0,0);
  lcd.print("Flawless Parking");
  lcd.setCursor(4,1);
  lcd.print("xin chao");
  delay(1000);
  lcd.clear();
  
  pinMode(buzzer,OUTPUT);
  pinMode(inPos,INPUT_PULLUP);
  pinMode(outPos,INPUT_PULLUP);
  for(int n=0;n<5;n++){
    pinMode(slots[n],INPUT_PULLUP);
    lastSlotStatus[n] = ""; // MQTT: Khởi tạo trạng thái rỗng
  }
  ESP32PWM::allocateTimer(0);
	ESP32PWM::allocateTimer(1);
	ESP32PWM::allocateTimer(2);
	ESP32PWM::allocateTimer(3);
  servo1.setPeriodHertz(50);
  servo2.setPeriodHertz(50);
  servo1.attach(servo1Pin,500,2400);
  servo2.attach(servo2Pin,500,2400);

  setup_wifi();
  client.setServer(MQTT_BROKER_IP, MQTT_PORT);
  checkAndPublishSlotStatus();
  showLCD();
}

void loop() {
    // --- Luôn duy trì kết nối MQTT ---
  if (!client.connected()) {
    reconnect_mqtt();
  }
  client.loop();

  // --- MQTT: Kiểm tra trạng thái các ô đỗ mỗi 1 giây ---
  if (millis() - lastSlotCheckTime > 100) {
    lastSlotCheckTime = millis();
    checkAndPublishSlotStatus();
  }
  if(pos1!=posOpen&&digitalRead(inPos)!=LOW&&digitalRead(outPos)!=LOW)showLCD();
  //xử lý xe vào
  if(digitalRead(inPos)==LOW){
    if(inPosState==HIGH){
      timeWait=millis();
      if(carNum>=5){
        lcd.clear();
        lcd.print("Het cho");
        lcd.setCursor(0,1);
        lcd.print("Khong con cho de xe");
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
          lcd.print("Barie da mo");
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
        lcd.print("Xe ra khoi bai");
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
      lcd.print("P1:");
    }
    if(n==1){
      lcd.setCursor(5,0);
      lcd.print("P2:");
    }
    if(n==2){
      lcd.setCursor(10,0);
      lcd.print("P3:");
    }
    if(n==3){
      lcd.setCursor(0,1);
      lcd.print("P4:");
    }
    if(n==4){
      lcd.setCursor(5,1);
      lcd.print("P5:");
    }
    if(digitalRead(slots[n])==LOW){
      lcd.print("F");
      carNum++;
    }else{
      lcd.print("E");
    }
  }
  lcd.setCursor(10,1);
  lcd.print("TONG:");
  lcd.print(carNum);
} 