"""
GeoCoral — single-image inference.

Applies the same preprocessing used at training time (CLAHE -> resize
224x224 -> ImageNet normalization) to a single uploaded image and
returns the predicted class and probability. Intended to be called
from the Django upload view once a user submits a field photo, then
paired with its GPS coordinates for the geomapping interface.

CLI usage:
    python -m training.predict path/to/image.jpg
"""

import os
import sys

import cv2
import numpy as np
import tensorflow as tf

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from data_prep.prepare_dataset import apply_clahe

_model = None  # lazy-loaded singleton


def _get_model():
    global _model
    if _model is None:
        _model = tf.keras.models.load_model(config.BEST_MODEL_PATH)
    return _model


def preprocess_image(image_path):
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not read image at {image_path}")

    image = apply_clahe(image)
    image = cv2.resize(image, (config.IMG_SIZE, config.IMG_SIZE), interpolation=cv2.INTER_AREA)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0

    mean = np.array(config.IMAGENET_MEAN, dtype=np.float32)
    std = np.array(config.IMAGENET_STD, dtype=np.float32)
    image = (image - mean) / std

    return np.expand_dims(image, axis=0)


def predict(image_path, model_path=None):
    """Returns {"label": "healthy"|"bleached", "probability": float}
    where probability is the model's confidence in the predicted label."""
    model = _get_model() if model_path is None else tf.keras.models.load_model(model_path)
    batch = preprocess_image(image_path)
    prob_bleached = float(model.predict(batch, verbose=0)[0][0])

    if prob_bleached >= 0.5:
        return {"label": "bleached", "probability": prob_bleached}
    return {"label": "healthy", "probability": 1.0 - prob_bleached}


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m training.predict <image_path>")
        sys.exit(1)

    result = predict(sys.argv[1])
    print(f"Prediction: {result['label']} (confidence: {result['probability']:.4f})")
