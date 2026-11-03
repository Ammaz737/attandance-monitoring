import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import cv2
import numpy as np
from app.db.database import rows


def test_session_correction_preserves_original_event(admin, person):
    body = {'person_id': person['id'], 'kind': 'IN', 'reason': 'Verified at reception'}
    event = admin.post('/api/v1/attendance', json=body).json()
    session = admin.get('/api/v1/attendance').json()[0]
    start = datetime.now(timezone.utc) - timedelta(hours=2)
    end = datetime.now(timezone.utc) - timedelta(hours=1)
    response = admin.patch(f"/api/v1/attendance/{session['id']}", json={
        'in_at': start.isoformat(), 'out_at': end.isoformat(), 'reason': 'Verified missing exit from gate log'})
    assert response.status_code == 200, response.text
    assert rows('SELECT * FROM attendance_events WHERE id=?', (event['id'],))[0]['occurred_at'] == event['occurred_at']
    assert rows('SELECT * FROM attendance_sessions')[0]['out_at'] == end.isoformat()
    assert rows("SELECT * FROM audit_logs WHERE action='attendance.corrected'")
    assert admin.get('/api/v1/dashboard').json()['counts']['present'] == 0


def test_recording_encode_and_authorized_playback(admin):
    from app.core.config import STORAGE
    from app.workers.manager import CameraWorker, ffmpeg_path
    from app.db.database import connection, now, uid
    assert ffmpeg_path(), 'Project-local FFmpeg is required for this integration test.'
    location = admin.post('/api/v1/locations', json={'name': 'Synthetic media test'}).json()
    camera = admin.post('/api/v1/cameras', json={'name': 'Synthetic camera', 'location_id': location['id'], 'source': '0'}).json()
    worker = CameraWorker(camera)
    folder = STORAGE / 'recordings' / camera['id']
    folder.mkdir(parents=True, exist_ok=True)
    raw = folder / 'synthetic.avi'
    writer = cv2.VideoWriter(str(raw), cv2.VideoWriter_fourcc(*'MJPG'), 10, (320, 240))
    assert writer.isOpened()
    for index in range(20):
        image = np.zeros((240, 320, 3), dtype=np.uint8)
        cv2.rectangle(image, (10 + index, 20), (80 + index, 150), (70, 150, 80), -1)
        writer.write(image)
    record_id = uid()
    with connection() as db:
        db.execute('INSERT INTO recordings VALUES (?,?,?,?,?,?,?)', (record_id, camera['id'], str(raw), now(), None, 'recording', 0))
    worker.finish_recording(writer, record_id, raw)
    stored = rows('SELECT * FROM recordings WHERE id=?', (record_id,))[0]
    assert stored['status'] == 'ready', worker.record_error
    response = admin.get(f'/api/v1/recordings/{record_id}/file')
    assert response.status_code == 200
    assert response.headers['content-type'] == 'video/mp4'
    assert len(response.content) > 1000
    assert admin.get(f'/api/v1/recordings/{record_id}/file', headers={'Range': 'bytes=0-99'}).status_code == 206


def test_crossing_requires_repeated_identity_and_creates_review(admin, person, monkeypatch):
    import app.workers.manager as module
    from app.workers.manager import CameraWorker
    location = admin.post('/api/v1/locations', json={'name': 'Test gate'}).json()
    camera = admin.post('/api/v1/cameras', json={'name': 'Test entrance', 'location_id': location['id'], 'source': '0', 'role': 'both'}).json()
    monkeypatch.setattr(module, 'ALLOW_AUTOMATIC_ATTENDANCE', False)
    worker = CameraWorker(camera)
    item = {'person_id': person['id'], 'track_id': '1', 'confidence': .9, 'box': [0, 0, 40, 100]}
    from app.db.database import now
    worker.handle_evidence([item], 100, now())
    worker.handle_evidence([item], 100, now())
    assert not rows('SELECT * FROM sightings')
    worker.handle_evidence([item], 100, now())
    assert len(rows('SELECT * FROM sightings')) == 1
    item['box'] = [60, 0, 100, 100]
    worker.handle_evidence([item], 100, now())
    assert len(rows('SELECT * FROM review_items')) == 1
    assert not rows('SELECT * FROM attendance_sessions')


def test_vertical_crossing_uses_width_and_configured_entry_direction(admin, person, monkeypatch):
    import app.workers.manager as module
    from app.workers.manager import CameraWorker
    from app.db.database import now
    location = admin.post('/api/v1/locations', json={'name': 'Side gate'}).json()
    camera = admin.post('/api/v1/cameras', json={'name': 'Vertical gate', 'location_id': location['id'],
        'source': '0', 'role': 'both', 'line_x': .5, 'entry_direction': 'left'}).json()
    monkeypatch.setattr(module, 'ALLOW_AUTOMATIC_ATTENDANCE', False)
    worker = CameraWorker(camera)
    item = {'person_id': person['id'], 'track_id': '1', 'confidence': .9, 'box': [140, 0, 180, 30]}
    for _ in range(3): worker.handle_evidence([item], 200, now())
    # Up/down motion on the same side of a vertical line must not count.
    item['box'] = [140, 80, 180, 120]
    worker.handle_evidence([item], 200, now())
    assert not rows('SELECT * FROM review_items')
    item['box'] = [20, 80, 60, 120]
    worker.handle_evidence([item], 200, now())
    reviews = rows('SELECT * FROM review_items')
    assert len(reviews) == 1 and reviews[0]['message'].startswith('IN crossing')
    item['box'] = [140, 80, 180, 120]
    worker.handle_evidence([item], 200, now())
    reviews = rows('SELECT * FROM review_items')
    assert len(reviews) == 2 and reviews[1]['message'].startswith('OUT crossing')


def test_legacy_camera_settings_migrate_to_vertical(admin):
    from app.db.database import connection, init_db
    location = admin.post('/api/v1/locations', json={'name': 'Migration gate'}).json()
    camera = admin.post('/api/v1/cameras', json={'name': 'Old camera', 'location_id': location['id'], 'source': '0', 'line_x': .65}).json()
    with connection() as db:
        db.execute('ALTER TABLE cameras RENAME COLUMN line_x TO line_y')
        db.execute("UPDATE cameras SET entry_direction='up' WHERE id=?", (camera['id'],))
    init_db()
    init_db()  # Migration is safe on subsequent startups too.
    migrated = rows('SELECT * FROM cameras WHERE id=?', (camera['id'],))[0]
    assert migrated['line_x'] == .65
    assert migrated['entry_direction'] == 'left'
    assert 'line_y' not in migrated
