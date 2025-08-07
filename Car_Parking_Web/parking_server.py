from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import sqlite3
import paho.mqtt.client as mqtt
from datetime import datetime
import threading
import json

# --- CẤU HÌNH ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'parking_secret_key'
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*")

MQTT_BROKER_IP = "192.168.72.170"
MQTT_PORT = 1883
DB_FILE = "parking_log.db"

MQTT_TOPIC_LICENSE_PLATE = "parking/entry/license_plate"
MQTT_TOPIC_SPOT_STATUS = "parking/spot/+/status"

# --- DATABASE SETUP ---
def setup_database():
    """Tạo database và các bảng cần thiết."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Bảng lịch sử check-in
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS checkins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                license_plate TEXT NOT NULL,
                checkin_time DATETIME NOT NULL
            )
        """)
        
        # Bảng trạng thái ô đỗ - Sửa lại cấu trúc
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS parking_spots (
                spot_id TEXT PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'empty',
                license_plate TEXT,
                reserved_by INTEGER,
                last_updated DATETIME NOT NULL
            )
        """)
        
        # Khởi tạo 5 ô đỗ xe mặc định
        for i in range(1, 6):
            cursor.execute("""
                INSERT OR IGNORE INTO parking_spots (spot_id, status, last_updated) 
                VALUES (?, 'empty', ?)
            """, (f'P{i}', datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        # Bảng đặt chỗ
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reservations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                spot_id TEXT NOT NULL,
                license_plate TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                reserved_at DATETIME NOT NULL,
                status TEXT DEFAULT 'active',
                FOREIGN KEY (spot_id) REFERENCES parking_spots (spot_id)
            )
        """)
        
        conn.commit()
        conn.close()
        print(f"✅ Database '{DB_FILE}' đã sẵn sàng với 5 ô đỗ xe")
    except Exception as e:
        print(f"❌ Lỗi database: {e}")

# --- MQTT CLIENT ---
mqtt_client = None

def on_connect(client, userdata, flags, rc, properties=None):
    """Callback kết nối MQTT."""
    if rc == 0:
        print("🔌 Kết nối MQTT thành công!")
        client.subscribe(MQTT_TOPIC_LICENSE_PLATE)
        client.subscribe(MQTT_TOPIC_SPOT_STATUS)
        
        # Emit trạng thái kết nối tới clients
        socketio.emit('mqtt_status', {'connected': True})
    else:
        print(f"❌ Lỗi kết nối MQTT: {rc}")
        socketio.emit('mqtt_status', {'connected': False})

