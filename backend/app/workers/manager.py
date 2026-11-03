import shutil
import subprocess
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import cv2
if hasattr(cv2, 'setLogLevel'):
    cv2.setLogLevel(0)

from app.core.config import ALLOW_AUTOMATIC_ATTENDANCE, STORAGE, FLIP_WEBCAM_SOURCES
from app.core.security import decrypt
from app.db.database import connection, now, rows, uid
from app.events.bus import bus
from app.modules.attendance.service import mark
from app.vision.engine import engine


def ffmpeg_path():
    executable = shutil.which('ffmpeg')
    if executable:
        return executable
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except (ImportError, RuntimeError):
        return None


class CorrectedCapture:
    """Correct driver-mirrored webcam pixels before any consumer sees them."""
    def __init__(self, capture):
        self.capture = capture

    def read(self):
        ok, frame = self.capture.read()
        return (ok, cv2.flip(frame, 1)) if ok and frame is not None else (ok, frame)

    def __getattr__(self, name):
        return getattr(self.capture, name)


def open_capture(source):
    if source.isdigit():
        capture = cv2.VideoCapture(int(source))
        return CorrectedCapture(capture) if source in FLIP_WEBCAM_SOURCES else capture
    return cv2.VideoCapture(source, cv2.CAP_FFMPEG,
                            [cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000, cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000])


def probe(source):
    cap = open_capture(source)
    try:
        ok, frame = cap.read()
        import base64
        preview = ''
        if ok:
            thumb = cv2.resize(frame, (640, int(frame.shape[0] * 640 / frame.shape[1])))
            encoded_ok, encoded = cv2.imencode('.jpg', thumb)
            if encoded_ok:
                preview = base64.b64encode(encoded).decode()
        return {'ok': bool(ok), 'width': int(frame.shape[1]) if ok else 0,
                'height': int(frame.shape[0]) if ok else 0, 'preview': preview}
    finally:
        cap.release()


