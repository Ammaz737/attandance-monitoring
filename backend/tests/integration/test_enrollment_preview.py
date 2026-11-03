import threading
import time
from types import SimpleNamespace
import numpy as np
import cv2
from app.db.database import connection, rows
from app.modules.enrollment.preview import previews


def fake_devices(monkeypatch):
    import app.streaming.devices as devices
    monkeypatch.setattr(devices, 'discover_webcams', lambda: [{'source': '700', 'name': 'Test USB Webcam'}])


def test_native_preview_capture_cleanup_and_no_enrollment_side_effect(admin, person, monkeypatch):
    import app.workers.manager as workers
    fake_devices(monkeypatch)
    released = threading.Event()
    class Capture:
        def isOpened(self): return True
        def read(self): return True, np.full((240, 320, 3), 120, dtype=np.uint8)
        def release(self): released.set()
    monkeypatch.setattr(workers, 'open_capture', lambda source: Capture())
    options = admin.get('/api/v1/enrollment/cameras').json()
    assert options['devices'] == [{'id': 'device:700', 'name': 'Test USB Webcam'}]
    base = f"/api/v1/people/{person['id']}/enrollment/preview"
    response = admin.post(base, json={'device_id': 'device:700'})
    assert response.status_code == 200, response.text
    token = response.json()['id']
    frame = {}
    for _ in range(30):
        frame = admin.get(f'{base}/{token}').json()
        if frame.get('ready'): break
        time.sleep(.02)
    assert frame['ready'] and frame['image'].startswith('/9j/')
    assert not rows('SELECT * FROM face_templates')
    assert not rows('SELECT * FROM attendance_sessions')
    assert not rows('SELECT * FROM recordings')
    assert admin.delete(f'{base}/{token}').status_code == 200
    assert released.wait(1)
    assert token not in previews.sessions


def test_running_camera_preview_reuses_raw_frames(admin, person, monkeypatch):
    import app.workers.manager as workers
    location = admin.post('/api/v1/locations', json={'name': 'Entry'}).json()
    camera = admin.post('/api/v1/cameras', json={'name': 'Registered webcam', 'location_id': location['id'], 'source': '700'}).json()
    with connection() as db:
        db.execute('UPDATE cameras SET enabled=1 WHERE id=?', (camera['id'],))
    thread = threading.Thread(target=lambda: None)
    thread.start(); thread.join()
    worker = SimpleNamespace(last_frame=time.time(), raw_frame=np.zeros((240, 320, 3), np.uint8),
                             raw_jpeg=cv2.imencode(".jpg", np.full((240, 320, 3), 120, np.uint8))[1].tobytes(),
                             lock=threading.Lock(), thread=thread, stop_event=threading.Event(), encoding_threads=[])
    monkeypatch.setitem(workers.manager.workers, camera['id'], worker)
    def must_not_open(source):
        raise AssertionError('A running webcam must not be opened a second time.')
    monkeypatch.setattr(workers, 'open_capture', must_not_open)
    fake_devices(monkeypatch)
    base = f"/api/v1/people/{person['id']}/enrollment/preview"
    response = admin.post(base, json={'device_id': 'device:700'})
    assert response.status_code == 200
    token = response.json()['id']
    assert previews.sessions[token].camera_id == camera['id']
    assert admin.get(f'{base}/{token}').json()['ready']
    assert admin.delete(f'{base}/{token}').status_code == 200
    assert not worker.stop_event.is_set()


def test_preview_validates_device_person_and_role(admin, person, monkeypatch):
    fake_devices(monkeypatch)
    base = f"/api/v1/people/{person['id']}/enrollment/preview"
    assert admin.post(base, json={'device_id': 'http://untrusted/stream'}).status_code == 400
    assert admin.post(base, json={'device_id': 'device:1234'}).status_code == 400
    with connection() as db:
        db.execute('UPDATE people SET active=0 WHERE id=?', (person['id'],))
    assert admin.post(base, json={'device_id': 'device:700'}).status_code == 400
    credentials = {'username': 'viewer', 'password': 'viewer-password-123', 'role': 'operator'}
    admin.post('/api/v1/users', json=credentials)
    admin.post('/api/v1/auth/login', json=credentials)
    assert admin.get('/api/v1/enrollment/cameras').status_code == 403
    assert admin.post(base, json={'device_id': 'device:700'}).status_code == 403


def test_preview_is_owner_scoped_and_expires(admin, person):
    preview = previews.start(admin.get('/api/v1/auth/me').json()['id'], person['id'], camera_id='missing-camera')
    base = f"/api/v1/people/{person['id']}/enrollment/preview/{preview.id}"
    credentials = {'username': 'reviewer', 'password': 'reviewer-password-123', 'role': 'attendance'}
    admin.post('/api/v1/users', json=credentials)
    admin.post('/api/v1/auth/login', json=credentials)
    assert admin.get(base).status_code == 404
    assert preview.id in previews.sessions
    admin.post('/api/v1/auth/login', json={'username': 'admin', 'password': 'test-password-123'})
    preview.last_access = time.monotonic() - 21
    assert admin.get(base).status_code == 410
    assert preview.id not in previews.sessions


def test_preview_rejects_black_feed_with_overlay_lines():
    from app.modules.enrollment.preview import preview_image
    frame = np.zeros((480, 640, 3), np.uint8)
    cv2.line(frame, (0, 200), (639, 200), (0, 255, 0), 2)
    cv2.line(frame, (0, 260), (639, 260), (255, 190, 80), 2)
    result = preview_image(cv2.imencode('.jpg', frame)[1].tobytes())
    assert not result['ready']
    assert 'black or too dark' in result['error']
    assert 'image' not in result


def test_enrollment_preview_allows_active_frontend_origin(admin, person, monkeypatch):
    fake_devices(monkeypatch)
    base = f"/api/v1/people/{person['id']}/enrollment/preview"
    # Invalid device reaches route validation, proving origin middleware allowed it.
    response = admin.post(base, json={'device_id': 'device:missing'}, headers={'Origin': 'http://127.0.0.1:5175'})
    assert response.status_code == 400
    blocked = admin.post(base, json={'device_id': 'device:missing'}, headers={'Origin': 'https://untrusted.example'})
    assert blocked.status_code == 403
    assert 'frontend address' in blocked.json()['detail']


def test_enrollment_identifies_failed_sample_and_preserves_templates(admin, person, monkeypatch):
    from app.vision.engine import engine
    calls = []
    def enroll(content):
        calls.append(content)
        if len(calls) == 2:
            raise ValueError('No face detected. Retake this sample.')
        return [1.0, 0.0]
    monkeypatch.setattr(engine, 'enrollment', enroll)
    monkeypatch.setattr(engine, 'match', lambda *args, **kwargs: (None, 0))
    files = [('files', (f'capture-{i}.jpg', b'sample', 'image/jpeg')) for i in range(3)]
    result = admin.post(f"/api/v1/people/{person['id']}/enrollment", files=files)
    assert result.status_code == 422
    assert result.json()['detail'].startswith('Sample 2: No face detected.')
    assert not rows('SELECT * FROM face_templates')
