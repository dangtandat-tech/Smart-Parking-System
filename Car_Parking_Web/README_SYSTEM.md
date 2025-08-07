# 🚗 Hệ Thống Bãi Đỗ Xe Thông Minh

## 📋 Tổng Quan

Hệ thống bãi đỗ xe thông minh tích hợp:
- **Web Dashboard** cho người dùng đặt chỗ và theo dõi
- **MQTT Communication** để nhận dữ liệu real-time
- **ESP32 Sensors** phát hiện xe đỗ
- **Raspberry Pi Camera** nhận dạng biển số xe

## 🏗️ Cấu Trúc Hệ Thống

### Frontend Files:
- `login.html` - Trang đăng nhập/đăng ký
- `user_dashboard.html` - Dashboard người dùng
- `mqtt_simulator.html` - Công cụ mô phỏng MQTT
- `parking.html` - Giao diện quản trị (admin)

### Backend Integration:
- **MQTT Broker**: Nhận dữ liệu từ IoT devices
- **WebSocket**: Kết nối real-time với frontend
- **Database**: Lưu trữ thông tin đặt chỗ và người dùng

## 🔧 Setup và Cài Đặt

### 1. MQTT Broker Setup

```bash
# Cài đặt Mosquitto MQTT Broker
sudo apt-get update
sudo apt-get install mosquitto mosquitto-clients

# Start Mosquitto với WebSocket support
mosquitto -c mosquitto.conf
```

### 2. Mosquitto Configuration (mosquitto.conf)

```conf
# Port for MQTT
port 1883

# Port for WebSocket
listener 9001
protocol websockets

# Allow anonymous connections (chỉ để test)
allow_anonymous true

# Log settings
log_dest file /var/log/mosquitto/mosquitto.log
log_type error
log_type warning
log_type notice
log_type information
```

### 3. ESP32 Code (Arduino IDE)

```cpp
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";
const char* mqtt_server = "192.168.1.100"; // IP của MQTT broker

// Pins
const int trigPin = 5;
const int echoPin = 18;
const int ledPin = 2;

WiFiClient espClient;
PubSubClient client(espClient);

int spotId = 1; // ID của vị trí đỗ xe

void setup() {
    Serial.begin(115200);
    
    // Setup pins
    pinMode(trigPin, OUTPUT);
    pinMode(echoPin, INPUT);
    pinMode(ledPin, OUTPUT);
    
    // Connect to WiFi
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("WiFi connected");
    
    // Setup MQTT
    client.setServer(mqtt_server, 1883);
    client.setCallback(callback);
}

void loop() {
    if (!client.connected()) {
        reconnect();
    }
    client.loop();
    
    // Đọc cảm biến siêu âm
    long distance = readUltrasonic();
    bool carPresent = distance < 30; // Xe có mặt nếu khoảng cách < 30cm
    
    // Gửi dữ liệu mỗi 5 giây
    static unsigned long lastSend = 0;
    if (millis() - lastSend > 5000) {
        sendSensorData(carPresent, distance);
        lastSend = millis();
    }
    
    // LED indicator
    digitalWrite(ledPin, carPresent ? HIGH : LOW);
    
    delay(100);
}

long readUltrasonic() {
    digitalWrite(trigPin, LOW);
    delayMicroseconds(2);
    digitalWrite(trigPin, HIGH);
    delayMicroseconds(10);
    digitalWrite(trigPin, LOW);
    
    long duration = pulseIn(echoPin, HIGH);
    long distance = duration * 0.034 / 2;
    
    return distance;
}

void sendSensorData(bool occupied, long distance) {
    DynamicJsonDocument doc(1024);
    
    doc["spot_id"] = spotId;
    doc["occupied"] = occupied;
    doc["distance"] = distance;
    doc["timestamp"] = WiFi.getTime();
    doc["sensor_type"] = "ultrasonic";
    
    char buffer[256];
    serializeJson(doc, buffer);
    
    String topic = "parking/sensors/" + String(spotId);
    client.publish(topic.c_str(), buffer);
    
    Serial.println("Sent: " + String(buffer));
}

void callback(char* topic, byte* payload, unsigned int length) {
    // Xử lý message từ broker nếu cần
}

void reconnect() {
    while (!client.connected()) {
        if (client.connect("ESP32Client")) {
            Serial.println("MQTT connected");
        } else {
            delay(5000);
        }
    }
}
```

### 4. Raspberry Pi Camera Code (Python)

