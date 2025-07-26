from ultralytics import YOLO
import cv2
import easyocr
import re
import warnings
import numpy as np
import time
import PIL
from PIL import Image

# Sửa lỗi cho Pillow >= 10.0.0 không còn ANTIALIAS
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS

# Bỏ các warning không cần thiết
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", message=".*pin_memory.*")
warnings.filterwarnings("ignore", message=".*CUDA.*")
warnings.filterwarnings("ignore", message=".*MPS.*")

def fix_vn_plate(text):
    """
    - Nếu ký tự 1 hoặc 2 là letter (OCR nhầm số thành chữ), chuyển ngược thành số.
    - Nếu ký tự 3 là số (OCR nhầm số thành chữ), chuyển thành letter theo chuẩn VN.
    """
    # map số → chữ ở vị trí thứ 3
    num_to_letter = {'4':'A','0':'O','1':'I','5':'S','7':'T', 'R': 'A'}
    # map chữ → số cho hai vị trí đầu
    letter_to_num = {'S':'3', 'U':'0', 'J':'3', '7': '1'}

    def repl(m):
        d1, d2, d3 = m.group(1), m.group(2), m.group(3)
        # 1) nếu d1 là letter thì map về số
        if d1.isalpha():
            d1 = letter_to_num.get(d1, d1)
        # 2) nếu d2 là letter thì map về số
        if d2.isalpha():
            d2 = letter_to_num.get(d2, d2)
        # 3) nếu d3 là số thì map → letter
        if d3.isdigit():
            d3 = num_to_letter.get(d3, d3)
        else:
            d3 = num_to_letter.get(d3, d3)
        return d1 + d2 + d3

    # bắt 3 ký tự đầu bất kỳ, phần rest giữ nguyên
    return re.sub(r'^(.)(.)(.)', repl, text, count=1)

def process_frame(frame, model, reader):
    # Dự đoán với YOLOv8
    results = model(frame)
    
    # Kết quả cuối cùng
    detected_plates = []
    
    # Biến để vẽ lên frame gốc
    annotated_frame = frame.copy()
    
    for r in results:
        if r.boxes is not None:
            for i, box in enumerate(r.boxes):
                confidence = box.conf.item()
                class_id = int(box.cls.item())
                bbox = box.xyxy[0].tolist()
                
                # Lấy tọa độ bounding box
                x1, y1, x2, y2 = map(int, bbox)
                
                # Crop biển số
                cropped_img = frame[y1:y2, x1:x2]
                if cropped_img.size == 0:
                    continue
                    
                # Tiền xử lý
                try:
                    license_plate_crop_gray = cv2.cvtColor(cropped_img, cv2.COLOR_BGR2GRAY)
                    _, license_plate_crop_thresh = cv2.threshold(license_plate_crop_gray, 64, 255, cv2.THRESH_BINARY_INV)
                    
                    # OCR
                    results_ocr = reader.readtext(
                        license_plate_crop_thresh,
                        allowlist='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ',
                        paragraph=False
                    )
                    
                    if results_ocr:
                        # Sắp xếp kết quả theo thứ tự từ trên xuống
                        results_ocr.sort(key=lambda x: x[0][0][1])
                        merged_text = ' '.join([text[1] for text in results_ocr])
                        
                        # Sửa biển số theo chuẩn VN
                        clean_text = fix_vn_plate(merged_text)
                        
                        # Thêm vào danh sách kết quả
                        detected_plates.append({
                            'text': clean_text,
                            'bbox': (x1, y1, x2, y2),
                            'confidence': confidence
                        })
                        
                        # Vẽ bounding box lên frame gốc
                        cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        
                        # Hiển thị text phía trên biển số
                        cv2.putText(annotated_frame, clean_text, (x1, y1-10), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                except Exception as e:
                    print(f"Lỗi xử lý biển số: {e}")
                    continue
    
    return annotated_frame, detected_plates

def main():
    # Khởi tạo camera
    # 0 là camera mặc định, có thể thay đổi tùy theo setup
    cap = cv2.VideoCapture(0)
    
    # Thiết lập độ phân giải (tùy theo camera)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    # Tải model
    print("Đang tải model YOLO và EasyOCR...")
    model = YOLO('best.pt')
    reader = easyocr.Reader(['en', 'vi'], gpu=False)  # Không dùng GPU trên Raspberry Pi
    print("Đã tải xong model!")
    
    # Biến đếm frames để không xử lý mọi frame (tiết kiệm tài nguyên)
    frame_count = 0
    
    # Lưu kết quả nhận dạng gần nhất
    last_detected_plates = []
    
    print("Bắt đầu xử lý video. Nhấn 'q' để thoát.")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Không thể đọc từ camera")
            break
        
        # Hiển thị frame gốc
        display_frame = frame.copy()
        
        # Chỉ xử lý mỗi 10 frame để tiết kiệm tài nguyên
        if frame_count % 10 == 0:
            # Xử lý frame
            annotated_frame, detected_plates = process_frame(frame, model, reader)
            
            # Cập nhật kết quả nếu tìm thấy biển số
            if detected_plates:
                last_detected_plates = detected_plates
            
            # Dùng frame đã annotate để hiển thị
            display_frame = annotated_frame
        
        # Vẽ kết quả nhận dạng gần nhất lên frame hiện tại
        for plate in last_detected_plates:
            x1, y1, x2, y2 = plate['bbox']
            cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(display_frame, plate['text'], (x1, y1-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
        
        # Hiển thị FPS
        cv2.putText(display_frame, f"Frame: {frame_count}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # Hiển thị frame
        cv2.imshow('License Plate Detection', display_frame)
        
        # Tăng biến đếm frame
        frame_count += 1
        
        # Nhấn 'q' để thoát
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    # Giải phóng tài nguyên
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()