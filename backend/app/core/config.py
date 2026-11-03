import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / '.env')
os.environ.setdefault('OPENCV_FFMPEG_LOGLEVEL', '-8')
STORAGE = Path(os.getenv('STORAGE_ROOT', str(ROOT / 'storage')))
if not STORAGE.is_absolute():
    STORAGE = ROOT / STORAGE
STORAGE.mkdir(parents=True, exist_ok=True)
DATABASE = Path(os.getenv('DATABASE_PATH', str(STORAGE / 'attendance.sqlite3')))
MODEL_ROOT = Path(os.getenv('MODEL_ROOT', str(ROOT / 'model_assets')))
if not MODEL_ROOT.is_absolute():
    MODEL_ROOT = ROOT / MODEL_ROOT
TIMEZONE = os.getenv('APP_TIMEZONE', 'Asia/Karachi')
ORIGINS = os.getenv('FRONTEND_ORIGIN', 'http://localhost:5173,http://127.0.0.1:5173,http://localhost:5175,http://127.0.0.1:5175,http://localhost:8000,http://127.0.0.1:8000').split(',')
COOKIE_SECURE = os.getenv('COOKIE_SECURE', 'false').lower() == 'true'
FACE_MODEL = os.getenv('FACE_MODEL', 'sface')
FACE_THRESHOLD = float(os.getenv('FACE_THRESHOLD', '0.60'))
FACE_MARGIN = float(os.getenv('FACE_MARGIN', '0.08'))
ENABLE_AI = os.getenv('ENABLE_AI', 'false').lower() == 'true'
DETECTOR_WEIGHTS = os.getenv('DETECTOR_WEIGHTS', '')
if DETECTOR_WEIGHTS and not Path(DETECTOR_WEIGHTS).is_absolute():
    DETECTOR_WEIGHTS = str(ROOT / DETECTOR_WEIGHTS)
ALLOW_AUTOMATIC_ATTENDANCE = os.getenv('ALLOW_AUTOMATIC_ATTENDANCE', 'false').lower() == 'true'

# Exact numeric webcam sources requiring a horizontal driver correction.
FLIP_WEBCAM_SOURCES = {source.strip() for source in os.getenv("FLIP_WEBCAM_SOURCES", "").split(",") if source.strip().isdigit()}
