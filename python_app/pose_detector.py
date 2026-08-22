import cv2
import mediapipe as mp
import numpy as np


# ── MediaPipe setup ──────────────────────────────────────────────────────────
mp_pose    = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
mp_styles  = mp.solutions.drawing_styles


# ── Landmark index constants (so you never have to remember numbers) ─────────
class Joint:
    NOSE           = 0
    LEFT_SHOULDER  = 11
    RIGHT_SHOULDER = 12
    LEFT_ELBOW     = 13
    RIGHT_ELBOW    = 14
    LEFT_WRIST     = 15
    RIGHT_WRIST    = 16
    LEFT_HIP       = 23
    RIGHT_HIP      = 24
    LEFT_KNEE      = 25
    RIGHT_KNEE     = 26
    LEFT_ANKLE     = 27
    RIGHT_ANKLE    = 28


# ── Core angle calculator ─────────────────────────────────────────────────────
def calculate_angle(a, b, c):
    """
    Returns the angle IN DEGREES at point b, formed by the line a->b->c.

    Example: to get knee angle during a squat:
        a = hip, b = knee, c = ankle
        angle ~170° when standing, ~80° when fully squatted
    """
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)

    ba = a - b
    bc = c - b

    cosine = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
    angle  = np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0)))

    return round(angle, 2)


# ── Helper: extract [x, y] from a landmark ───────────────────────────────────
def get_point(landmarks, index):
    lm = landmarks[index]
    return [lm.x, lm.y]


# ── Helper: check if a landmark is visible enough to trust ───────────────────
def is_visible(landmarks, index, threshold=0.3):
    return landmarks[index].visibility > threshold


# ── Main PoseDetector class ───────────────────────────────────────────────────
class PoseDetector:
    """
    Wraps MediaPipe Pose. Open once, call process_frame() in a loop.
    """

    def __init__(self):
        self.pose = mp_pose.Pose(
            static_image_mode        = False,   # False = video mode (faster)
            model_complexity         = 1,       # 0=fast, 1=balanced, 2=accurate
            smooth_landmarks         = True,    # reduces jitter
            min_detection_confidence = 0.6,
            min_tracking_confidence  = 0.6,
        )
        self.landmarks = None   # updated every frame
        self.results   = None

    def process_frame(self, frame):
        """
        Feed in a BGR frame from OpenCV.
        Returns the annotated frame with skeleton drawn on it.
        """
        # MediaPipe needs RGB
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False          # tiny speed boost

        self.results = self.pose.process(rgb)

        rgb.flags.writeable = True
        frame = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

        if self.results.pose_landmarks:
            self.landmarks = self.results.pose_landmarks.landmark

            # Draw the skeleton on the frame
            mp_drawing.draw_landmarks(
                frame,
                self.results.pose_landmarks,
                mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec = mp_styles.get_default_pose_landmarks_style(),
            )
        else:
            self.landmarks = None  # no person detected

        return frame

    def get_angle(self, a_index, b_index, c_index):
        """
        Get the joint angle between three landmark indices.
        Returns None if any landmark is not visible.
        """
        if self.landmarks is None:
            return None

        if not all(is_visible(self.landmarks, i)
                   for i in [a_index, b_index, c_index]):
            return None

        a = get_point(self.landmarks, a_index)
        b = get_point(self.landmarks, b_index)
        c = get_point(self.landmarks, c_index)

        return calculate_angle(a, b, c)

    def get_landmark(self, index):
        """Get [x, y] of a single landmark. Returns None if not visible."""
        if self.landmarks is None:
            return None
        if not is_visible(self.landmarks, index):
            return None
        return get_point(self.landmarks, index)

    def is_person_detected(self):
        return self.landmarks is not None

    def close(self):
        self.pose.close()