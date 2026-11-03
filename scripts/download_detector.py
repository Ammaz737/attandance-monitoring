"""Download the official Apache-designated RF-DETR Small checkpoint."""
import hashlib
import json
import urllib.request
import importlib.metadata
from pathlib import Path

root = Path(__file__).resolve().parents[1]
destination = root / 'backend' / 'model_assets'
destination.mkdir(parents=True, exist_ok=True)
target = destination / 'rf-detr-small.pth'
url = 'https://storage.googleapis.com/rfdetr/small_coco/checkpoint_best_regular.pth'
expected_md5 = 'fb37061c1af7bace359c91b723a8d5c1'
if not target.exists():
    print('Downloading official RF-DETR Small weights...')
    temporary = target.with_suffix('.download')
    urllib.request.urlretrieve(url, temporary)
    digest = hashlib.md5(temporary.read_bytes()).hexdigest()
    if digest != expected_md5:
        temporary.unlink(missing_ok=True)
        raise RuntimeError('Checkpoint checksum differs from the official package manifest.')
    temporary.replace(target)
distribution = importlib.metadata.distribution('rfdetr')
license_files = [file for file in distribution.files or [] if str(file).endswith('licenses/LICENSE')]
if not license_files:
    raise RuntimeError('Install the official rfdetr package to preserve its license file.')
(destination / 'RF-DETR.LICENSE').write_bytes(distribution.locate_file(license_files[0]).read_bytes())
(destination / 'rf-detr-small.manifest.json').write_text(json.dumps({
    'file': target.name, 'source': url, 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
    'official_md5': expected_md5, 'license': 'RF-DETR.LICENSE',
}, indent=2), encoding='utf-8')
print('Detector ready. Set DETECTOR_WEIGHTS=./model_assets/rf-detr-small.pth and ENABLE_AI=true.')
