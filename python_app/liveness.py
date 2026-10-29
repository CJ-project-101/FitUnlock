"""
FitPlay webcam liveness check - random mid-set body-turn challenges.

At random reps DURING the set (never at the end) the user is asked to show a
DIFFERENT side of their body:
  facing the camera  -> randomly asked to turn to the LEFT or RIGHT side
  showing left side  -> asked to show the RIGHT side
  showing right side -> asked to show the LEFT side
After each turn the exercise continues on the new side (see guard.working_side).
A pre-recorded video cannot react to a random request.
"""
import math
import random
import time

import cv2
from pose_detector import Joint

RESPONSE_SECONDS = 8.0
HOLD_SECONDS = 0.8
MAX_ATTEMPTS = 2

# Frames are mirrored with cv2.flip before MediaPipe sees them. If the prompt
# says LEFT but only the RIGHT turn passes, set this to False.
MIRRORED = True

FRONT_RATIO = 0.55   # shoulder width / torso length above this = facing camera
SIDE_RATIO = 0.35    # below this = body is turned sideways
Z_MARGIN = 0.08      # how much closer one side must be to count as "facing"
MIN_VIS = 0.3

REQUIRED_JOINTS = ("LEFT_SHOULDER", "RIGHT_SHOULDER", "LEFT_HIP", "RIGHT_HIP")


def verify_joints():
    missing = [name for name in REQUIRED_JOINTS if not hasattr(Joint, name)]
    if missing:
        raise RuntimeError("Pose detector is missing required Joint landmarks: "
                           + ", ".join(missing))


def detect_orientation(detector):
    """Returns "FRONT", "LEFT", "RIGHT" (side nearest the camera) or None."""
    lms = detector.landmarks
    if lms is None:
        return None
    ids = (Joint.LEFT_SHOULDER, Joint.RIGHT_SHOULDER,
           Joint.LEFT_HIP, Joint.RIGHT_HIP)
    if any(lms[i].visibility < MIN_VIS for i in ids):
        return None

    ls, rs, lh, rh = (lms[i] for i in ids)
    shoulder_sep = math.hypot(ls.x - rs.x, ls.y - rs.y)
    torso = math.hypot((ls.x + rs.x) / 2 - (lh.x + rh.x) / 2,
                       (ls.y + rs.y) / 2 - (lh.y + rh.y) / 2)
    if torso < 0.05:
        return None

    ratio = shoulder_sep / torso      # works standing AND lying down
    if ratio >= FRONT_RATIO:
        return "FRONT"
    if ratio > SIDE_RATIO:
        return None                   # mid-turn, ignore

    # Sideways: the shoulder/hip closer to the camera has the smaller z
    diff = (ls.z + lh.z) / 2 - (rs.z + rh.z) / 2
    if diff < -Z_MARGIN:
        return "LEFT"
    if diff > Z_MARGIN:
        return "RIGHT"
    return None


def _shown(side):
    """Side name as the user should see it in the prompt."""
    if MIRRORED:
        return "RIGHT" if side == "LEFT" else "LEFT"
    return side


class LivenessGuard:
    def __init__(self, detector, target_reps, mid_check=True, num_checks=None,
                 intro=None, rng=None, clock=None):
        self.detector = detector
        self.target_reps = max(1, int(target_reps))
        self.rng = rng or random
        self.clock = clock or time.monotonic

        self.failed = False
        self.failure_reason = ""
        self.challenge_active = False
        self.passed = False
        self._resume_flag = False

        # Which side the exercise should measure. Starts as LEFT (old behaviour),
        # follows the visible side until the first challenge, then locks to the
        # side the user turned to.
        self.working_side = "LEFT"
        self._side_locked = False

        # Reps at which a check fires, all strictly before the last rep
        if num_checks is None:
            num_checks = 1 if self.target_reps < 10 else 2

        if not mid_check:
            self._pending = []
        elif self.target_reps < 2:
            self._pending = [0]          # 1-rep set: no middle, check before the rep
        else:
            n = min(num_checks, self.target_reps - 1)
            self._pending = sorted(self.rng.sample(range(1, self.target_reps), n))

        self.orientation = None
        self._target = None
        self._start_orientation = None
        self._challenge_started = 0.0
        self._hold_started = None
        self._attempts = 0

    def _start_challenge(self):
        self.challenge_active = True
        self._target = None
        self._start_orientation = None
        self._challenge_started = self.clock()
        self._hold_started = None
        self._attempts = 0

    def _fail(self, reason):
        self.failed = True
        self.failure_reason = reason
        self.challenge_active = False
        self.passed = False

    def update(self, count):
        if self.failed or self.passed:
            return

        self.orientation = detect_orientation(self.detector)

        if not self.challenge_active:
            # Follow whichever side is visible until the first challenge locks it
            if (not self._side_locked
                    and self.orientation in ("LEFT", "RIGHT")):
                self.working_side = self.orientation

            if self._pending and count >= self._pending[0]:
                self._start_challenge()
            elif not self._pending and count >= self.target_reps:
                self.passed = True
            return

        now = self.clock()

        if now - self._challenge_started > RESPONSE_SECONDS:
            self._attempts += 1
            if self._attempts >= MAX_ATTEMPTS:
                self._fail("Liveness challenge timed out. The set was rejected.")
            else:
                self._challenge_started = now
                self._hold_started = None
            return

        ori = self.orientation

        # Step 1: see how they are standing, then ask for a DIFFERENT side
        if self._target is None:
            if ori is None:
                return
            if ori == "FRONT":
                self._target = self.rng.choice(("LEFT", "RIGHT"))
            else:
                self._target = "RIGHT" if ori == "LEFT" else "LEFT"
            self._start_orientation = ori
            self._challenge_started = now
            return

        # Step 2: hold the requested side, then carry on with it
        if ori == self._target:
            if self._hold_started is None:
                self._hold_started = now
            elif now - self._hold_started >= HOLD_SECONDS:
                self.working_side = self._target
                self._side_locked = True
                self._pending.pop(0)
                self.challenge_active = False
                self._resume_flag = True
                self._hold_started = None
        else:
            self._hold_started = None

    def pop_resume_flag(self):
        value = self._resume_flag
        self._resume_flag = False
        return value

    def _prompt(self):
        if self._target is None:
            return "LIVENESS: Stay in view of the camera"
        side = _shown(self._target)
        if self._start_orientation == "FRONT":
            return f"LIVENESS: Turn sideways - show your {side} side"
        return f"LIVENESS: Flip around - show your {side} side"

    def draw(self, frame):
        if self.challenge_active:
            cv2.rectangle(frame, (10, 235), (frame.shape[1] - 10, 325),
                          (20, 20, 20), -1)
            cv2.putText(frame, self._prompt(), (20, 265),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.56, (0, 255, 255), 2)
            remaining = max(
                0, int(RESPONSE_SECONDS - (self.clock() - self._challenge_started)))
            cv2.putText(frame, f"Hold position: {remaining}s", (20, 292),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
            cv2.putText(frame, "Note: camera is mirrored - your LEFT shows as RIGHT",
                        (20, 312), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 200, 255), 1)
            # Debug aid while tuning. Delete when it works well.
            cv2.putText(frame, f"seen: {self.orientation}",
                        (frame.shape[1] - 150, 292),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)

        if self.failed:
            cv2.putText(frame, self.failure_reason[:80], (20, 350),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 0, 255), 2)
        return frame