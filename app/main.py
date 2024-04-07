from dotenv import load_dotenv
from datetime import datetime
from flask import Flask
from detection_eye import detection_eye_bp
import logging
import pytz
import sys


app = Flask(__name__)
# Register the blueprint containing the DetectionEye routes
app.register_blueprint(detection_eye_bp)

# Configure logging
local_timezone = pytz.timezone('Europe/Berlin')
logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                    format='[%(asctime)s.%(msecs)03d] [%(levelname)s]: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logging.Formatter.converter = lambda *args: datetime.now(local_timezone).timetuple()
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


if __name__ == "__main__":
    # Run the Flask application
    app.run(host='0.0.0.0', port=5001)