```python
import cv2
import pytesseract
import paho.mqtt.client as mqtt
import json
import time
import re
from datetime import datetime

# MQTT settings
MQTT_BROKER = "192.168.1.100"
MQTT_PORT = 1883
MQTT_TOPIC = "parking/camera/license_plate"

# Camera settings
camera = cv2.VideoCapture(0)
mqtt_client = mqtt.Client()

def connect_mqtt():
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_start()
    print("Connected to MQTT broker")

def preprocess_image(image):
    # Chuyển sang grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Áp dụng blur để giảm noise
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Threshold để tăng contrast
    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    return thresh

def extract_license_plate(image):
    # Preprocess image
    processed = preprocess_image(image)
    
    # OCR để đọc text
    text = pytesseract.image_to_string(processed, config='--psm 8 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ')
    
    # Clean và validate license plate format
    text = re.sub(r'[^A-Z0-9]', '', text.upper())
    
    # Vietnamese license plate pattern: 99A-9999 or 99AA-999
    patterns = [
        r'^[0-9]{2}[A-Z]{1}-[0-9]{4,5}$',
        r'^[0-9]{2}[A-Z]{2}-[0-9]{3,4}$'
    ]
    
    for pattern in patterns:
        if re.match(pattern, text):
            # Format with dash
            if len(text) == 7:  # 99A9999
                return f"{text[:3]}-{text[3:]}"
            elif len(text) == 8:  # 99AA999
                return f"{text[:4]}-{text[4:]}"
    
    return None

def calculate_confidence(text, image):
    # Simple confidence calculation based on text length and clarity
    if not text:
        return 0
    
    # Basic confidence metrics
    confidence = 50
    
    if len(text) >= 7:
        confidence += 20
    
    if '-' in text:
        confidence += 15
    
    # Check for common OCR errors
    if any(char in text for char in ['O', '0', 'I', '1']):
        confidence += 10
    
    return min(confidence, 95)

def send_license_plate_data(license_plate, spot_id, confidence):
    data = {
        "license_plate": license_plate,
        "spot_id": spot_id,
        "confidence": confidence,
        "timestamp": datetime.now().isoformat(),
        "camera_id": "cam_01"
    }
    
    mqtt_client.publish(MQTT_TOPIC, json.dumps(data))
    print(f"Sent: {license_plate} at spot {spot_id} (confidence: {confidence}%)")

def main():
    connect_mqtt()
    
    spot_id = 1  # ID của vị trí camera giám sát
    
    print("Starting license plate recognition...")
    
    while True:
        ret, frame = camera.read()
        if not ret:
            continue
        
        # Extract license plate
        license_plate = extract_license_plate(frame)
        
        if license_plate:
            confidence = calculate_confidence(license_plate, frame)
            
            if confidence > 70:  # Only send if confidence > 70%
                send_license_plate_data(license_plate, spot_id, confidence)
                
                # Draw on frame for display
                cv2.putText(frame, f"License: {license_plate}", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.putText(frame, f"Confidence: {confidence}%", (10, 70), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # Display frame (optional)
        cv2.imshow('License Plate Recognition', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        
        time.sleep(1)  # Process every second
    
    camera.release()
    cv2.destroyAllWindows()
    mqtt_client.loop_stop()
    mqtt_client.disconnect()

if __name__ == "__main__":
    main()
```

## 🚀 Cách Sử Dụng Hệ Thống

### 1. Khởi động hệ thống:

1. **Start MQTT Broker**:
   ```bash
   mosquitto -c mosquitto.conf
   ```

2. **Deploy ESP32**: Upload code lên các ESP32 tại mỗi vị trí đỗ xe

3. **Start Raspberry Pi Camera**: Chạy script Python cho nhận dạng biển số

4. **Open Web Interface**: Mở `login.html` trong trình duyệt

### 2. Quy trình đặt chỗ:

1. **Đăng nhập** vào hệ thống
2. **Chọn vị trí trống** trên sơ đồ bãi đỗ
3. **Nhập biển số xe** và xác nhận đặt chỗ
4. **Đỗ xe** tại vị trí đã đặt
5. **Hệ thống tự động** xác nhận qua camera

### 3. Giám sát real-time:

- **Dashboard** hiển thị trạng thái tất cả vị trí
- **Notifications** cho các sự kiện quan trọng
- **Activity log** theo dõi hoạt động
- **Statistics** thống kê sử dụng

## 📊 MQTT Topics

### Sensor Data (ESP32 → Web):
```
Topic: parking/sensors/{spot_id}
Payload: {
  "spot_id": 1,
  "occupied": true,
  "distance": 15,
  "timestamp": "2024-01-01T10:00:00Z",
  "sensor_type": "ultrasonic"
}
```

### License Plate Recognition (Pi → Web):
```
Topic: parking/camera/license_plate
Payload: {
  "license_plate": "29A-1234",
  "spot_id": 1,
  "confidence": 95,
  "timestamp": "2024-01-01T10:00:00Z",
  "camera_id": "cam_01"
}
```

### Reservations (Web → System):
```
Topic: parking/reservations/{spot_id}
Payload: {
  "user_id": 1,
  "license_plate": "29A-1234",
  "reserved_at": "2024-01-01T10:00:00Z"
}
```

## 🔍 Testing với Simulator

1. Mở `mqtt_simulator.html`
2. Kết nối tới MQTT broker
3. Mô phỏng các scenario:
   - Xe vào bãi
   - Xe rời bãi  
   - Biển số sai
   - Hoạt động ngẫu nhiên

## 🚨 Xử Lý Lỗi

### Trường hợp biển số không khớp:
1. Sensor phát hiện xe → Status: "processing"
2. Camera đọc biển số → So sánh với reservation
3. Nếu không khớp → Status: "processing" (màu vàng)
4. Cần can thiệp thủ công

### Kết nối MQTT bị mất:
1. Web hiển thị trạng thái "disconnected"
2. Tự động thử kết nối lại
3. Queue messages để gửi khi reconnect

## 📱 Responsive Design

- **Desktop**: Hiển thị đầy đủ 6 cột
- **Tablet**: 4 cột, điều chỉnh kích thước
- **Mobile**: 2 cột, layout tối ưu cho điện thoại

## 🔐 Bảo Mật

- **Authentication**: Session-based login
- **MQTT Security**: Username/password cho production
- **Data Validation**: Validate license plate format
- **XSS Protection**: Sanitize user inputs

## 🔄 Future Enhancements

- [ ] Payment integration
- [ ] Mobile app
- [ ] Advanced analytics
- [ ] Multiple camera angles
- [ ] Machine learning for better recognition
- [ ] Push notifications
- [ ] Admin dashboard
- [ ] Booking history
- [ ] User profiles
