"""
FitPlay webcam liveness checks.

Uses ordered gesture challenges only:
1) Raise left hand
2) Raise right hand
3) Raise both hands
4) Stretch both arms sideways
5) Put both hands near the head
Then repeat the sequence.

No body-size/scale consistency check is used.
"""
import random
import time
from collections import namedtuple

import cv2
from pose_detector import Joint

RESPONSE_SECONDS = 8.0
HOLD_SECONDS = 0.8
MAX_ATTEMPTS = 2

REQUIRED_JOINTS = (
    "NOSE", "LEFT_SHOULDER", "RIGHT_SHOULDER",
    "LEFT_WRIST", "RIGHT_WRIST",
)

Challenge = namedtuple("Challenge", "key prompt test")
GESTURES = (
    Challenge(
        "left_up", "LIVENESS: Raise your LEFT hand",
        lambda p: p["LEFT_WRIST"][1] < p["LEFT_SHOULDER"][1] - 0.06,
    ),
    Challenge(
        "right_up", "LIVENESS: Raise your RIGHT hand",
        lambda p: p["RIGHT_WRIST"][1] < p["RIGHT_SHOULDER"][1] - 0.06,
    ),
    Challenge(
        "both_up", "LIVENESS: Raise BOTH hands above your shoulders",
        lambda p: p["LEFT_WRIST"][1] < p["LEFT_SHOULDER"][1] - 0.04
        and p["RIGHT_WRIST"][1] < p["RIGHT_SHOULDER"][1] - 0.04,
    ),
    Challenge(
        "t_pose", "LIVENESS: Stretch BOTH arms out sideways",
        lambda p: abs(p["LEFT_WRIST"][1] - p["LEFT_SHOULDER"][1]) < 0.12
        and abs(p["RIGHT_WRIST"][1] - p["RIGHT_SHOULDER"][1]) < 0.12
        and p["LEFT_WRIST"][0] < p["LEFT_SHOULDER"][0] - 0.10
        and p["RIGHT_WRIST"][0] > p["RIGHT_SHOULDER"][0] + 0.10,
    ),
    Challenge(
        "hands_head", "LIVENESS: Put BOTH hands near your head",
        lambda p: abs(p["LEFT_WRIST"][0] - p["NOSE"][0]) < 0.22
        and abs(p["RIGHT_WRIST"][0] - p["NOSE"][0]) < 0.22
        and abs(p["LEFT_WRIST"][1] - p["NOSE"][1]) < 0.24
        and abs(p["RIGHT_WRIST"][1] - p["NOSE"][1]) < 0.24,
    ),
)


def verify_joints():
    missing = [name for name in REQUIRED_JOINTS if not hasattr(Joint, name)]
    if missing:
        raise RuntimeError(
            "Pose detector is missing required Joint landmarks: "
            + ", ".join(missing)
        )


class LivenessGuard:
    """Ordered gesture challenges; no body-scale tracking."""

    def __init__(self, detector, target_reps, mid_check=True, intro=None,
                 rng=None, clock=None):
        self.detector = detector
        self.target_reps = max(1, int(target_reps))
        self.rng = rng or random
        self.clock = clock or time.monotonic
        self.intro = intro

        self.failed = False
        self.failure_reason = ""
        self.challenge_active = False
        self.passed = False
        self._resume_flag = False

        self._mid_check_enabled = bool(mid_check and self.target_reps >= 3)
        self._mid_done = not self._mid_check_enabled
        self._final_done = False
        self._mid_at = (
            self.rng.randint(1, max(1, self.target_reps - 1))
            if self._mid_check_enabled else None
        )

        self._challenge_index = 0
        self._challenge = None
        self._challenge_started = 0.0
        self._gesture_started = None
        self._attempts = 0
        self._awaiting_final_stand = bool(intro)
        self._is_final_challenge = False
        self._last_count = 0

    def _landmarks(self):
        points = {}
        for name in REQUIRED_JOINTS:
            try:
                point = self.detector.get_landmark(getattr(Joint, name))
            except (AttributeError, TypeError, ValueError):
                point = None
            if point is None or len(point) < 2:
                return None
            x, y = float(point[0]), float(point[1])
            if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
                return None
            points[name] = (x, y)
        return points

    def _start_challenge(self, final=False):
        self.challenge_active = True
        self._challenge = GESTURES[self._challenge_index % len(GESTURES)]
        self._challenge_index += 1
        self._challenge_started = self.clock()
        self._gesture_started = None
        self._attempts = 0
        self._is_final_challenge = final

    def _fail(self, reason):
        self.failed = True
        self.failure_reason = reason
        self.challenge_active = False
        self.passed = False

    def update(self, count):
        if self.failed or self.passed:
            return

        self._last_count = count
        person_detected = self.detector.is_person_detected()
        points = self._landmarks() if person_detected else None

        if self._awaiting_final_stand:
            if count >= self.target_reps:
                self._awaiting_final_stand = False
                self._start_challenge(final=True)
            return

        if not self.challenge_active:
            if self._mid_check_enabled and not self._mid_done and count >= self._mid_at:
                self._start_challenge(final=False)
            elif count >= self.target_reps and not self._final_done:
                self._start_challenge(final=True)
            elif count >= self.target_reps and self._mid_done and self._final_done:
                self.passed = True
            return

        if self.clock() - self._challenge_started > RESPONSE_SECONDS:
            self._attempts += 1
            if self._attempts >= MAX_ATTEMPTS:
                self._fail("Liveness challenge timed out. The set was rejected.")
            else:
                self._challenge_started = self.clock()
                self._gesture_started = None
            return

        if not person_detected or points is None:
            self._gesture_started = None
            return

        try:
            matched = bool(self._challenge.test(points))
        except (KeyError, TypeError, ValueError):
            matched = False

        if matched:
            if self._gesture_started is None:
                self._gesture_started = self.clock()
            elif self.clock() - self._gesture_started >= HOLD_SECONDS:
                self.challenge_active = False
                self._resume_flag = True
                if self._is_final_challenge:
                    self._final_done = True
                else:
                    self._mid_done = True
                self._challenge = None
                self._gesture_started = None
                self.passed = self._mid_done and self._final_done
        else:
            self._gesture_started = None

    def pop_resume_flag(self):
        value = self._resume_flag
        self._resume_flag = False
        return value

    def draw(self, frame):
        if self.intro and self._awaiting_final_stand and not self.failed:
            cv2.putText(frame, self.intro, (20, 225),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 200, 255), 2)

        if self.challenge_active and self._challenge:
            cv2.rectangle(frame, (10, 235), (frame.shape[1] - 10, 305),
                          (20, 20, 20), -1)
            cv2.putText(frame, self._challenge.prompt, (20, 265),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.56, (0, 255, 255), 2)
            remaining = max(
                0, int(RESPONSE_SECONDS - (self.clock() - self._challenge_started))
            )
            cv2.putText(frame, f"Hold gesture: {remaining}s", (20, 292),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

        if self.failed:
            cv2.putText(frame, self.failure_reason[:80], (20, 330),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 0, 255), 2)
        return frame