class CameraWorker:
    def __init__(self, camera):
        self.camera = camera
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True, name=f"camera-{camera['id'][:8]}")
        self.lock = threading.Lock()
        self.jpeg = None
        self.raw_frame = None
        self.raw_jpeg = None
        self.raw_at = None
        self.raw_stamp = 0.0
        self.analysis_jpeg = None
        self.analysis_stamp = 0.0
        self.last_frame = 0.0
        self.health = 'connecting'
        self.message = ''
        self.frames = 0
        self.fps = 0.0
        self.detections = 0
        self.last_seen = {}
        self.identity = {}
        self.sides = {}
        self.tracker = None
        self.record_error = ''
        self.encoding_threads = []
        self.last_crossing = {}
        self.stream_generation = 0

    def analyze_loop(self):
        previous = 0.0
        while not self.stop_event.is_set():
            with self.lock:
                stamp, captured_at = self.raw_stamp, self.raw_at
                generation = self.stream_generation
                frame = self.raw_frame.copy() if self.raw_frame is not None and self.raw_stamp != previous else None
            if frame is None:
                self.stop_event.wait(0.1)
                continue
            previous = stamp
            try:
                detections = engine.analyze(frame, self.tracker)
                if generation != self.stream_generation:
                    continue
                self.detections = len(detections)
                self.handle_evidence(detections, frame.shape[1], captured_at)
                names = {p['id']: p['name'] for p in rows('SELECT id,name FROM people WHERE active=1')}
                for item in detections:
                    x1, y1, x2, y2 = map(int, item['box'])
                    confirmed = self.identity.get(item['track_id'] or ('face-' + str(item['person_id'])), (None, 0, 0))[1] >= 3
                    label = names.get(item['person_id'], 'Unknown') if confirmed else 'Verifying / Unknown'
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (90, 210, 110), 2)
                    cv2.putText(frame, label, (x1, max(18, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (90, 210, 110), 2)
                cv2.putText(frame, datetime.fromisoformat(captured_at).astimezone(ZoneInfoLocal).strftime('%H:%M:%S') + ' ANALYZED FRAME',
                            (16, frame.shape[0] - 16), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
                success, encoded = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
                if success:
                    with self.lock:
                        self.analysis_jpeg, self.analysis_stamp = encoded.tobytes(), stamp
            except Exception:
                self.message = 'AI processing failed; live stream continues. Check model configuration.'
            self.stop_event.wait(0.3)

    def set_health(self, state, message=''):
        if state != self.health:
            bus.emit('camera.health.changed', self.camera['id'], status=state)
        self.health, self.message = state, message

    def handle_evidence(self, detections, frame_width, captured_at):
        for item in detections:
            person_id = item['person_id']
            track = item['track_id']
            if not person_id:
                continue
            key = track or ('face-' + person_id)
            old_person, count, last = self.identity.get(key, (None, 0, 0))
            if old_person != person_id:
                self.sides.pop(key, None)
            count = count + 1 if old_person == person_id and time.time() - last < 5 else 1
            self.identity[key] = (person_id, count, time.time())
            if count < 3:
                continue
            if time.time() - self.last_seen.get(person_id, 0) > 10:
                with connection() as db:
                    db.execute('INSERT INTO sightings VALUES (?,?,?,?,?,?)',
                               (uid(), person_id, self.camera['id'], item['confidence'], key, captured_at))
                self.last_seen[person_id] = time.time()
                bus.emit('sighting.confirmed', person_id, camera_id=self.camera['id'])
            # Directional attendance requires a body track, never just a face box.
            if not track or self.camera['role'] == 'monitoring':
                continue
            center_x = (item['box'][0] + item['box'][2]) / (2 * frame_width)
            delta = center_x - self.camera['line_x']
            if abs(delta) < 0.035:
                continue
            side = 1 if delta > 0 else -1
            previous = self.sides.get(key)
            self.sides[key] = side
            if previous is None or previous == side:
                continue
            direction = 'right' if side > previous else 'left'
            kind = 'IN' if direction == self.camera['entry_direction'] else 'OUT'
            if self.camera['role'] == 'entry' and kind != 'IN' or self.camera['role'] == 'exit' and kind != 'OUT':
                continue
            crossing_key = (person_id, kind)
            if time.time() - self.last_crossing.get(crossing_key, 0) < 30:
                continue
            self.last_crossing[crossing_key] = time.time()
            if not ALLOW_AUTOMATIC_ATTENDANCE:
                with connection() as db:
                    db.execute('INSERT INTO review_items VALUES (?,?,?,?,?,?)',
                               (uid(), person_id, self.camera['id'], f'{kind} crossing detected; automatic attendance disabled. Verify liveness and identity.', 'open', captured_at))
                bus.emit('review.created', person_id)
                continue
            try:
                mark(person_id, kind, 'Confirmed face and directional crossing; liveness not implemented',
                     source='camera', camera_id=self.camera['id'],
                     event_key=f"{self.camera['id']}:{person_id}:{kind}:{int(time.time() // 30)}", occurred_at=captured_at)
            except Exception:
                # Session conflicts must not kill the stream worker.
                pass
        cutoff = time.time() - 15
        for key in list(self.identity):
            if self.identity[key][2] < cutoff:
                self.identity.pop(key, None)
                self.sides.pop(key, None)

    def finish_recording(self, writer, record_id, raw_path):
        if writer is None:
            return
        writer.release()
        ffmpeg = ffmpeg_path()
        output = raw_path.with_suffix('.mp4')
        status = 'unavailable'
        try:
            if ffmpeg and raw_path.is_file():
                process = subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-y', '-i', str(raw_path),
                                          '-an', '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p',
                                          '-movflags', '+faststart', str(output)],
                                         capture_output=True, timeout=45, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                if process.returncode == 0 and output.is_file():
                    status = 'ready'
                    raw_path.unlink(missing_ok=True)
            if status != 'ready':
                self.record_error = 'Recording could not be encoded. Install FFmpeg with libx264.'
            with connection() as db:
                db.execute('UPDATE recordings SET path=?,ended_at=COALESCE(ended_at,?),status=?,bytes=? WHERE id=?',
                           (str(output if status == 'ready' else raw_path), now(), status,
                            output.stat().st_size if status == 'ready' else 0, record_id))
            bus.emit('recording.status.changed', record_id, status=status)
        except Exception:
            self.record_error = 'Recording encoding failed.'
            with connection() as db:
                db.execute("UPDATE recordings SET ended_at=COALESCE(ended_at,?),status='unavailable' WHERE id=?", (now(), record_id))

    def queue_recording(self, writer, record_id, raw_path):
        if writer is None:
            return
        writer.release()
        # Finalize the capture interval before encoding so timeline links stay accurate.
        with connection() as db:
            db.execute("UPDATE recordings SET ended_at=?,status='encoding' WHERE id=?", (now(), record_id))
        self.encoding_threads = [thread for thread in self.encoding_threads if thread.is_alive()]
        thread = threading.Thread(target=self.finish_recording, args=(writer, record_id, raw_path), daemon=True)
        self.encoding_threads.append(thread)
        thread.start()

    def run(self):
        source = decrypt(self.camera['source'])
        engine.load()
        try:
            from trackers import ByteTrackTracker
            self.tracker = ByteTrackTracker(frame_rate=2.0, lost_track_buffer=90, track_activation_threshold=0.4, high_conf_det_threshold=0.4)
        except ImportError:
            pass
        analysis_thread = threading.Thread(target=self.analyze_loop, daemon=True)
        analysis_thread.start()
        while not self.stop_event.is_set():
            cap, writer, record_id, raw_path = None, None, None, None
            try:
                with self.lock:
                    self.stream_generation += 1
                    self.raw_frame = None
                    self.raw_jpeg = None
                self.identity.clear()
                self.sides.clear()
                if self.tracker is not None:
                    from trackers import ByteTrackTracker
                    self.tracker = ByteTrackTracker(frame_rate=2.0, lost_track_buffer=90, track_activation_threshold=0.4, high_conf_det_threshold=0.4)
                cap = open_capture(source)
                if not cap.isOpened():
                    raise RuntimeError('Camera could not connect.')
                self.set_health('live')
                segment_start, written_frames, fps_start = 0, 0, time.time()
                fps_frames = 0
                while not self.stop_event.is_set():
                    ok, frame = cap.read()
                    if not ok:
                        raise RuntimeError('No frame received. Reconnecting.')
                    captured_at, captured_time = now(), time.time()
                    self.last_frame = captured_time
                    h, w = frame.shape[:2]
                    if w > 1280:
                        frame = cv2.resize(frame, (1280, int(h * 1280 / w)))
                        h, w = frame.shape[:2]
                    # Freeze enrollment pixels before any analysis, recording or overlays.
                    encoded_ok, raw_encoded = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
                    with self.lock:
                        self.raw_frame, self.raw_at, self.raw_stamp = frame.copy(), captured_at, captured_time
                        self.raw_jpeg = raw_encoded.tobytes() if encoded_ok else None
                    if self.camera['recording'] and ffmpeg_path():
                        if writer is None or captured_time - segment_start >= 60:
                            self.queue_recording(writer, record_id, raw_path)
                            segment_start = captured_time
                            written_frames = 0
                            folder = STORAGE / 'recordings' / datetime.now(timezone.utc).strftime('%Y-%m-%d') / self.camera['id']
                            folder.mkdir(parents=True, exist_ok=True)
                            record_id = uid()
                            raw_path = folder / f'{record_id}.avi'
                            writer = cv2.VideoWriter(str(raw_path), cv2.VideoWriter_fourcc(*'MJPG'), 10, (w, h))
                            if not writer.isOpened():
                                raise RuntimeError('Video writer failed.')
                            with connection() as db:
                                db.execute('INSERT INTO recordings VALUES (?,?,?,?,?,?,?)',
                                           (record_id, self.camera['id'], str(raw_path), captured_at, None, 'recording', 0))
                        target_frames = max(1, int((captured_time - segment_start) * 10) + 1)
                        while written_frames < target_frames:
                            writer.write(frame)
                            written_frames += 1
                    elif self.camera['recording']:
                        self.record_error = 'FFmpeg is not installed. Recording unavailable; live preview still works.'
                    overlay = frame.copy()
                    if self.camera['role'] != 'monitoring':
                        x = int(w * self.camera['line_x'])
                        cv2.line(overlay, (x, 0), (x, h), (255, 190, 80), 2)
                    cv2.putText(overlay, datetime.now(ZoneInfoLocal).strftime('%H:%M:%S'), (16, h - 16),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                    success, encoded = cv2.imencode('.jpg', overlay, [cv2.IMWRITE_JPEG_QUALITY, 75])
                    if success:
                        with self.lock:
                            self.jpeg = encoded.tobytes()
                    fps_frames += 1
                    if captured_time - fps_start >= 2:
                        self.fps = round(fps_frames / (captured_time - fps_start), 1)
                        fps_start, fps_frames = captured_time, 0
                    self.stop_event.wait(0.03)
            except Exception:
                self.set_health('reconnecting', 'Stream unavailable. Check camera, network and source credentials.')
            finally:
                if cap is not None:
                    cap.release()
                self.queue_recording(writer, record_id, raw_path)
            self.stop_event.wait(3)
        self.set_health('stopped')
        analysis_thread.join(timeout=5)


from zoneinfo import ZoneInfo
from app.core.config import TIMEZONE
ZoneInfoLocal = ZoneInfo(TIMEZONE)


class WorkerManager:
    def __init__(self):
        self.workers = {}
        self.lock = threading.RLock()
        self.retention_stop = threading.Event()

    def restore(self):
        self.retention_stop = threading.Event()
        with connection() as db:
            db.execute("UPDATE recordings SET status='unavailable',ended_at=COALESCE(ended_at,?) WHERE status IN ('recording','encoding')", (now(),))
        for camera in rows('SELECT * FROM cameras WHERE enabled=1'):
            self.start(camera)
        threading.Thread(target=self.retention_loop, daemon=True).start()

    def start(self, camera):
        with self.lock:
            old = self.workers.get(camera['id'])
            if old and old.thread.is_alive():
                return
            worker = CameraWorker(camera)
            self.workers[camera['id']] = worker
            worker.thread.start()

    def stop(self, camera_id):
        with self.lock:
            worker = self.workers.get(camera_id)
        if worker:
            worker.stop_event.set()
            worker.thread.join(timeout=12)

    def status(self, camera_id):
        worker = self.workers.get(camera_id)
        if not worker:
            return {'status': 'stopped', 'fps': 0, 'last_frame_at': None, 'last_analysis_at': None, 'detections': 0, 'message': '', 'recording_error': ''}
        age = time.time() - worker.last_frame if worker.last_frame else None
        health = worker.health
        if health == 'live' and age is not None and age > 8:
            health = 'degraded'
        return {'status': health, 'fps': worker.fps if health == 'live' else 0,
                'last_frame_at': datetime.fromtimestamp(worker.last_frame, timezone.utc).isoformat() if worker.last_frame else None,
                'last_analysis_at': datetime.fromtimestamp(worker.analysis_stamp, timezone.utc).isoformat() if worker.analysis_stamp else None,
                'detections': worker.detections if health == 'live' else 0,
                'message': worker.message, 'recording_error': worker.record_error}

    def frame(self, camera_id, analysis=False):
        worker = self.workers.get(camera_id)
        if not worker or not worker.last_frame or time.time() - worker.last_frame > 8:
            return None, None
        with worker.lock:
            return (worker.analysis_jpeg, worker.analysis_stamp) if analysis else (worker.jpeg, worker.last_frame)

    def retention_loop(self):
        while not self.retention_stop.is_set():
            for record in rows('''SELECT r.*,c.retention_days FROM recordings r JOIN cameras c ON c.id=r.camera_id
                                  WHERE r.status IN ('ready','unavailable') AND r.ended_at IS NOT NULL'''):
                if datetime.fromisoformat(record['ended_at']) < datetime.now(timezone.utc) - timedelta(days=record['retention_days']):
                    path = Path(record['path']).resolve()
                    if path.is_relative_to((STORAGE / 'recordings').resolve()):
                        try:
                            path.unlink(missing_ok=True)
                            with connection() as db:
                                db.execute("UPDATE recordings SET status='expired',bytes=0 WHERE id=?", (record['id'],))
                        except OSError:
                            pass
            self.retention_stop.wait(60)

    def shutdown(self):
        self.retention_stop.set()
        for worker in list(self.workers.values()):
            worker.stop_event.set()
        for worker in list(self.workers.values()):
            worker.thread.join(timeout=12)
            for thread in worker.encoding_threads:
                thread.join(timeout=45)


manager = WorkerManager()
