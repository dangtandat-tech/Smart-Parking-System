# Smart Parking System 🚗🅿️

## Giới thiệu

Smart Parking System là một dự án sử dụng công nghệ Internet of Things (IoT) nhằm tối ưu hóa việc quản lý bãi đỗ xe tự động và hiệu quả hơn. Dự án này giúp người dùng dễ dàng tìm kiếm, đặt chỗ và giám sát tình trạng bãi đỗ xe theo thời gian thực, đồng thời hỗ trợ quản lý bãi xe một cách thông minh và tiết kiệm chi phí.

## Tính năng chính

- **Giám sát trạng thái chỗ đỗ xe theo thời gian thực**  
  Sử dụng cảm biến và thiết bị IoT để nhận biết vị trí còn trống và đã được sử dụng trong bãi đỗ.

- **Tìm kiếm và đặt chỗ đỗ xe tự động**  
  Ứng dụng cho phép người dùng tìm kiếm và đặt trước chỗ đỗ xe qua giao diện web/mobile.

- **Quản lý phương tiện ra vào**  
  Tích hợp hệ thống nhận diện biển số xe (LPR) để tự động ghi nhận phương tiện ra/vào bãi đỗ.

- **Thống kê & báo cáo**  
  Hỗ trợ quản lý bãi đỗ xe với các báo cáo sử dụng, doanh thu, và tình trạng hoạt động.

## Kiến trúc hệ thống

- **Thiết bị IoT**: Cảm biến nhận diện chỗ trống, camera nhận diện biển số, bộ điều khiển trung tâm.
- **Backend**: Server xử lý dữ liệu, API giao tiếp với thiết bị IoT và ứng dụng khách.
- **Frontend**: Giao diện web/mobile cho người dùng và quản trị viên.

## Công nghệ sử dụng

- **Ngôn ngữ lập trình**: Python, JavaScript (Node.js hoặc React)
- **Thiết bị IoT**: ESP8266/ESP32, cảm biến siêu âm, camera
- **Cơ sở dữ liệu**: MongoDB / MySQL / Firebase
- **Giao tiếp**: MQTT, HTTP/REST API

## Hướng dẫn cài đặt

1. **Clone repository:**
   ```bash
   git clone https://github.com/dangtandat-tech/Smart-Parking-System.git
   cd Smart-Parking-System
   ```

2. **Cài đặt các thư viện cần thiết cho backend và frontend (tham khảo README trong từng thư mục con nếu có).**

3. **Cấu hình kết nối thiết bị IoT, cơ sở dữ liệu và các thông số môi trường trong file `.env`.**

4. **Chạy ứng dụng:**
   - Backend:  
     ```bash
     cd backend
     npm install
     npm start
     ```
   - Frontend:  
     ```bash
     cd frontend
     npm install
     npm start
     ```

## Đóng góp

Chào mừng mọi đóng góp cho dự án! Vui lòng tạo Issue hoặc Pull Request để thảo luận và đóng góp.

## License

MIT License

---
