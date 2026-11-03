import numpy as np
from app.workers.manager import CorrectedCapture


def test_webcam_correction_flips_pixels_and_preserves_capture_lifecycle():
    class Capture:
        released = False
        def read(self):
            return True, np.array([[[10, 20, 30], [70, 80, 90]]], dtype=np.uint8)
        def isOpened(self): return True
        def release(self): self.released = True
    capture = Capture()
    corrected = CorrectedCapture(capture)
    ok, frame = corrected.read()
    assert ok and corrected.isOpened()
    assert frame.tolist() == [[[70, 80, 90], [10, 20, 30]]]
    corrected.release()
    assert capture.released


def test_webcam_correction_handles_failed_read():
    class Capture:
        def read(self): return False, None
    assert CorrectedCapture(Capture()).read() == (False, None)
