from datetime import datetime, timezone
from app.db.database import connection, now, rows, uid
from app.core.security import decrypt
from app.core.helpers import date_window


def test_authentication_and_setup_lock(client):
    assert client.get('/api/v1/people').status_code == 401
    credentials = {'username': 'admin', 'password': 'test-password-123'}
    assert client.get('/api/v1/auth/status').json()['setup_required']
    assert client.post('/api/v1/auth/setup', json=credentials).status_code == 201
    assert client.post('/api/v1/auth/setup', json=credentials).status_code == 409
    assert client.post('/api/v1/auth/login', json={**credentials, 'password': 'wrong-password'}).status_code == 401
    result = client.post('/api/v1/auth/login', json=credentials)
    assert 'HttpOnly' in result.headers['set-cookie']
    assert client.get('/api/v1/auth/me').json()['role'] == 'admin'
    assert client.post('/api/v1/auth/logout').status_code == 200
    assert client.get('/api/v1/auth/me').status_code == 401


def test_people_persistence_and_validation(admin, person):
    data = admin.get('/api/v1/people').json()
    assert data[0]['id'] == person['id']
    assert data[0]['template_count'] == 0
    duplicate = {k: person[k] for k in ('name', 'employee_id', 'contact', 'department', 'consent')}
    assert admin.post('/api/v1/people', json=duplicate).status_code == 409
    assert admin.post('/api/v1/people', json={**duplicate, 'employee_id': 'EMP-002', 'consent': False}).status_code == 400
    assert admin.post('/api/v1/people', json={**duplicate, 'name': '  '}).status_code == 422
    assert admin.patch(f"/api/v1/people/{person['id']}", json={**duplicate, 'name': 'Ali Updated'}).status_code == 200
    assert admin.post(f"/api/v1/people/{person['id']}/toggle").status_code == 200
    assert admin.get('/api/v1/people').json()[0]['active'] == 0


def test_attendance_reentry_and_conflicts(admin, person):
    body = {'person_id': person['id'], 'kind': 'IN', 'reason': 'Verified at reception'}
    assert admin.post('/api/v1/attendance', json={**body, 'kind': 'OUT'}).status_code == 409
    assert admin.post('/api/v1/attendance', json=body).status_code == 200
    assert admin.post('/api/v1/attendance', json=body).status_code == 409
    assert admin.post(f"/api/v1/people/{person['id']}/toggle").status_code == 409
    assert admin.get('/api/v1/dashboard').json()['counts']['present'] == 1
    assert admin.post('/api/v1/attendance', json={**body, 'kind': 'OUT'}).status_code == 200
    assert admin.post('/api/v1/attendance', json=body).status_code == 200
    sessions = admin.get('/api/v1/attendance').json()
    assert len(sessions) == 2
    assert sum(row['out_at'] is None for row in sessions) == 1
    assert len(rows("SELECT * FROM audit_logs WHERE action='attendance.manual'")) == 3


def test_camera_source_protected_and_configuration(admin):
    location = admin.post('/api/v1/locations', json={'name': 'Reception'}).json()
    body = {'name': 'Gate camera', 'location_id': location['id'], 'source': 'rtsp://user:secret@10.0.0.2/live', 'role': 'both'}
    response = admin.post('/api/v1/cameras', json=body)
    assert response.status_code == 201, response.text
    camera = response.json()
    assert 'source' not in camera
    assert camera['status'] == 'stopped'
    stored = rows('SELECT source FROM cameras WHERE id=?', (camera['id'],))[0]['source']
    assert 'secret' not in stored
    assert decrypt(stored) == body['source']
    assert 'secret' not in admin.get('/api/v1/cameras').text
    assert admin.patch(f"/api/v1/cameras/{camera['id']}", json={**body, 'source': '', 'line_x': .65}).status_code == 200
    assert decrypt(rows('SELECT source FROM cameras WHERE id=?', (camera['id'],))[0]['source']) == body['source']
    assert admin.post('/api/v1/cameras', json={**body, 'source': 'file:///secret'}).status_code == 422
    assert admin.post('/api/v1/cameras', json={**body, 'line_x': 5}).status_code == 422


def test_permissions_and_origin(admin, person):
    credentials = {'username': 'viewer', 'password': 'viewer-password-123', 'role': 'operator'}
    assert admin.post('/api/v1/users', json=credentials).status_code == 201
    assert admin.post('/api/v1/auth/login', json=credentials).status_code == 200
    assert admin.get('/api/v1/people').status_code == 200
    assert admin.get('/api/v1/audit').status_code == 403
    assert admin.post('/api/v1/attendance', json={'person_id': person['id'], 'kind': 'IN', 'reason': 'Verified manually'}).status_code == 403
    assert admin.post('/api/v1/locations', json={'name': 'Blocked'}).status_code == 403
    assert admin.post('/api/v1/auth/logout', headers={'Origin': 'https://untrusted.example'}).status_code == 403


def test_no_fake_ai_and_enrollment_failure(admin, person):
    assert admin.get('/api/v1/sightings').json() == []
    assert admin.get('/api/v1/recordings').json() == []
    vision = admin.get('/api/v1/settings').json()['vision']
    assert not vision['face_ready'] and not vision['liveness_ready']
    files = [('files', (f'face-{i}.jpg', b'not-an-image', 'image/jpeg')) for i in range(3)]
    response = admin.post(f"/api/v1/people/{person['id']}/enrollment", files=files)
    assert response.status_code == 422
    assert admin.get('/api/v1/people').json()[0]['template_count'] == 0


def test_recording_expiry_and_csv(admin, person):
    location = admin.post('/api/v1/locations', json={'name': 'Hall'}).json()
    camera = admin.post('/api/v1/cameras', json={'name': 'Hall camera', 'location_id': location['id'], 'source': '0'}).json()
    record_id = uid()
    with connection() as db:
        db.execute('INSERT INTO recordings VALUES (?,?,?,?,?,?,?)', (record_id, camera['id'], '/missing.mp4', now(), now(), 'expired', 0))
    assert admin.get(f'/api/v1/recordings/{record_id}/file').status_code == 403
    assert admin.get('/api/v1/recordings').json()[0]['status'] == 'expired'
    admin.post('/api/v1/attendance', json={'person_id': person['id'], 'kind': 'IN', 'reason': 'Report verification'})
    from zoneinfo import ZoneInfo
    day = datetime.now(ZoneInfo('Asia/Karachi')).date()
    response = admin.get(f'/api/v1/reports/attendance.csv?day={day}')
    assert response.status_code == 200 and 'EMP-001' in response.text


def test_timezone_boundary():
    from datetime import date
    start, end = date_window(date(2026, 10, 19))
    assert start.startswith('2026-10-18T19:00:00')
    assert end.startswith('2026-10-19T19:00:00')


def test_camera_event_idempotency(admin, person):
    from app.modules.attendance.service import mark
    first = mark(person['id'], 'IN', 'Confirmed', event_key='camera-test-1')
    second = mark(person['id'], 'IN', 'Confirmed', event_key='camera-test-1')
    assert first['kind'] == 'IN'
    assert second == {'duplicate': True}
    assert len(rows('SELECT * FROM attendance_sessions')) == 1
