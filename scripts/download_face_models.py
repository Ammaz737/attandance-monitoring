"""Download the OpenCV CPU face baseline from official OpenCV repositories.

Usage: backend/.venv/Scripts/python.exe scripts/download_face_models.py
Downloads are inbound only. No enrollment images or templates leave this computer.
"""
import hashlib
import json
import urllib.request
from pathlib import Path

root = Path(__file__).resolve().parents[1]
destination = root / 'backend' / 'model_assets' / 'models' / 'sface'
destination.mkdir(parents=True, exist_ok=True)
models = {
    'face_detection_yunet_2023mar.onnx': 'face_detection_yunet',
    'face_recognition_sface_2021dec.onnx': 'face_recognition_sface',
}
manifest = []
for filename, directory in models.items():
    url = f'https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/{directory}/{filename}'
    target = destination / filename
    if not target.exists():
        temporary = target.with_suffix('.download')
        print(f'Downloading {filename}...')
        urllib.request.urlretrieve(url, temporary)
        if temporary.stat().st_size < 100000:
            raise RuntimeError('Model download is incomplete. No configuration was changed.')
        temporary.replace(target)
    license_url = f'https://raw.githubusercontent.com/opencv/opencv_zoo/main/models/{directory}/LICENSE'
    urllib.request.urlretrieve(license_url, destination / f'{directory}.LICENSE')
    manifest.append({'file': filename, 'source': url, 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
                     'license_file': f'{directory}.LICENSE'})
(destination / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print('Face models ready. Set ENABLE_AI=true and FACE_MODEL=sface in backend/.env, then restart.')
