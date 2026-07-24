import cv2

print("OpenCV Version:", cv2.__version__)

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

print("Camera Opened:", cap.isOpened())

ret, frame = cap.read()

print("Frame Read:", ret)

if ret:
    cv2.imshow("Camera Test", frame)
    cv2.waitKey(5000)

cap.release()
cv2.destroyAllWindows()
