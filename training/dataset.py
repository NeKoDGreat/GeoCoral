"""
GeoCoral — tf.data input pipeline.

Images are already CLAHE-corrected and resized to 224x224 by
data_prep/prepare_dataset.py. This module handles:
  - loading from processed_data/{split}/{label}/*.jpg
  - ImageNet mean/std normalization (all splits)
  - data augmentation (train split only): rotation, horizontal/vertical
    flip, zoom, brightness/contrast jitter
"""

import os
import sys

import tensorflow as tf

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

AUTOTUNE = tf.data.AUTOTUNE


def _list_files_and_labels(split_dir):
    file_paths, labels = [], []
    for label_idx, class_name in enumerate(config.CLASS_NAMES):
        class_dir = os.path.join(split_dir, class_name)
        if not os.path.isdir(class_dir):
            continue
        for fname in os.listdir(class_dir):
            if fname.lower().endswith((".jpg", ".jpeg", ".png")):
                file_paths.append(os.path.join(class_dir, fname))
                labels.append(label_idx)
    return file_paths, labels


def _decode_image(path):
    raw = tf.io.read_file(path)
    image = tf.io.decode_image(raw, channels=3, expand_animations=False)
    image.set_shape([None, None, 3])
    image = tf.image.resize(image, [config.IMG_SIZE, config.IMG_SIZE])
    image = tf.cast(image, tf.float32) / 255.0
    return image


def _normalize(image):
    """ImageNet mean/std normalization, matching ResNet50 pretraining stats."""
    mean = tf.constant(config.IMAGENET_MEAN, dtype=tf.float32)
    std = tf.constant(config.IMAGENET_STD, dtype=tf.float32)
    return (image - mean) / std


# Augmentation layers are stateful (each holds a random-seed Variable), so
# they must be created exactly once at module scope rather than inside the
# per-image function passed to Dataset.map — creating them per-call trips
# "tf.function only supports singleton tf.Variables created on the first
# call" once the map function is traced.
_rotation_layer = tf.keras.layers.RandomRotation(
    factor=config.AUGMENTATION["rotation_range_deg"] / 360.0, fill_mode="reflect"
)
_zoom_layer = tf.keras.layers.RandomZoom(
    height_factor=(-config.AUGMENTATION["zoom_range"], config.AUGMENTATION["zoom_range"]),
    fill_mode="reflect",
)


def _augment(image):
    """Random augmentation applied only to the training subset."""
    aug = config.AUGMENTATION

    if aug["horizontal_flip"]:
        image = tf.image.random_flip_left_right(image)
    if aug["vertical_flip"]:
        image = tf.image.random_flip_up_down(image)

    image = _rotation_layer(image, training=True)
    image = _zoom_layer(image, training=True)

    lo, hi = aug["brightness_range"]
    image = tf.image.random_brightness(image, max_delta=(hi - lo) / 2.0)

    lo, hi = aug["contrast_range"]
    image = tf.image.random_contrast(image, lower=lo, upper=hi)

    image = tf.clip_by_value(image, 0.0, 1.0)
    return image


def _make_dataset(split_name, augment, shuffle):
    split_dir = config.SPLIT_DIRS[split_name]
    file_paths, labels = _list_files_and_labels(split_dir)

    if not file_paths:
        raise FileNotFoundError(
            f"No images found in {split_dir}. "
            f"Run data_prep/prepare_dataset.py first."
        )

    ds = tf.data.Dataset.from_tensor_slices((file_paths, labels))

    if shuffle:
        ds = ds.shuffle(buffer_size=min(config.SHUFFLE_BUFFER, len(file_paths)),
                         seed=config.RANDOM_SEED, reshuffle_each_iteration=True)

    def _load(path, label):
        image = _decode_image(path)
        if augment:
            image = _augment(image)
        image = _normalize(image)
        return image, tf.cast(label, tf.float32)

    ds = ds.map(_load, num_parallel_calls=AUTOTUNE)
    ds = ds.batch(config.BATCH_SIZE)
    ds = ds.prefetch(AUTOTUNE)
    return ds, len(file_paths)


def get_train_dataset():
    return _make_dataset("train", augment=True, shuffle=True)


def get_val_dataset():
    return _make_dataset("val", augment=False, shuffle=False)


def get_test_dataset():
    return _make_dataset("test", augment=False, shuffle=False)
