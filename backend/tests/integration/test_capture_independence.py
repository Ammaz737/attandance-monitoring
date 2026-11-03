import time
import numpy as np
from app.db.database import rows


def test_slow_inference_does_not_block_capture(admin, monkeypatch):
    import app.workers.manager as module
    location = admin.post('/api/v1/locations', json={'name': 'Synthetic capture test'}).json()
    camera = admin.post('/api/v1/cameras', json={'name': 'Capture test', 'location_id': location['id'], 'source': '0'}).json()
    worker = module.CameraWorker(rows('SELECT * FROM cameras WHERE id=?', (camera['id'],))[0])
    counts = {'capture': 0, 'inference': 0}

    class SyntheticCapture:
        def isOpened(self):
            return True

        def read(self):
            counts['capture'] += 1
            if counts['capture'] >= 25:
                worker.stop_event.set()
            return True, np.zeros((240, 320, 3), dtype=np.uint8)

        def release(self):
            pass

    def slow_inference(frame, tracker):
        counts['inference'] += 1
        time.sleep(.25)
        return []

    monkeypatch.setattr(module, 'open_capture', lambda source: SyntheticCapture())
    monkeypatch.setattr(module.engine, 'analyze', slow_inference)
    monkeypatch.setattr(module.engine, 'load', lambda: None)
    worker.thread.start()
    worker.thread.join(timeout=30)
    assert not worker.thread.is_alive()
    assert counts['capture'] == 25
    assert 0 < counts['inference'] < counts['capture']
    assert worker.jpeg and worker.analysis_jpeg
    assert worker.health == 'stopped'
