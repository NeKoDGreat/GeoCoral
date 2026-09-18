"""
GeoCoral — bridge to the ML training project's inference code.

The ML project (config.py, training/, data_prep/) lives one directory
above this Django project (see ML_PROJECT_ROOT in settings.py). This
module adds it to sys.path once and reuses training.predict.predict()
directly, so preprocessing (CLAHE, resize, ImageNet normalization) and
the loaded model stay in sync with training/predict.py rather than
duplicating that logic here.
"""

import sys

from django.conf import settings

_ml_path_added = False


def _ensure_ml_project_on_path():
    global _ml_path_added
    if not _ml_path_added:
        sys.path.insert(0, str(settings.ML_PROJECT_ROOT))
        _ml_path_added = True


def classify_image(image_path):
    """Runs the trained ResNet50 classifier on an uploaded image.

    Returns {"label": "healthy"|"bleached", "probability": float}.
    Raises FileNotFoundError if no trained model checkpoint exists yet
    at settings.GEOCORAL_MODEL_PATH — run training/train.py first.
    """
    _ensure_ml_project_on_path()
    from training.predict import predict  # imported lazily so Django can
                                           # start up even before TensorFlow
                                           # / a trained model are available

    return predict(image_path, model_path=settings.GEOCORAL_MODEL_PATH)
