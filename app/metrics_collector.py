from prometheus_client import Gauge, Counter


class MetricsCollector:
    def __init__(self):
        self.frame_processing_time = Gauge('frame_processing_time_seconds', 'Time taken to process each frame')
        self.motion_events_detected = Counter('motion_events_detected_total', 'Total number of motion events detected')
        self.error_count = Counter('error_count_total', 'Total number of errors encountered')
        self.camera_fps = Gauge('camera_fps', 'Frames per second (FPS) of the camera stream')
        self.frame_drop_rate = Gauge('frame_drop_rate_percentage', 'Percentage of frames that are dropped or skipped during processing')
        self.network_bandwidth_usage = Gauge('network_bandwidth_usage_bytes', 'Network bandwidth usage in bytes')
        self.response_time = Gauge('response_time_seconds', 'Response time of the application endpoints')
        self.concurrency_level = Gauge('concurrency_level', 'Number of concurrent requests or processing tasks')

    def record_frame_processing_time(self, processing_time):
        self.frame_processing_time.set(processing_time)

    def increment_motion_events_detected(self):
        self.motion_events_detected.inc()

    def increment_error_count(self):
        self.error_count.inc()

    def set_camera_fps(self, fps):
        self.camera_fps.set(fps)

    def set_frame_drop_rate(self, rate):
        self.frame_drop_rate.set(rate)

    def set_network_bandwidth_usage(self, usage):
        self.network_bandwidth_usage.set(usage)

    def set_response_time(self, time):
        self.response_time.set(time)

    def set_concurrency_level(self, level):
        self.concurrency_level.set(level)
