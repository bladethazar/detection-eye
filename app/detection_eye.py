from datetime import datetime
import pytz
from dotenv import load_dotenv
from flask import Flask, Response, jsonify
from prometheus_client import generate_latest
import sys
import threading
import time
import cv2
import requests
import logging
import os
import notifier

# Configure logging
local_timezone = pytz.timezone('Europe/Berlin')
logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                    format='[%(asctime)s.%(msecs)03d] [%(levelname)s]: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logging.Formatter.converter = lambda *args: datetime.now(local_timezone).timetuple()
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__)


class DetectionEye:
    def __init__(self):
        self.camera_root_url = os.getenv('CAMERA_ROOT_URL')
        self.video_feed_url = os.getenv('VIDEO_FEED_URL')
        self.cap = cv2.VideoCapture(self.video_feed_url)
        # self.metrics_collector = metrics_collector.MetricsCollector()
        self.notifier = notifier.Notifier()

    def __del__(self):
        self.cap.release()

    def read_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return None
        return frame

    def create_camera_shot(self):
        try:
            requests.post(f"{self.camera_root_url}/focus")
            res = requests.post(f"{self.camera_root_url}/shot.jpg")
            return res.content
        except Exception as e:
            app.logger.error(f"Error creating IP camera shot: {str(e)}")
            return jsonify({'error': 'Internal Server Error'}), 500

    def detect_motion(self):
        try:
            cap = self.cap
            bg_subtractor = cv2.createBackgroundSubtractorMOG2()

            def generate():
                motion_detection_notification_sent = False
                notification_interval = 20  # Send notification interval in seconds
                last_motion_detected_time = 0  # Initialize last motion detected time
                motion_detected_coords = []  # List to store motion coordinates

                try:
                    while cap.isOpened():
                        frame = self.read_frame()
                        fg_mask = bg_subtractor.apply(frame)
                        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                        motion_detected = False  # Flag to track if motion is detected in any contour

                        # Initialize a dictionary to store motion coordinates

                        for contour in contours:
                            if cv2.contourArea(contour) < 900:
                                continue
                            (x, y, w, h) = cv2.boundingRect(contour)
                            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                            motion_detected = True  # Set motion detected flag to True
                            motion_detected_coords.append((x, y))  # Store motion coordinates

                            if motion_detected and not motion_detection_notification_sent:
                                # Motion detected for the first time, send notification
                                camera_shot = self.create_camera_shot()
                                self.notifier.send_telegram_message('Motion detected!', camera_shot)
                                motion_detection_notification_sent = True
                                last_motion_detected_time = time.time()  # Update last motion detected time

                            if motion_detected and time.time() - last_motion_detected_time >= notification_interval:
                                # Reset motion detection notification after interval
                                motion_detection_notification_sent = False
                                logger.info(f"Total number of motions detected: {len(motion_detected_coords)} within the last {'{:.3f}'.format(time.time() - last_motion_detected_time)} seconds.")
                                logger.info(f"Motions detected at coordinates: {motion_detected_coords}")
                                motion_detected_coords.clear()

                        ret, jpeg = cv2.imencode('.jpg', frame)
                        yield b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n'
                    self.__del__()
                except IOError as io_e:
                    logger.error(io_e)

            return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')
        except Exception as e:
            logger.error(f"Error in detect_motion: {str(e)}")
            return 500, str(e)

    def get_video_feed(self):
        try:
            cap = self.cap

            def generate():
                try:
                    while cap.isOpened():
                        frame = self.read_frame()
                        ret, jpeg = cv2.imencode('.jpg', frame)
                        yield b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n'
                    # Release video capture object when done
                    self.__del__()
                    # cap.release()
                except IOError as io_e:
                    return 500, str(io_e)

            return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')
        except Exception as e:
            return 500, str(e)


@app.route('/detection_video_feed')
def detection_video_feed():
    try:
        detection_eye = DetectionEye()
        return detection_eye.detect_motion()
    except Exception as e:
        raise e


# Function to stream video from the IP camera
@app.route('/video_feed')
def video_feed():
    try:
        detection_eye = DetectionEye()
        return detection_eye.get_video_feed()
    except Exception as e:
        raise e


# Endpoint to serve Prometheus metrics
@app.route('/metrics')
def metrics():
    return Response(generate_latest(), mimetype='text/plain')


def run_detection_eye():
    # Start motion detection in a separate thread
    try:
        detection_eye = DetectionEye()
        detection_thread = threading.Thread(target=detection_eye.detect_motion())
        detection_thread.start()
    except Exception as e:
        raise e

    pass


if __name__ == "__main__":
    # run_detection_eye()

    # Start Flask web server for video streaming
    app.run(host='0.0.0.0', port=5001)
