import json
import threading
import time
from pathlib import Path
import cv2
import numpy as np
from app.core import config
from app.core.security import decrypt
from app.db.database import rows


class VisionEngine:
    """Local-only weights. Never silently download biometric models."""

    def __init__(self):
        self.face = None
        self.detector = None
        self.model_name = config.FACE_MODEL
        self.lock = threading.RLock()
        self.attempted = False
        self.error = 'AI disabled. Configure local model weights and ENABLE_AI=true.'

    def load(self):
        with self.lock:
            if self.attempted or not config.ENABLE_AI:
                return
            self.attempted = True
            errors = []
            face_dir = config.MODEL_ROOT / 'models' / self.model_name
            if self.model_name == 'sface' and (face_dir / 'face_recognition_sface_2021dec.onnx').is_file() and (face_dir / 'face_detection_yunet_2023mar.onnx').is_file():
                try:
                    from app.vision.opencv_face import OpenCVFace
                    self.face = OpenCVFace(face_dir)
                except Exception:
                    errors.append('OpenCV face models failed to load. Check ONNX files.')
            elif self.model_name != 'sface' and face_dir.is_dir() and list(face_dir.glob('*.onnx')):
                try:
                    from insightface.app import FaceAnalysis
                    self.face = FaceAnalysis(name=self.model_name, root=str(config.MODEL_ROOT),
                                             allowed_modules=['detection', 'recognition'],
                                             providers=['CPUExecutionProvider'])
                    self.face.prepare(ctx_id=-1, det_size=(640, 640))
                except Exception:
                    self.face = None
                    errors.append('Face model failed to initialize. Check dependencies and ONNX files.')
            else:
                errors.append(f'Face model missing: model_assets/models/{self.model_name}/')
            if config.DETECTOR_WEIGHTS and Path(config.DETECTOR_WEIGHTS).is_file():
                try:
                    from rfdetr import RFDETRSmall
                    self.detector = RFDETRSmall(pretrain_weights=config.DETECTOR_WEIGHTS, device='cpu')
                except Exception:
                    errors.append('RF-DETR failed to initialize. Check weights and AI dependencies.')
            else:
                errors.append('RF-DETR local weights not configured.')
            self.error = ' '.join(errors)

    def status(self):
        return {'enabled': config.ENABLE_AI, 'face_ready': self.face is not None,
                'detector_ready': self.detector is not None, 'model': self.model_name,
                'message': self.error, 'liveness_ready': False,
                'automatic_attendance': config.ALLOW_AUTOMATIC_ATTENDANCE,
                'threshold': config.FACE_THRESHOLD, 'margin': config.FACE_MARGIN}

    def enrollment(self, content):
        self.load()
        if self.face is None:
            raise RuntimeError(self.error or 'Face recognition model unavailable.')
        image = cv2.imdecode(np.frombuffer(content, np.uint8), cv2.IMREAD_COLOR)
        if image is None or image.shape[0] * image.shape[1] > 20000000:
            raise ValueError('Upload a valid image under 20 megapixels.')
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        if cv2.Laplacian(gray, cv2.CV_64F).var() < 35:
            raise ValueError('Image is too blurry. Capture a sharper face.')
        with self.lock:
            faces = self.face.get(image)
        if not faces:
            raise ValueError('No face detected. Face the camera, move closer, and use front lighting. Retake this sample.')
        if len(faces) > 1:
            raise ValueError(f'{len(faces)} faces detected. Keep only the enrolling person in view, including mirrors and screens. Retake this sample.')
        face = faces[0]
        if float(face.det_score) < 0.75 or min(face.bbox[2:] - face.bbox[:2]) < 80:
            raise ValueError('Move closer and use better lighting for a clear face.')
        return face.normed_embedding.tolist()

    def match(self, embedding, exclude=None):
        samples = rows('''SELECT f.*,p.active FROM face_templates f JOIN people p ON p.id=f.person_id
                          WHERE p.active=1 AND f.model=?''', (self.model_name,))
        scores = {}
        vector = np.asarray(embedding, dtype=np.float32)
        for sample in samples:
            if sample['person_id'] == exclude:
                continue
            template = np.asarray(json.loads(decrypt(sample['embedding'])), dtype=np.float32)
            similarity = float(np.dot(vector, template) / (np.linalg.norm(vector) * np.linalg.norm(template) + 1e-8))
            scores[sample['person_id']] = max(scores.get(sample['person_id'], -1), similarity)
        ranking = sorted(scores.items(), key=lambda pair: pair[1], reverse=True)
        if not ranking:
            return None, 0.0
        person_id, score = ranking[0]
        runner_up = ranking[1][1] if len(ranking) > 1 else -1
        if score < config.FACE_THRESHOLD or score - runner_up < config.FACE_MARGIN:
            return None, score
        return person_id, score

    def analyze(self, frame, tracker=None):
        self.load()
        result = []
        with self.lock:
            if self.detector is not None:
                from PIL import Image
                detected = self.detector.predict(Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)), threshold=0.4)
                # RF-DETR uses COCO category IDs; person is category 1.
                detected = detected[detected.class_id == 1]
                if tracker is not None:
                    detected = tracker.update(detected, timestamp=time.monotonic())
                for index, box in enumerate(detected.xyxy):
                    track_id = str(int(detected.tracker_id[index])) if detected.tracker_id is not None else None
                    result.append({'box': box.tolist(), 'track_id': track_id, 'person_id': None, 'confidence': 0.0})
            if self.face is not None:
                for face in self.face.get(frame):
                    if float(face.det_score) < 0.75 or min(face.bbox[2:] - face.bbox[:2]) < 60:
                        continue
                    person_id, confidence = self.match(face.normed_embedding)
                    center = (face.bbox[:2] + face.bbox[2:]) / 2
                    candidates = [item for item in result if item['box'][0] <= center[0] <= item['box'][2]
                                  and item['box'][1] <= center[1] <= item['box'][3]]
                    if candidates:
                        target = min(candidates, key=lambda item: (item['box'][2]-item['box'][0]) * (item['box'][3]-item['box'][1]))
                        target.update(person_id=person_id, confidence=confidence)
                    else:
                        result.append({'box': face.bbox.tolist(), 'track_id': None, 'person_id': person_id,
                                       'confidence': confidence})
        return result


engine = VisionEngine()
