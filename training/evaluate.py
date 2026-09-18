"""
GeoCoral — model evaluation on the held-out test set.

Reports accuracy, precision, recall, and F1-score (Model Evaluation
Metrics), plus a confusion matrix, matching the requirement that the
trained model be evaluated on a separate test dataset before
integration into the web/mobile application.

Run:
    python -m training.evaluate
"""

import os
import sys

import numpy as np
import tensorflow as tf
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from training.dataset import get_test_dataset


def evaluate(model_path=None):
    model_path = model_path or config.BEST_MODEL_PATH
    print(f"Loading model from {model_path}...")
    model = tf.keras.models.load_model(model_path)

    print("Loading test dataset...")
    test_ds, n_test = get_test_dataset()
    print(f"Test images: {n_test}")

    y_true, y_pred_prob = [], []
    for images, labels in test_ds:
        probs = model.predict(images, verbose=0).flatten()
        y_pred_prob.extend(probs.tolist())
        y_true.extend(labels.numpy().tolist())

    y_true = np.array(y_true)
    y_pred_prob = np.array(y_pred_prob)
    y_pred = (y_pred_prob >= 0.5).astype(int)

    accuracy = accuracy_score(y_true, y_pred)
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    cm = confusion_matrix(y_true, y_pred)

    print("\n=== Test Set Results ===")
    print(f"Accuracy:  {accuracy:.4f}")
    print(f"Precision: {precision:.4f}  (positive class: '{config.POSITIVE_CLASS}')")
    print(f"Recall:    {recall:.4f}")
    print(f"F1-score:  {f1:.4f}")

    print("\nConfusion matrix (rows=true, cols=predicted):")
    print(f"           {config.CLASS_NAMES[0]:>10} {config.CLASS_NAMES[1]:>10}")
    for i, row in enumerate(cm):
        print(f"{config.CLASS_NAMES[i]:>10} {row[0]:>10} {row[1]:>10}")

    print("\nFull classification report:")
    print(classification_report(y_true, y_pred, target_names=config.CLASS_NAMES, zero_division=0))

    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "confusion_matrix": cm.tolist(),
    }


if __name__ == "__main__":
    evaluate()
