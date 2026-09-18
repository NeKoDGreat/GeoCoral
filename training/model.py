"""
GeoCoral — ResNet50 transfer-learning model.

Architecture (Model Development and Transfer Learning):
  - ResNet50 base, pretrained on ImageNet, original 1000-class head removed
  - Custom head: GlobalAveragePooling2D -> Dropout -> Dense(1, sigmoid)
  - Two-phase training:
      Phase 1 (head training):  base frozen, only head trainable
      Phase 2 (fine-tuning):    final residual blocks (conv5_block*) unfrozen
"""

import os
import sys

import tensorflow as tf
from tensorflow.keras import layers, models
from tensorflow.keras.applications import ResNet50

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


def build_model():
    """Builds the ResNet50-based binary classifier with the base frozen
    (ready for Phase 1 / head training)."""
    base_model = ResNet50(
        weights="imagenet",
        include_top=False,
        input_shape=(config.IMG_SIZE, config.IMG_SIZE, config.IMG_CHANNELS),
    )
    base_model.trainable = False  # Phase 1: freeze convolutional base

    inputs = tf.keras.Input(shape=(config.IMG_SIZE, config.IMG_SIZE, config.IMG_CHANNELS))
    x = base_model(inputs, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dropout(config.DROPOUT_RATE)(x)
    outputs = layers.Dense(1, activation="sigmoid", name="bleaching_probability")(x)

    model = models.Model(inputs, outputs, name="geocoral_resnet50")
    return model, base_model


def unfreeze_for_fine_tuning(base_model):
    """Phase 2: unfreeze the final residual blocks (conv5_block*) while
    keeping earlier blocks frozen, so low-level ImageNet features are
    preserved and only higher-level, bleaching-relevant features adapt."""
    base_model.trainable = True
    for layer in base_model.layers:
        if not layer.name.startswith(config.FINE_TUNE_AT_LAYER_PREFIX):
            layer.trainable = False
    return base_model


def compile_model(model, learning_rate):
    metrics = [
        tf.keras.metrics.BinaryAccuracy(name="accuracy"),
        tf.keras.metrics.Precision(name="precision"),
        tf.keras.metrics.Recall(name="recall"),
        tf.keras.metrics.AUC(name="auc"),
    ]
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
        loss="binary_crossentropy",
        metrics=metrics,
    )
    return model


def count_trainable_params(model):
    trainable = sum(tf.keras.backend.count_params(w) for w in model.trainable_weights)
    non_trainable = sum(tf.keras.backend.count_params(w) for w in model.non_trainable_weights)
    return trainable, non_trainable
