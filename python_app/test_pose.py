import cv2
import sys
import os

# So Python can find pose_detector.py
sys.path.append(os.path.dirname(__file__))

from pose_detector import PoseDetector, Joint


def test_pose():
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    detector = PoseDetector()

    print("Pose detector running!")
    print("Stand in front of camera. Do a slow squat and watch the angle change.")
    print("Press Q to quit.\n")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)          # mirror so it feels natural
        frame = detector.process_frame(frame)

        if detector.is_person_detected():

            # ── Squat angle (left knee) ──────────────────────────────────────
            knee_angle = detector.get_angle(
                Joint.LEFT_HIP,
                Joint.LEFT_KNEE,
                Joint.LEFT_ANKLE
            )

            # ── Arm angle (left arm — for jumping jacks) ─────────────────────
            arm_angle = detector.get_angle(
                Joint.LEFT_SHOULDER,
                Joint.LEFT_ELBOW,
                Joint.LEFT_WRIST
            )

            # ── Display on screen ─────────────────────────────────────────────
            if knee_angle is not None:
                color = (0, 255, 0) if knee_angle > 150 else (0, 165, 255)
                cv2.putText(frame,
                            f"Knee angle: {knee_angle:.1f} deg",
                            (20, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

            if arm_angle is not None:
                cv2.putText(frame,
                            f"Arm angle:  {arm_angle:.1f} deg",
                            (20, 90),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 200, 0), 2)

            cv2.putText(frame, "Person detected",
                        (20, 440), cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, (0, 255, 0), 2)
        else:
            cv2.putText(frame, "No person detected — move closer",
                        (20, 440), cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, (0, 0, 255), 2)

        cv2.imshow("FitPlay — Pose Test", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    detector.close()
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    test_pose()