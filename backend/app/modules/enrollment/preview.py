"""Short-lived, owner-scoped enrollment previews. No AI or recording side effects."""
import base64
import threading
import time
import cv2
import numpy as np
from fastapi import HTTPException
from app.db.database import uid


def preview_image(jpeg):
    """Reject unusable dark feeds even if the camera successfully encodes JPEG."""
    frame = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        return {'ready': False, 'error': 'Camera image could not be decoded. Restart the camera.'}
    height, width = frame.shape[:2]
    center = frame[height // 5:height * 4 // 5, width // 5:width * 4 // 5]
    gray = cv2.cvtColor(center, cv2.COLOR_BGR2GRAY)
    if np.mean(gray < 18) > .97:
        return {'ready': False, 'error': 'Camera image is black or too dark for enrollment. Check lighting, uncover the lens, then restart the camera.'}
    return {'ready': True, 'image': base64.b64encode(jpeg).decode()}


class Preview:
    def __init__(self, owner, person_id, source=None, camera_id=None):
        self.id = uid()
        self.owner, self.person_id = owner, person_id
        self.source, self.camera_id = source, camera_id
        self.last_access = time.monotonic()
        self.stop = threading.Event()
        self.lock = threading.Lock()
        self.jpeg = None
        self.frame_at = 0
        self.error = ''
        self.thread = None
        if source is not None:
            self.thread = threading.Thread(target=self.capture, daemon=True)
            self.thread.start()

    def capture(self):
        from app.workers.manager import open_capture
        cap = None
        try:
            cap = open_capture(self.source)
            if not cap.isOpened():
                raise RuntimeError()
            failures = 0
            while not self.stop.is_set() and time.monotonic() - self.last_access < 20:
                ok, frame = cap.read()
                if not ok:
                    failures += 1
                    if failures > 15:
                        raise RuntimeError()
                    self.stop.wait(.1)
                    continue
                failures = 0
                height, width = frame.shape[:2]
                if width > 1280:
                    frame = cv2.resize(frame, (1280, int(height * 1280 / width)))
                success, encoded = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
                if success:
                    with self.lock:
                        self.jpeg, self.frame_at = encoded.tobytes(), time.monotonic()
                self.stop.wait(.08)
        except Exception:
            self.error = 'The camera could not deliver video. Close other camera apps, check system camera access, then try again.'
        finally:
            if cap is not None:
                cap.release()
            with self.lock:
                self.jpeg = None

    def read(self):
        self.last_access = time.monotonic()
        if self.stop.is_set():
            raise HTTPException(410, 'Preview ended. Start the camera again.')
        if self.camera_id:
            from app.workers.manager import manager
            worker = manager.workers.get(self.camera_id)
            if not worker or not worker.last_frame or time.time() - worker.last_frame > 5:
                return {'ready': False, 'error': 'The selected camera has no recent frames. Check its connection.'}
            with worker.lock:
                jpeg = worker.raw_jpeg
            if jpeg:
                return preview_image(jpeg)
        with self.lock:
            jpeg, stamp = self.jpeg, self.frame_at
        if jpeg and time.monotonic() - stamp < 5 and not self.error:
            return preview_image(jpeg)
        return {'ready': False, 'error': self.error}

    def close(self):
        self.stop.set()
        if self.thread:
            self.thread.join(timeout=6)


class PreviewSessions:
    def __init__(self):
        self.sessions = {}
        self.lock = threading.RLock()

    def start(self, owner, person_id, source=None, camera_id=None):
        with self.lock:
            for token, preview in list(self.sessions.items()):
                if preview.owner == owner or time.monotonic() - preview.last_access > 20:
                    preview.close()
                    if preview.thread and preview.thread.is_alive():
                        raise HTTPException(409, 'The previous camera is still closing. Try again in a moment.')
                    self.sessions.pop(token, None)
                elif source is not None and preview.source == source:
                    raise HTTPException(409, 'This webcam is being used by another enrollment preview. Try again shortly.')
            preview = Preview(owner, person_id, source, camera_id)
            self.sessions[preview.id] = preview
            return preview

    def get(self, token, owner, person_id):
        with self.lock:
            preview = self.sessions.get(token)
        if not preview or preview.owner != owner or preview.person_id != person_id:
            raise HTTPException(404, 'Enrollment preview not found.')
        if time.monotonic() - preview.last_access > 20:
            self.close(token, owner, person_id)
            raise HTTPException(410, 'Preview expired. Start the camera again.')
        return preview

    def close(self, token, owner, person_id):
        with self.lock:
            preview = self.sessions.get(token)
            if preview and preview.owner == owner and preview.person_id == person_id:
                self.sessions.pop(token, None)
                preview.close()

    def shutdown(self):
        with self.lock:
            for preview in self.sessions.values():
                preview.close()
            self.sessions.clear()


previews = PreviewSessions()
