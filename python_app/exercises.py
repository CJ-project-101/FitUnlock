import cv2
import time
import sys
import os

sys.path.append(os.path.dirname(__file__))
from pose_detector import PoseDetector, Joint


# ── Minutes earned per activity ──────────────────────────────────────────────
REWARDS = {
    "squats":        {"reps": 10, "minutes": 15},
    "jumping_jacks": {"reps": 15, "minutes": 20},
    "push_ups":      {"reps": 8,  "minutes": 20},
    "arm_raises":    {"reps": 12, "minutes": 10},
}


# ── Shared overlay helper ─────────────────────────────────────────────────────
def draw_hud(frame, exercise_name, count, target, stage, angle_text=""):
    """Draws the status panel on top of the camera frame."""
    h, w = frame.shape[:2]

    # Dark semi-transparent top bar
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 130), (20, 20, 20), -1)
    frame = cv2.addWeighted(overlay, 0.6, frame, 0.4, 0)

    # Exercise name
    cv2.putText(frame, exercise_name.upper().replace("_", " "),
                (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 200, 0), 2)

    # Rep counter  e.g.  "Reps: 4 / 10"
    cv2.putText(frame, f"Reps: {count} / {target}",
                (20, 75), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)

    # Stage bubble  (UP / DOWN)
    stage_color = (0, 255, 0) if stage == "up" else (0, 165, 255)
    cv2.putText(frame, f"Stage: {stage.upper() if stage else '---'}",
                (20, 115), cv2.FONT_HERSHEY_SIMPLEX, 0.8, stage_color, 2)

    # Optional angle readout (bottom-left)
    if angle_text:
        cv2.putText(frame, angle_text,
                    (20, h - 20), cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, (180, 180, 180), 1)

    # Progress bar (bottom of screen)
    bar_w = int(w * (count / target))
    cv2.rectangle(frame, (0, h - 10), (w, h), (50, 50, 50), -1)
    cv2.rectangle(frame, (0, h - 10), (bar_w, h), (0, 200, 100), -1)

    return frame


