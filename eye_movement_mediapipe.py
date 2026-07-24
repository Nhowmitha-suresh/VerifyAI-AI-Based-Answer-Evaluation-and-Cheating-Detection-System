"""
Eye & Iris Tracker Module - MediaPipe FaceMesh Engine
Provides precise gaze direction, iris center calculation, eye aspect ratio (EAR),
and pupil localization for proctoring and computer vision applications.
"""

import cv2
import numpy as np
import mediapipe as mp

class EyeTracker:
    # Landmark indices for MediaPipe Face Mesh (468 + 10 refine landmark points)
    LEFT_IRIS = [474, 475, 476, 477]
    RIGHT_IRIS = [469, 470, 471, 472]
    
    # Eye corner & contour landmarks
    LEFT_EYE_CORNERS = [33, 133]    # Inner, Outer
    RIGHT_EYE_CORNERS = [362, 263]  # Inner, Outer
    
    LEFT_EYE_TOP_BOTTOM = [159, 145]
    RIGHT_EYE_TOP_BOTTOM = [386, 374]

    def __init__(self, min_detection_confidence=0.5, min_tracking_confidence=0.5):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )

    def process_frame(self, frame):
        """
        Process BGR frame and return eye/iris analysis dict.
        Returns None if no face is detected.
        """
        img_h, img_w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb)

        if not results.multi_face_landmarks:
            return None

        landmarks = results.multi_face_landmarks[0].landmark
        lm_px = np.array([(int(p.x * img_w), int(p.y * img_h)) for p in landmarks])

        # Iris centers
        left_iris_pts = lm_px[self.LEFT_IRIS]
        right_iris_pts = lm_px[self.RIGHT_IRIS]
        
        left_center = np.mean(left_iris_pts, axis=0)
        right_center = np.mean(right_iris_pts, axis=0)

        # Eye aspect ratio (EAR) estimation for blinking / drowsiness
        left_top = lm_px[self.LEFT_EYE_TOP_BOTTOM[0]]
        left_bot = lm_px[self.LEFT_EYE_TOP_BOTTOM[1]]
        left_outer = lm_px[self.LEFT_EYE_CORNERS[0]]
        left_inner = lm_px[self.LEFT_EYE_CORNERS[1]]

        left_ear = np.linalg.norm(left_top - left_bot) / max(1.0, np.linalg.norm(left_outer - left_inner))

        right_top = lm_px[self.RIGHT_EYE_TOP_BOTTOM[0]]
        right_bot = lm_px[self.RIGHT_EYE_TOP_BOTTOM[1]]
        right_outer = lm_px[self.RIGHT_EYE_CORNERS[0]]
        right_inner = lm_px[self.RIGHT_EYE_CORNERS[1]]

        right_ear = np.linalg.norm(right_top - right_bot) / max(1.0, np.linalg.norm(right_outer - right_inner))

        avg_ear = (left_ear + right_ear) / 2.0

        # Relative iris positions within eye horizontal span (0.0=left, 1.0=right)
        left_span = left_inner[0] - left_outer[0]
        right_span = right_outer[0] - right_inner[0]
        
        rel_left_x = (left_center[0] - left_outer[0]) / max(1, left_span) if left_span != 0 else 0.5
        rel_right_x = (right_center[0] - right_inner[0]) / max(1, right_span) if right_span != 0 else 0.5
        
        avg_rel_x = (rel_left_x + rel_right_x) / 2.0

        # Gaze Direction Classification
        if avg_rel_x < 0.35:
            gaze_dir = "LOOKING_LEFT"
        elif avg_rel_x > 0.65:
            gaze_dir = "LOOKING_RIGHT"
        else:
            gaze_dir = "CENTER"

        return {
            "lm_px": lm_px,
            "left_iris_center": tuple(left_center.astype(int)),
            "right_iris_center": tuple(right_center.astype(int)),
            "left_iris_pts": left_iris_pts,
            "right_iris_pts": right_iris_pts,
            "avg_ear": avg_ear,
            "relative_gaze_x": avg_rel_x,
            "gaze_direction": gaze_dir,
            "raw_landmarks": landmarks
        }

    def close(self):
        self.face_mesh.close()


def main():
    """Standalone live preview for EyeTracker."""
    cap = cv2.VideoCapture(0)
    tracker = EyeTracker()

    print("[INFO] Starting Eye & Iris Tracker... Press ESC to exit.")
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        data = tracker.process_frame(frame)
        if data:
            # Draw iris points
            cv2.circle(frame, data["left_iris_center"], 4, (0, 255, 0), -1)
            cv2.circle(frame, data["right_iris_center"], 4, (0, 255, 0), -1)

            # Draw HUD metrics
            gaze = data["gaze_direction"]
            ear = data["avg_ear"]
            
            color = (0, 255, 0) if gaze == "CENTER" else (0, 0, 255)
            cv2.putText(frame, f"GAZE: {gaze}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            cv2.putText(frame, f"EAR: {ear:.2f}", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        else:
            cv2.putText(frame, "NO FACE DETECTED", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        cv2.imshow("Eye & Iris Tracker - Preview", frame)
        if cv2.waitKey(1) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()
    tracker.close()

if __name__ == "__main__":
    main()
