import cv2
import sys

def test_webcam():
    print("Opening webcam...")
    cap = cv2.VideoCapture(0)  # 0 = default webcam

    if not cap.isOpened():
        print("ERROR: Could not open webcam.")
        print("Try changing VideoCapture(0) to VideoCapture(1)")
        sys.exit()

    print("Webcam opened! Press Q to quit.")

    while True:
        ret, frame = cap.read()

        if not ret:
            print("ERROR: Can't read from webcam.")
            break

        # Flip frame so it acts like a mirror
        frame = cv2.flip(frame, 1)

        # Show resolution info on screen
        h, w, _ = frame.shape
        cv2.putText(frame, f"Resolution: {w}x{h}",
                    (20, 40), cv2.FONT_HERSHEY_SIMPLEX,
                    0.8, (0, 255, 0), 2)

        cv2.imshow("Webcam Test", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("Webcam test done.")

if __name__ == "__main__":
    test_webcam()