def on_message(client, userdata, msg):
    """Callback nhận tin nhắn MQTT."""
    print(f"📬 Nhận tin nhắn: {msg.topic}")
    
    # Xử lý biển số xe
    if msg.topic == MQTT_TOPIC_LICENSE_PLATE:
        license_plate = msg.payload.decode('utf-8')
        checkin_time = datetime.now()
        
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO checkins (license_plate, checkin_time) VALUES (?, ?)", 
                         (license_plate, checkin_time.strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            conn.close()
            
            # Emit tới dashboard
            socketio.emit('license_plate_detected', {
                'license_plate': license_plate,
                'timestamp': checkin_time.isoformat()
            })
            
            print(f"✅ Lưu biển số: {license_plate}")
            
        except Exception as e:
            print(f"❌ Lỗi lưu biển số: {e}")
    
    # Xử lý trạng thái ô đỗ
    elif msg.topic.startswith("parking/spot/"):
        spot_id = msg.topic.split('/')[2]
        status = msg.payload.decode('utf-8')
        last_updated = datetime.now()
        
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE parking_spots 
                SET status = ?, last_updated = ? 
                WHERE spot_id = ?
            """, (status, last_updated.strftime("%Y-%m-%d %H:%M:%S"), spot_id))
            
            conn.commit()
            conn.close()
            
            # Emit tới dashboard
            socketio.emit('spot_status_update', {
                'spot_id': spot_id,
                'status': status,
                'timestamp': last_updated.isoformat()
            })
            
            print(f"✅ Cập nhật ô {spot_id}: {status}")
            
        except Exception as e:
            print(f"❌ Lỗi cập nhật ô đỗ: {e}")

def setup_mqtt():
    """Thiết lập kết nối MQTT."""
    global mqtt_client
    try:
        mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, "parking_server")
        mqtt_client.on_connect = on_connect
        mqtt_client.on_message = on_message
        
        # Thử kết nối MQTT, nếu không được thì skip
        try:
            mqtt_client.connect(MQTT_BROKER_IP, MQTT_PORT, 60)
            
            # Chạy MQTT loop trong thread riêng
            mqtt_thread = threading.Thread(target=mqtt_client.loop_forever)
            mqtt_thread.daemon = True
            mqtt_thread.start()
            print("✅ MQTT client đã khởi động")
        except:
            print("⚠️ Không thể kết nối MQTT broker - chạy ở chế độ offline")
            mqtt_client = None
        
    except Exception as e:
        print(f"❌ Lỗi thiết lập MQTT: {e}")
        mqtt_client = None

# --- API ENDPOINTS ---

@app.route('/api/spots', methods=['GET'])
def get_parking_spots():
    """Lấy danh sách tất cả ô đỗ."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT spot_id, status, license_plate, reserved_by, last_updated FROM parking_spots")
        spots = cursor.fetchall()
        conn.close()
        
        result = []
        for spot in spots:
            result.append({
                'spot_id': spot[0],
                'status': spot[1],
                'license_plate': spot[2],
                'reserved_by': spot[3],
                'last_updated': spot[4]
            })
            
        return jsonify({'success': True, 'spots': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/reserve', methods=['POST'])
def make_reservation():
    """Đặt chỗ đỗ xe."""
    try:
        data = request.json
        spot_id = data.get('spot_id')
        license_plate = data.get('license_plate')
        user_id = data.get('user_id', 1)
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Kiểm tra ô đỗ có trống không
        cursor.execute("SELECT status FROM parking_spots WHERE spot_id = ?", (spot_id,))
        result = cursor.fetchone()
        
        if not result or result[0] != 'empty':
            conn.close()
            return jsonify({'success': False, 'error': 'Ô đỗ không khả dụng'})
        
        # Tạo đặt chỗ
        reserved_at = datetime.now()
        cursor.execute("""
            INSERT INTO reservations (spot_id, license_plate, user_id, reserved_at) 
            VALUES (?, ?, ?, ?)
        """, (spot_id, license_plate, user_id, reserved_at.strftime("%Y-%m-%d %H:%M:%S")))
        
        # Cập nhật trạng thái ô đỗ
        cursor.execute("""
            UPDATE parking_spots 
            SET status = 'reserved', license_plate = ?, reserved_by = ?, last_updated = ? 
            WHERE spot_id = ?
        """, (license_plate, user_id, reserved_at.strftime("%Y-%m-%d %H:%M:%S"), spot_id))
        
        conn.commit()
        conn.close()
        
        # Emit tới tất cả clients
        socketio.emit('reservation_made', {
            'spot_id': spot_id,
            'license_plate': license_plate,
            'user_id': user_id,
            'timestamp': reserved_at.isoformat()
        })
        
        return jsonify({'success': True, 'message': 'Đặt chỗ thành công'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/cancel-reservation', methods=['POST'])
def cancel_reservation():
    """Hủy đặt chỗ."""
    try:
        data = request.json
        spot_id = data.get('spot_id')
        user_id = data.get('user_id', 1)
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Kiểm tra quyền hủy đặt chỗ
        cursor.execute("SELECT reserved_by FROM parking_spots WHERE spot_id = ?", (spot_id,))
        result = cursor.fetchone()
        
        if not result or result[0] != user_id:
            conn.close()
            return jsonify({'success': False, 'error': 'Không có quyền hủy đặt chỗ này'})
        
        # Cập nhật trạng thái
        now = datetime.now()
        cursor.execute("""
            UPDATE parking_spots 
            SET status = 'empty', license_plate = NULL, reserved_by = NULL, last_updated = ?
            WHERE spot_id = ?
        """, (now.strftime("%Y-%m-%d %H:%M:%S"), spot_id))
        
        # Cập nhật bảng reservations
        cursor.execute("""
            UPDATE reservations 
            SET status = 'cancelled' 
            WHERE spot_id = ? AND user_id = ? AND status = 'active'
        """, (spot_id, user_id))
        
        conn.commit()
        conn.close()
        
        # Emit tới clients
        socketio.emit('reservation_cancelled', {
            'spot_id': spot_id,
            'user_id': user_id,
            'timestamp': now.isoformat()
        })
        
        return jsonify({'success': True, 'message': 'Hủy đặt chỗ thành công'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/checkins', methods=['GET'])
def get_checkins():
    """Lấy lịch sử check-in."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT license_plate, checkin_time FROM checkins ORDER BY checkin_time DESC LIMIT 10")
        checkins = cursor.fetchall()
        conn.close()
        
        result = []
        for checkin in checkins:
            result.append({
                'license_plate': checkin[0],
                'checkin_time': checkin[1]
            })
            
        return jsonify({'success': True, 'checkins': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# --- SOCKETIO EVENTS ---

@socketio.on('connect')
def handle_connect():
    """Client kết nối."""
    print('🔌 Client đã kết nối')
    emit('mqtt_status', {'connected': mqtt_client is not None})

@socketio.on('disconnect')
def handle_disconnect():
    """Client ngắt kết nối."""
    print('❌ Client đã ngắt kết nối')

@socketio.on('request_spots_update')
def handle_spots_request():
    """Client yêu cầu cập nhật trạng thái ô đỗ."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT spot_id, status, license_plate, reserved_by, last_updated FROM parking_spots")
        spots = cursor.fetchall()
        conn.close()
        
        spots_data = []
        for spot in spots:
            spots_data.append({
                'spot_id': spot[0],
                'status': spot[1],
                'license_plate': spot[2],
                'reserved_by': spot[3],
                'last_updated': spot[4]
            })
            
        emit('spots_update', {'spots': spots_data})
    except Exception as e:
        emit('error', {'message': str(e)})
@socketio.on('simulate_license_detection')
def handle_simulate_license_detection(data):
    """Giả lập phát hiện biển số từ camera."""
    license_plate = data.get('license_plate')
    
    if not license_plate:
        return
    
    # Tìm ô đỗ có đặt chỗ với biển số này
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT spot_id, status, reserved_by FROM parking_spots 
            WHERE license_plate = ? AND status IN ('reserved', 'occupied')
        """, (license_plate,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            spot_id, current_status, reserved_by = result
            
            if current_status == 'reserved':
                # Xác nhận đặt chỗ - chuyển thành occupied
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                now = datetime.now()
                
                cursor.execute("""
                    UPDATE parking_spots 
                    SET status = 'occupied', last_updated = ?
                    WHERE spot_id = ?
                """, (now.strftime("%Y-%m-%d %H:%M:%S"), spot_id))
                
                conn.commit()
                conn.close()
                
                # Emit xác nhận
                socketio.emit('reservation_confirmed', {
                    'spot_id': spot_id,
                    'license_plate': license_plate,
                    'user_id': reserved_by,
                    'timestamp': now.isoformat()
                })
                
                emit('license_plate_detected', {
                    'license_plate': license_plate,
                    'timestamp': now.isoformat(),
                    'status': 'confirmed',
                    'spot_id': spot_id
                })
                
                print(f"✅ Xác nhận xe {license_plate} tại {spot_id}")
            else:
                # Xe đã ở trong bãi
                emit('license_plate_detected', {
                    'license_plate': license_plate,
                    'timestamp': datetime.now().isoformat(),
                    'status': 'already_parked',
                    'spot_id': spot_id
                })
        else:
            # Biển số không có đặt chỗ
            emit('license_plate_detected', {
                'license_plate': license_plate,
                'timestamp': datetime.now().isoformat(),
                'status': 'unauthorized'
            })
            
            print(f"⚠️ Xe {license_plate} không có đặt chỗ")
            
    except Exception as e:
        print(f"❌ Lỗi xử lý phát hiện biển số: {e}")
        emit('error', {'message': str(e)})
# --- DEMO ENDPOINTS (Để test khi không có MQTT) ---

@app.route('/api/demo/car-enter', methods=['POST'])
def demo_car_enter():
    """Demo: Xe vào bãi."""
    try:
        data = request.json
        spot_id = data.get('spot_id', 'P1')
        license_plate = data.get('license_plate', '29A-1234')
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        now = datetime.now()
        
        cursor.execute("""
            UPDATE parking_spots 
            SET status = 'occupied', license_plate = ?, last_updated = ?
            WHERE spot_id = ?
        """, (license_plate, now.strftime("%Y-%m-%d %H:%M:%S"), spot_id))
        
        conn.commit()
        conn.close()
        
        # Emit event
        socketio.emit('spot_status_update', {
            'spot_id': spot_id,
            'status': 'occupied',
            'license_plate': license_plate,
            'timestamp': now.isoformat()
        })
        
        return jsonify({'success': True, 'message': f'Xe {license_plate} vào {spot_id}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/demo/car-exit', methods=['POST'])
def demo_car_exit():
    """Demo: Xe rời bãi."""
    try:
        data = request.json
        spot_id = data.get('spot_id', 'P1')
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        now = datetime.now()
        
        cursor.execute("""
            UPDATE parking_spots 
            SET status = 'empty', license_plate = NULL, reserved_by = NULL, last_updated = ?
            WHERE spot_id = ?
        """, (now.strftime("%Y-%m-%d %H:%M:%S"), spot_id))
        
        conn.commit()
        conn.close()
        
        # Emit event
        socketio.emit('spot_status_update', {
            'spot_id': spot_id,
            'status': 'empty',
            'timestamp': now.isoformat()
        })
        
        return jsonify({'success': True, 'message': f'Xe rời khỏi {spot_id}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# --- MAIN ---
if __name__ == '__main__':
    print("🚀 Khởi động Parking Server...")
    setup_database()
    setup_mqtt()
    print("✅ Server sẵn sàng tại http://localhost:5000")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)