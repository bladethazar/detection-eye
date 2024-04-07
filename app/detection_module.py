import os
# TODO: Implement metrics
from metrics_collector import metrics_collector
from dotenv import load_dotenv
from datetime import datetime
from flask import Response, current_app
import logging
import pytz
import time
import sys
import cv2

# Configure logging
local_timezone = pytz.timezone('Europe/Berlin')
logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                    format='[%(asctime)s.%(msecs)03d] [%(levelname)s]: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logging.Formatter.converter = lambda *args: datetime.now(local_timezone).timetuple()
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class DetectionModule:
    def __init__(self):
        self.activated = False
        self.notifications_activated = False
        self.send_detection_notification = False
        # Set default notification interval to 20 seconds if env-var not set
        self.notification_interval = os.getenv('NOTIFICATION_INTERVAL_IN_SECS') if os.getenv(
            'NOTIFICATION_INTERVAL_IN_SECS') else 20
        self.detect_motions = False
        self.motion_detected = False
        self.detect_cats = False
        self.cat_detected = False
        self.detect_faces = True
        self.face_detected = False
        self.motion_detected_coords = []  # List to store motion coordinates
        self.last_detection_time = 0

    def set_activated(self, status: bool):
        self.activated = True if status else False
        return {"is_activated": self.activated}

    def is_activated(self):
        return {"active": self.activated}

    def set_send_detection_notification(self):
        self.send_detection_notification = True
        return {"message": "Detection notification activated"}

    def activate_detect_motion_mode(self):
        self.detect_motions = True
        return {"message": "Motion detection activated."}

    def activate_detect_cats_mode(self):
        self.detect_cats = True
        return {"message": "Cat detection activated."}

    def activate_detect_faces_mode(self):
        self.detect_faces = True
        return {"message": "Motion detection activated."}

    def get_detection_mode_config(self):
        detection_module_config = {
            "detect_motions": self.detect_motions,
            "detect_cats": self.detect_cats,
            "detect_faces": self.detect_faces
        }
        return detection_module_config

    def check_detection_mode_status(self):
        if self.detect_motions:
            self.detect_cats = False
            self.detect_faces = False
        if self.detect_cats:
            self.detect_motions = False
            self.detect_faces = False
        if self.detect_faces:
            self.detect_motions = False
            self.detect_cats = False

    def detect(self, frame):
        try:
            def generate():
                bg_subtractor = cv2.createBackgroundSubtractorMOG2()

                try:
                    fg_mask = bg_subtractor.apply(frame)
                    contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    motion_detection_notification_sent = False
                    for contour in contours:
                        if cv2.contourArea(contour) < 900:
                            continue
                        (x, y, w, h) = cv2.boundingRect(contour)
                        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                        self.motion_detected = True  # Set motion detected flag to True
                        self.motion_detected_coords.append((x, y))  # Store motion coordinates

                        if self.motion_detected and not motion_detection_notification_sent:
                            # Motion detected for the first time, send notification
                            if self.notifications_activated:
                                self.send_detection_notification = True

                            motion_detection_notification_sent = True
                            self.last_detection_time = time.time()  # Update last motion detected time

                        if self.motion_detected and time.time() - self.last_detection_time >= self.notification_interval:
                            # Reset motion detection notification after interval
                            motion_detection_notification_sent = False
                            logger.info(
                                f"Total number of motions detected: {len(self.motion_detected_coords)} within the last {'{:.3f}'.format(time.time() - self.last_detection_time)} seconds.")
                            logger.info(f"Motions detected at coordinates: {self.motion_detected_coords}")
                            self.motion_detected_coords.clear()

                    ret, jpeg = cv2.imencode('.jpg', frame)
                    yield b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n'
                except IOError as io_e:
                    logger.error(io_e)
                    return 500, str(io_e)

            return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')
        except Exception as e:
            logger.error(f"Error in detect_motion: {str(e)}")
            return 500, str(e)

    # TODO: Implement cat detection
    def detect_cats(self):
        pass

    # TODO: Implement face detection
    def detect_faces(self):
        pass
