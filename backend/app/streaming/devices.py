"""Enumerate local video inputs without opening or recording their streams."""
import sys
import cv2


def discover_webcams():
    from cv2_enumerate_cameras import enumerate_cameras

    # Query one native backend to avoid listing the same camera twice.
    backend = cv2.CAP_DSHOW if sys.platform == 'win32' else cv2.CAP_AVFOUNDATION if sys.platform == 'darwin' else cv2.CAP_V4L2
    devices = []
    seen = set()
    for info in enumerate_cameras(backend):
        # CAP_ANY VideoCapture accepts backend + device index. Preserve the exact
        # native backend so a selection opens the camera that was enumerated.
        source = str(int(info.backend) + int(info.index))
        if source in seen:
            continue
        seen.add(source)
        devices.append({'source': source, 'name': info.name or f'Webcam {len(devices) + 1}'})
    return devices
