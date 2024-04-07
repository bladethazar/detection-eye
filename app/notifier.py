import os
import sys
import time
import requests
import logging

from flask import jsonify

logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                    format='[%(asctime)s.%(msecs)03d][%(levelname)s]: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logging.Formatter.converter = time.gmtime
logger = logging.getLogger(__name__)


class Notifier:
    def __init__(self):
        self.telegram_notifier_url = os.getenv('TELEGRAM_NOTIFIER_URL') if os.getenv('TELEGRAM_NOTIFIER_URL') else 'http://localhost:5000'

    def send_telegram_notification(self, message="", image=None):
        try:
            telegram_notifier_url = self.telegram_notifier_url
            if image is not None:
                params = {'caption': message}
                image_file = {'photo': ('image.jpg', image, 'image/jpeg')}
                response = requests.post(f"{telegram_notifier_url}/send_photo", params=params, files=image_file)
            else:
                params = {'message': message}
                response = requests.post(f"{telegram_notifier_url}/send_message", json=params)

            response.raise_for_status()
            logger.info('Request to [telegram-notifier] sent successful.')
        except Exception as e:
            logger.error(f'Request to [telegram-notifier] failed: {str(e)}')
            raise e
