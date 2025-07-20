import cv2

print("--- Bat dau kiem tra ---")

# Thử mở camera ở index 0
cap = cv2.VideoCapture(0)

# Kiểm tra xem camera có thực sự mở được không
if not cap.isOpened():
    print("LOI: Khong the mo camera!")
else:
    print("THANH CONG: Camera da mo duoc.")
    
    # Thử đọc một khung hình
    ret, frame = cap.read()
    
    if ret:
        print("THANH CONG: Da doc duoc mot khung hinh.")
        
        # Thử hiển thị khung hình trong một cửa sổ
        cv2.imshow("Test Camera", frame)
        print("Dang hien thi cua so. Nhan phim bat ky de thoat.")
        cv2.waitKey(0) # Đợi người dùng nhấn một phím bất kỳ
    else:
        print("LOI: Khong the doc khung hinh tu camera!")

# Giải phóng tài nguyên
cap.release()
cv2.destroyAllWindows()
print("--- Da kiem tra xong ---")
