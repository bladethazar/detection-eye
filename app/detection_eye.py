from concurrent.futures import ThreadPoolExecutor
from prometheus_client import generate_latest
from app import notifier
# TODO: Implement metrics
from metrics_collector import metrics_collector
from flask import jsonify, Response, Blueprint, send_from_directory
from dotenv import load_dotenv
from datetime import datetime
import detection_module
import requests
import logging
import pytz
import sys
import cv2
import os

# Configure logging
local_timezone = pytz.timezone('Europe/Berlin')
logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                    format='[%(asctime)s.%(msecs)03d] [%(levelname)s]: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logging.Formatter.converter = lambda *args: datetime.now(local_timezone).timetuple()
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Define a Blueprint for the DetectionEye routes
detection_eye_bp = Blueprint('detection_eye', __name__)


class DetectionEye:
    def __init__(self):
        self.camera_root_url = os.getenv('CAMERA_ROOT_URL')
        self.video_feed_url = os.getenv('VIDEO_FEED_URL')
        self.cap = cv2.VideoCapture(self.video_feed_url)
        self.detection_module = detection_module.DetectionModule()
        self.camera_shot = False
        self.notifier = notifier.Notifier()

    def __del__(self):
        self.cap.release()

    def read_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return None
        return frame

    def get_video_stream(self):
        def generate():
            try:
                while self.cap.isOpened():
                    frame = self.read_frame()
                    try:
                        # TODO: Currently no image is displayed at the video_stream endpoint.
                        #   Problem maybe related to instance / threading?
                        # if self.detection_module.is_activated():
                        #     if self.detection_module.send_detection_notification:
                        #         self.camera_shot = self.create_camera_shot()
                        #         self.notifier.send_telegram_notification('DetectionEye Notification!', self.camera_shot)
                        #     return self.detection_module.detect(frame)
                        # else:
                        ret, jpeg = cv2.imencode('.jpg', frame)
                        yield b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n'
                    except Exception as e:
                        raise e
                self.__del__()
            except IOError as io_e:
                return 500, str(io_e)

        return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

    def create_camera_shot(self):
        try:
            requests.post(f"{self.camera_root_url}/focus")
            res = requests.post(f"{self.camera_root_url}/shot.jpg")
            return res.content
        except Exception as e:
            logger.error(f"Error creating IP camera shot: {str(e)}")
            return jsonify({'error': 'Internal Server Error'}), 500


@detection_eye_bp.route('/video_stream', methods=['GET'])
def video_stream():
    detection_eye = DetectionEye()
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            # Submit the detect_motion function to the executor
            future = executor.submit(detection_eye.get_video_stream)
            # Wait for the result (response) of the detect_motion function
            result = future.result()
        return result
    # TODO: Adjustment for the except-clause necessary to display the image if the video-stream is not available
    except IOError as e:
        return send_from_directory(detection_eye_bp.static_folder, 'favicon.ico', mimetype='image/vnd.microsoft.icon')


@detection_eye_bp.route('/send_camera_shot', methods=['POST'])
def send_camera_shot():
    detection_eye = DetectionEye()
    try:
        camera_shot = detection_eye.create_camera_shot()
        detection_eye.notifier.send_telegram_notification("IP camera shot.", camera_shot)
        return jsonify({"message": "Camera Shot sent."})
    except IOError as e:
        return jsonify({"error": f"Sending camera-shot failed. \n\r{e}"}), 500


@detection_eye_bp.route('/metrics', methods=['GET'])
def metrics():
    return Response(generate_latest(), mimetype='text/plain')


@detection_eye_bp.route('/detection_status/<status>', methods=['POST'])
def detection_status(status):
    instance_detection_module = DetectionEye().detection_module
    if status.lower() == 'activate' and not instance_detection_module.activated:
        instance_detection_module.set_activated(True)
    if status.lower() == 'activate' and instance_detection_module.activated:
        return jsonify({"message": f"DetectionModule already active."}), 202
    if status.lower() == 'deactivate' and instance_detection_module.activated:
        instance_detection_module.set_activated(False)
    if status.lower() == 'deactivate' and not instance_detection_module.activated:
        return jsonify({"message": f"DetectionModule already inactive."}), 202
    else:
        return jsonify({"error": f"Request failed due to not known status. Possible status: activate | deactivate"}), 400


@detection_eye_bp.route('/detection_mode/<mode>', methods=['POST'])
def detection_mode(mode):
    instance_detection_module = DetectionEye().detection_module
    if instance_detection_module.activated:
        match mode:
            case 'motions': instance_detection_module.activate_detect_motion_mode()
            case 'cats': instance_detection_module.activate_detect_cats_mode()
            case 'faces': instance_detection_module.activate_detect_faces_mode()
            case _: return jsonify({"error": f"Request failed due to not known mode. Possible modes: motions | cats | faces"}), 400
    else:
        return jsonify({"error": "DetectionModule not active. Activate first, then set detection_mode"}), 400


@detection_eye_bp.route('/get_detection_config', methods=['GET'])
def get_detection_config():
    instance_detection_module = DetectionEye().detection_module
    return jsonify({"config": f"{instance_detection_module.get_detection_mode_config()}"})

