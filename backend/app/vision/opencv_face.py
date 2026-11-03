from types import SimpleNamespace
import cv2
import numpy as np


class OpenCVFace:
    """YuNet alignment + SFace embeddings on CPU, compatible with the face adapter."""

    def __init__(self, directory):
        self.detector = cv2.FaceDetectorYN.create(str(directory / 'face_detection_yunet_2023mar.onnx'), '', (320, 320), 0.8)
        self.recognizer = cv2.FaceRecognizerSF.create(str(directory / 'face_recognition_sface_2021dec.onnx'), '')

    def get(self, image):
        height, width = image.shape[:2]
        self.detector.setInputSize((width, height))
        _, faces = self.detector.detect(image)
        output = []
        if faces is None:
            return output
        for face in faces:
            aligned = self.recognizer.alignCrop(image, face)
            vector = self.recognizer.feature(aligned).flatten()
            vector = vector / (np.linalg.norm(vector) + 1e-8)
            x, y, w, h = face[:4]
            output.append(SimpleNamespace(bbox=np.array([x, y, x + w, y + h]),
                                          det_score=face[-1], normed_embedding=vector))
        return output
