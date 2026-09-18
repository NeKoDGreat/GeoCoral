"""
GeoCoral — central configuration.

Values here mirror the Methodology chapter of the GeoCoral capstone
proposal (Hardware and Software Specifications, Data Collection and
Dataset Preparation, Image Preprocessing and Augmentation, Model
Development and Transfer Learning, Model Training and Hyperparameter
Tuning).
"""

import os

# ----------------------------------------------------------------------
# Paths
# ----------------------------------------------------------------------
# RAW_LOCAL_DIR: field images captured by authorized divers in the three
#   selected Samal Island marine sanctuaries, organized as:
#     RAW_LOCAL_DIR/healthy/*.jpg
#     RAW_LOCAL_DIR/bleached/*.jpg
#   plus a metadata CSV (see data_prep/prepare_dataset.py) carrying GPS
#   coordinates, date/time, depth, sanctuary location, area code, and
#   photographer for each image.
#
# RAW_KAGGLE_DIR: the supplementary public "Bleached and Unbleached
#   Corals Classification" dataset (Kaggle, sonainjamil). Used only to
#   grow the training set — these images carry no field GPS data and
#   are therefore excluded from the geomapping interface.
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

RAW_LOCAL_DIR = os.path.join(PROJECT_ROOT, "raw_data", "local_field_images")
RAW_KAGGLE_DIR = os.path.join(PROJECT_ROOT, "raw_data", "kaggle_bleached_corals")
LOCAL_METADATA_CSV = os.path.join(RAW_LOCAL_DIR, "metadata.csv")

PROCESSED_DIR = os.path.join(PROJECT_ROOT, "processed_data")
SPLIT_DIRS = {
    "train": os.path.join(PROCESSED_DIR, "train"),
    "val": os.path.join(PROCESSED_DIR, "val"),
    "test": os.path.join(PROCESSED_DIR, "test"),
}
SPLIT_METADATA_CSV = os.path.join(PROCESSED_DIR, "split_metadata.csv")

MODEL_DIR = os.path.join(PROJECT_ROOT, "saved_models")
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
BEST_MODEL_PATH = os.path.join(MODEL_DIR, "geocoral_resnet50_best.keras")
FINAL_MODEL_PATH = os.path.join(MODEL_DIR, "geocoral_resnet50_final.keras")

# ----------------------------------------------------------------------
# Classes
# ----------------------------------------------------------------------
# Binary classification: index 0 = healthy, index 1 = bleached.
# A system meant for conservation planning must recognize both a
# healthy baseline and bleaching, not just detect bleaching in isolation.
CLASS_NAMES = ["healthy", "bleached"]
POSITIVE_CLASS = "bleached"  # the class the sigmoid output represents (label 1)

# ----------------------------------------------------------------------
# Dataset split (Data Collection and Dataset Preparation)
# ----------------------------------------------------------------------
# Stratified 70% / 15% / 15% train / val / test, preserving class balance
# in every subset.
TRAIN_SPLIT = 0.70
VAL_SPLIT = 0.15
TEST_SPLIT = 0.15
RANDOM_SEED = 42

# ----------------------------------------------------------------------
# Image preprocessing (Image Preprocessing and Augmentation)
# ----------------------------------------------------------------------
IMG_SIZE = 224  # ResNet50 input dimensions
IMG_CHANNELS = 3

# CLAHE parameters (contrast-limited adaptive histogram equalization),
# applied to correct light attenuation / haze / color distortion typical
# of underwater photographs, before resizing and normalization.
CLAHE_CLIP_LIMIT = 2.0
CLAHE_TILE_GRID_SIZE = (8, 8)

# ImageNet mean/std (RGB, 0-1 scale) — ResNet50 was pretrained on these
# statistics, so inputs are normalized to match.
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

# Data augmentation — training subset only. Validation and test subsets
# are preprocessed (CLAHE + resize + normalize) but never augmented, so
# reported performance reflects realistic, unmodified images.
AUGMENTATION = {
    "rotation_range_deg": 20,
    "horizontal_flip": True,
    "vertical_flip": True,
    "zoom_range": 0.15,
    "brightness_range": (0.8, 1.2),   # multiplicative jitter
    "contrast_range": (0.8, 1.2),     # multiplicative jitter
}

# ----------------------------------------------------------------------
# Model / transfer learning (Model Development and Transfer Learning)
# ----------------------------------------------------------------------
DROPOUT_RATE = 0.3

# Two-phase transfer learning strategy:
#   Phase 1 ("head training"): ResNet50 convolutional base frozen,
#     only the new classification head is trained.
#   Phase 2 ("fine-tuning"): final residual blocks unfrozen and trained
#     jointly with the head at a lower learning rate.
# ResNet50's last residual stage ("conv5_block*") is unfrozen for phase 2.
FINE_TUNE_AT_LAYER_PREFIX = "conv5_block"

# ----------------------------------------------------------------------
# Training / hyperparameters (Model Training and Hyperparameter Tuning)
# ----------------------------------------------------------------------
BATCH_SIZE = 32
HEAD_LEARNING_RATE = 1e-4
FINE_TUNE_LEARNING_RATE = 1e-5

HEAD_EPOCHS = 30       # max epochs for phase 1 (early stopping usually stops sooner)
FINE_TUNE_EPOCHS = 30  # max epochs for phase 2

EARLY_STOPPING_PATIENCE = 5
EARLY_STOPPING_MONITOR = "val_loss"

SHUFFLE_BUFFER = 1000
