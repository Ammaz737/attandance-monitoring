# Local AI models

Face inference stays on this computer. No hosted inference key is required.

## Included CPU face baseline

`scripts/download_face_models.py` fetches YuNet (2023 OpenCV 4.x-compatible model)
and SFace from the official OpenCV Zoo repository, preserves their license files
and records download URLs and SHA-256 checksums in a local manifest.

```powershell
backend/.venv/Scripts/python.exe scripts/download_face_models.py
```

Set `ENABLE_AI=true` and `FACE_MODEL=sface` in `backend/.env` and restart.
The default 0.60 cosine threshold is conservative initial configuration, **not a
calibrated accuracy guarantee**. Test false matches, missed matches, lighting,
camera distance and ambiguity margins on representative footage.

YuNet and SFace sources and published license files:
- https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet
- https://github.com/opencv/opencv_zoo/tree/main/models/face_recognition_sface

## Person detection and tracking

```powershell
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements-ai.txt
```

Configure `DETECTOR_WEIGHTS` with an absolute path to official RF-DETR Small
weights. The engine uses CPU by default for a reproducible local baseline.
ByteTrack IDs are local to a camera/worker session. Body detections are matched
to faces geometrically; uncertain identities never become named attendance.

The included downloader verifies the checkpoint against the official package MD5
and saves its license and SHA-256 manifest:

```powershell
backend/.venv/Scripts/python.exe scripts/download_detector.py
```

Set `DETECTOR_WEIGHTS=./model_assets/rf-detr-small.pth` in `backend/.env`.
In this workspace, both detector and face weights have already been downloaded and
initialized successfully on CPU. `.env` enables AI but leaves automatic attendance off.

Sources:
- https://github.com/roboflow/rf-detr
- https://supervision.roboflow.com/latest/how_to/track_objects/
- https://trackers.roboflow.com/latest/api/trackers/

## Optional InsightFace

Set `FACE_MODEL` to your package name and provide **complete locally licensed**
ONNX package files in `backend/model_assets/models/<package>/`. Install InsightFace
and ONNX Runtime yourself. The app does not download InsightFace weights for you.
Public supplied InsightFace models are research-only unless separately licensed:
https://github.com/deepinsight/insightface

## Automatic attendance and limitations

`ALLOW_AUTOMATIC_ATTENDANCE=false` keeps directional crossings in the review queue.
Sightings and manual attendance still work. Setting it true enables camera IN/OUT
from repeated accepted face matches and body-track crossings. **There is no
liveness/anti-spoofing model in this version.** Never describe it as spoof-proof.

Recognition samples must be consented and quality controlled. Different embedding
models are not interchangeable: re-enroll after changing the face model. No
cross-camera appearance re-identification is implemented; each camera confirms
faces independently. Last-seen locations are evidence, not inferred positions.
