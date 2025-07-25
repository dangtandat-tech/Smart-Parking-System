from ultralytics import YOLO
import cv2
import easyocr
import re
import warnings
import numpy as np
import matplotlib.pyplot as plt
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
    letter_to_num = {'S':'3', 'U':'0', '7': '1'}

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

reader = easyocr.Reader(['en', 'vi'])
model = YOLO('best.pt')
results = model('test/test7.jpg')

for r in results:
    print(f"Detected {len(r.boxes)} objects")
    img = r.orig_img
    annotated_img = r.plot()
    cv2.imwrite('results/result_annotated.jpg', annotated_img)
    print("Kết quả đã được lưu vào 'results/result_annotated.jpg'")

    if r.boxes is not None:
        for i, box in enumerate(r.boxes):
            confidence = box.conf.item()
            class_id = int(box.cls.item())
            bbox = box.xyxy[0].tolist()
            print(f"Object {i+1}: Class {class_id}, Confidence: {confidence:.2f}, BBox: {bbox}")
            
            x1, y1, x2, y2 = map(int, bbox)
            cropped_img = img[y1:y2, x1:x2]
            crop_filename = f'results/anh_da_ocr_{i+1}.jpg'
            cv2.imwrite(crop_filename, cropped_img)
            print(f"Đã lưu biển số crop vào '{crop_filename}'")
            # Có thể thêm các bước tiền xử lý ảnh ở đây nếu cần
            # license_plate_crop_gray = cv2.cvtColor(cropped_img, cv2.COLOR_BGR2GRAY)
            # _, license_plate_crop_thresh = cv2.threshold(license_plate_crop_gray, 64, 255, cv2.THRESH_BINARY_INV)
            # crop_filename_thresh = f'results/anh_da_ocr_thresh_{i+1}.jpg'
            # cv2.imwrite(crop_filename_thresh, license_plate_crop_thresh)
            # print(f"Đã lưu biển số crop (đã xử lý) vào '{crop_filename_thresh}'")
            # OCR cả vùng crop (có thể là 2 hàng)
            results_ocr = reader.readtext(
                cropped_img,
                allowlist='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ',
                paragraph=False
            )

            if results_ocr:
                # Sắp xếp kết quả theo thứ tự từ trên xuống (theo y1)
                results_ocr.sort(key=lambda x: x[0][0][1])  # x[0] là bbox, x[0][0][1] là y1
                merged_text = ' '.join([text[1] for text in results_ocr])
                print(f"Raw OCR text: '{merged_text}'")
                # Sửa biển số theo chuẩn VN
                clean_text = fix_vn_plate(merged_text)
                print(f"Cleaned text: '{clean_text}'")
                best_confidence = sum([text[2] for text in results_ocr]) / len(results_ocr)
                print(f"Biển số detected: '{clean_text}' (conf: {best_confidence:.2f})")
            else:
                print("Không đọc được text từ biển số lần 1")