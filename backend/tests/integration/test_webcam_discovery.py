from types import SimpleNamespace


def test_discovery_returns_names_and_capture_indices(admin, monkeypatch):
    import app.streaming.devices as devices
    monkeypatch.setattr(devices, 'discover_webcams', lambda: [{'name': 'Integrated Camera', 'source': '700'}])
    response = admin.get('/api/v1/cameras/webcams')
    assert response.status_code == 200
    assert response.json() == {'devices': [{'name': 'Integrated Camera', 'source': '700'}]}


def test_discovery_handles_no_devices_and_errors(admin, monkeypatch):
    import app.streaming.devices as devices
    monkeypatch.setattr(devices, 'discover_webcams', lambda: [])
    assert admin.get('/api/v1/cameras/webcams').json() == {'devices': []}
    def unavailable():
        raise RuntimeError('private device path must not leak')
    monkeypatch.setattr(devices, 'discover_webcams', unavailable)
    result = admin.get('/api/v1/cameras/webcams')
    assert result.status_code == 503
    assert 'private device path' not in result.text


def test_discovery_requires_administrator(admin):
    credentials = {'username': 'viewer', 'password': 'viewer-password-123', 'role': 'operator'}
    admin.post('/api/v1/users', json=credentials)
    admin.post('/api/v1/auth/login', json=credentials)
    assert admin.get('/api/v1/cameras/webcams').status_code == 403


def test_native_enumeration_does_not_open_video(monkeypatch):
    import cv2
    import cv2_enumerate_cameras
    import app.streaming.devices as devices
    monkeypatch.setattr(devices.sys, 'platform', 'win32')
    def enumerate_devices(backend):
        assert backend == cv2.CAP_DSHOW
        return [SimpleNamespace(index=0, backend=backend, name='USB Camera', path='sensitive-path'),
                SimpleNamespace(index=0, backend=backend, name='USB Camera', path='sensitive-path')]
    monkeypatch.setattr(cv2_enumerate_cameras, 'enumerate_cameras', enumerate_devices)
    def must_not_open(*args):
        raise AssertionError('Discovery should not capture video.')
    monkeypatch.setattr(cv2, 'VideoCapture', must_not_open)
    assert devices.discover_webcams() == [{'source': '700', 'name': 'USB Camera'}]


def test_webcam_registration_round_trip(admin):
    location = admin.post('/api/v1/locations', json={'name': 'Desk'}).json()
    camera = admin.post('/api/v1/cameras', json={'name': 'USB Camera', 'location_id': location['id'], 'source': '700'}).json()
    assert camera['source_type'] == 'webcam'
    assert camera['webcam_source'] == '700'
    assert 'source' not in camera
