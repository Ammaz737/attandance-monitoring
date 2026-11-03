"""Validate local model initialization and inference without a camera or person data."""
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from app.vision.engine import engine
from trackers import ByteTrackTracker

engine.load()
status = engine.status()
print(status)
assert status['face_ready'], 'Face weights did not load.'
assert status['detector_ready'], 'Person detector did not load.'
result = engine.analyze(np.zeros((480, 640, 3), dtype=np.uint8), ByteTrackTracker())
assert result == [], f'Blank frame unexpectedly produced detections: {result}'
print('PASS: detector, face adapter, ByteTrack and blank-frame inference.')
