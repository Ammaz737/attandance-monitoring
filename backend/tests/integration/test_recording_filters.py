from app.db.database import connection, now, uid


def test_recordings_filter_by_location_and_combine_with_camera_person_date(admin, person):
    locations = [admin.post('/api/v1/locations', json={'name': name}).json() for name in ('Gate', 'Office')]
    cameras = [admin.post('/api/v1/cameras', json={'name': f'Camera {index}', 'location_id': location['id'], 'source': '0'}).json()
               for index, location in enumerate(locations)]
    stamp = now()
    ids = [uid(), uid()]
    with connection() as db:
        for index, camera in enumerate(cameras):
            db.execute('INSERT INTO recordings VALUES (?,?,?,?,?,?,?)', (ids[index], camera['id'], 'unused.mp4', stamp, stamp, 'ready', 100))
        db.execute('INSERT INTO sightings VALUES (?,?,?,?,?,?)', (uid(), person['id'], cameras[0]['id'], .9, '1', stamp))
    assert len(admin.get('/api/v1/recordings').json()) == 2
    filtered = admin.get('/api/v1/recordings', params={'location_id': locations[0]['id']}).json()
    assert [item['id'] for item in filtered] == [ids[0]]
    assert not admin.get('/api/v1/recordings', params={'location_id': locations[0]['id'], 'camera_id': cameras[1]['id']}).json()
    from app.core.helpers import date_window
    from app.core.config import TIMEZONE
    from datetime import datetime
    from zoneinfo import ZoneInfo
    day = datetime.fromisoformat(stamp).astimezone(ZoneInfo(TIMEZONE)).date().isoformat()
    result = admin.get('/api/v1/recordings', params={'location_id': locations[0]['id'], 'camera_id': cameras[0]['id'], 'person_id': person['id'], 'day': day})
    assert result.status_code == 200
    assert [item['id'] for item in result.json()] == [ids[0]]
    assert not admin.get('/api/v1/recordings', params={'location_id': 'missing'}).json()