# ─────────────────────────────────────────────────────────────────────────────
#  1. SQUATS
#  Calibrated to Calvin's readings:
#    standing  → knee angle ~178°   (threshold > 155  = "up")
#    squatted  → knee angle ~62.9°  (threshold < 110  = "down")
# ─────────────────────────────────────────────────────────────────────────────
def run_squats():
    TARGET   = REWARDS["squats"]["reps"]
    cap      = cv2.VideoCapture(0)
    detector = PoseDetector()
    count    = 0
    stage    = None          # "up" or "down"

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    print(f"\n[SQUATS] Target: {TARGET} reps.  Press Q to quit early.\n")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame    = cv2.flip(frame, 1)
        frame    = detector.process_frame(frame)
        angle_txt = ""

        if detector.is_person_detected():
            knee_angle = detector.get_angle(
                Joint.LEFT_HIP, Joint.LEFT_KNEE, Joint.LEFT_ANKLE
            )

            if knee_angle is not None:
                angle_txt = f"Knee angle: {knee_angle:.1f} deg"

            # ── State machine ──────────────────────────────────────────
                if knee_angle > 160:
                    stage = "up"
                elif knee_angle < 100 and stage == "up":
                    stage = "down"
                    count += 1
                    print(f"  Squat rep {count} ✓")

        frame = draw_hud(frame, "Squats", count, TARGET, stage or "---", angle_txt)

        # ── Completion flash ───────────────────────────────────────────────
        if count >= TARGET:
            cv2.putText(frame, "DONE! Great work!",
                        (100, 260), cv2.FONT_HERSHEY_SIMPLEX,
                        2.0, (0, 255, 0), 4)
            cv2.imshow("FitPlay — Squats", frame)
            cv2.waitKey(2000)
            break

        cv2.imshow("FitPlay — Squats", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    detector.close()
    cap.release()
    cv2.destroyAllWindows()

    success = count >= TARGET
    return success, count


# ─────────────────────────────────────────────────────────────────────────────
#  2. JUMPING JACKS
#  Detection: wrist rises ABOVE shoulder = arms up
#             wrist falls BELOW shoulder = arms down
#  (y-axis is flipped in image: smaller y = higher on screen)
# ─────────────────────────────────────────────────────────────────────────────
def run_jumping_jacks():
    TARGET   = REWARDS["jumping_jacks"]["reps"]
    cap      = cv2.VideoCapture(0)
    detector = PoseDetector()
    count    = 0
    stage    = None

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    print(f"\n[JUMPING JACKS] Target: {TARGET} reps.  Press Q to quit early.\n")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame    = cv2.flip(frame, 1)
        frame    = detector.process_frame(frame)
        info_txt = ""

        if detector.is_person_detected():
            left_shoulder  = detector.get_landmark(Joint.LEFT_SHOULDER)
            left_wrist     = detector.get_landmark(Joint.LEFT_WRIST)
            left_hip       = detector.get_landmark(Joint.LEFT_HIP)
            right_hip      = detector.get_landmark(Joint.RIGHT_HIP)
            left_ankle     = detector.get_landmark(Joint.LEFT_ANKLE)
            right_ankle    = detector.get_landmark(Joint.RIGHT_ANKLE)

            if all([left_shoulder, left_wrist,
                    left_hip, right_hip,
                    left_ankle, right_ankle]):

                shoulder_y  = left_shoulder[1]
                wrist_y     = left_wrist[1]

                hip_width   = abs(right_hip[0]   - left_hip[0])
                ankle_width = abs(right_ankle[0] - left_ankle[0])

                # Arms up = wrist above shoulder
                # Legs out = ankles wider than hips by 20%
                arms_up   = wrist_y  < shoulder_y
                arms_down = wrist_y  > shoulder_y + 0.05
                legs_out  = ankle_width > hip_width * 1.2
                legs_in   = ankle_width < hip_width * 1.1

                # Both arms AND legs must match for a valid jumping jack
                fully_open   = arms_up   and legs_out
                fully_closed = arms_down and legs_in

                info_txt = (f"Arms: {'UP' if arms_up else 'down'}  |  "
                            f"Legs: {'OUT' if legs_out else 'in'}  |  "
                            f"Reps: {count}")

                if fully_closed:
                    stage = "down"
                elif fully_open and stage == "down":
                    stage = "up"
                    count += 1
                    print(f"  Jumping jack rep {count} ✓")

        frame = draw_hud(frame, "Jumping Jacks", count, TARGET, stage or "---", info_txt)

        if count >= TARGET:
            cv2.putText(frame, "DONE! Great work!",
                        (100, 260), cv2.FONT_HERSHEY_SIMPLEX,
                        2.0, (0, 255, 0), 4)
            cv2.imshow("FitPlay — Jumping Jacks", frame)
            cv2.waitKey(2000)
            break

        cv2.imshow("FitPlay — Jumping Jacks", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    detector.close()
    cap.release()
    cv2.destroyAllWindows()

    success = count >= TARGET
    return success, count


# ─────────────────────────────────────────────────────────────────────────────
#  3. PUSH-UPS
#  Uses elbow angle:
#    arms straight (up position)  → angle > 155°
#    chest near floor (down)      → angle < 90°
# ─────────────────────────────────────────────────────────────────────────────
def run_push_ups():
    TARGET   = REWARDS["push_ups"]["reps"]
    cap      = cv2.VideoCapture(0)
    detector = PoseDetector()
    count    = 0
    stage    = None

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    print(f"\n[PUSH-UPS] Target: {TARGET} reps.  Lie sideways to camera.")
    print("Press Q to quit early.\n")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame    = cv2.flip(frame, 1)
        frame    = detector.process_frame(frame)
        angle_txt = ""

        if detector.is_person_detected():
            elbow_angle = detector.get_angle(
                Joint.LEFT_SHOULDER, Joint.LEFT_ELBOW, Joint.LEFT_WRIST
            )

            if elbow_angle is not None:
                angle_txt = f"Elbow angle: {elbow_angle:.1f} deg"

                if elbow_angle > 155:
                    stage = "up"
                elif elbow_angle < 90 and stage == "up":
                    stage = "down"
                    count += 1
                    print(f"  Push-up rep {count} ✓")

        frame = draw_hud(frame, "Push-Ups", count, TARGET, stage or "---", angle_txt)

        if count >= TARGET:
            cv2.putText(frame, "DONE! Great work!",
                        (100, 260), cv2.FONT_HERSHEY_SIMPLEX,
                        2.0, (0, 255, 0), 4)
            cv2.imshow("FitPlay — Push-Ups", frame)
            cv2.waitKey(2000)
            break

        cv2.imshow("FitPlay — Push-Ups", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    detector.close()
    cap.release()
    cv2.destroyAllWindows()

    success = count >= TARGET
    return success, count


# ─────────────────────────────────────────────────────────────────────────────
#  4. WALKING  (timed — no webcam needed)
# ─────────────────────────────────────────────────────────────────────────────
def run_walking(target_minutes=5):
    print(f"\n[WALKING] Walk for at least {target_minutes} minutes.")
    print("Press ENTER to START your walk...")
    input()

    start = time.time()

    print("Go! Walk around. Press ENTER when you're back...")
    input()

    elapsed_minutes = (time.time() - start) / 60
    print(f"\nYou walked for {elapsed_minutes:.1f} minutes!")

    if elapsed_minutes >= target_minutes:
        earned = int(elapsed_minutes * 6)   # 1 min walk → 6 min play
        print(f"Earned: {earned} minutes of playtime!")
        return True, earned
    else:
        print(f"Need {target_minutes} min. You only walked {elapsed_minutes:.1f} min.")
        return False, 0


# ─────────────────────────────────────────────────────────────────────────────
#  Quick test — run this file directly to test each exercise
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Which exercise to test?")
    print("1. Squats")
    print("2. Jumping Jacks")
    print("3. Push-Ups")
    print("4. Walking")
    choice = input("Enter 1-4: ").strip()

    if choice == "1":
        ok, reps = run_squats()
        print(f"\nResult: {'SUCCESS' if ok else 'incomplete'} — {reps} reps done")
    elif choice == "2":
        ok, reps = run_jumping_jacks()
        print(f"\nResult: {'SUCCESS' if ok else 'incomplete'} — {reps} reps done")
    elif choice == "3":
        ok, reps = run_push_ups()
        print(f"\nResult: {'SUCCESS' if ok else 'incomplete'} — {reps} reps done")
    elif choice == "4":
        ok, earned = run_walking()
        print(f"\nResult: {'SUCCESS' if ok else 'incomplete'} — {earned} min earned")
    else:
        print("Invalid choice")
