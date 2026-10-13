"""
cnn_pipeline.py - Convolutional Neural Network (CNN) pipeline for flame segmentation and classification.
"""
from __future__ import annotations

from typing import Any, Dict, Tuple
import numpy as np
import tensorflow as tf


def build_flame_cnn(
    input_shape: Tuple[int, int, int] = (128, 128, 3),
    num_filters: Tuple[int, ...] = (16, 32, 64),
    dense_units: int = 64,
    learning_rate: float = 0.001,
) -> tf.keras.Model:
    """Build a small CNN that predicts whether a frame contains a flame (sigmoid output)."""
    inputs = tf.keras.layers.Input(shape=input_shape)
    x = inputs
    for filters in num_filters:
        x = tf.keras.layers.Conv2D(filters, 3, padding="same", activation="relu")(x)
        x = tf.keras.layers.MaxPooling2D()(x)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x = tf.keras.layers.Dense(dense_units, activation="relu")(x)
    outputs = tf.keras.layers.Dense(1, activation="sigmoid")(x)

    model = tf.keras.Model(inputs, outputs, name="flame_cnn")
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
        loss="binary_crossentropy",
        metrics=["accuracy"],
    )
    return model


def preprocess_frame(frame: np.ndarray, size: Tuple[int, int] = (128, 128)) -> np.ndarray:
    """Resize an HxWx3 uint8 frame and scale it to [0, 1] with a leading batch axis."""
    resized = tf.image.resize(frame, size).numpy().astype(np.float32) / 255.0
    return resized[np.newaxis, ...]


def run_cnn_pipeline(
    frame: np.ndarray,
    model: tf.keras.Model | None = None,
    threshold: float = 0.5,
) -> Dict[str, Any]:
    """Run flame detection on a single frame and return a JSON-friendly result."""
    if model is None:
        input_shape = (128, 128, 3)
        model = build_flame_cnn(input_shape)
    height, width = model.input_shape[1:3]
    batch = preprocess_frame(frame, (height, width))
    score = float(model.predict(batch, verbose=0)[0, 0])
    return {
        "flame_probability": score,
        "flame_detected": score >= threshold,
        "threshold": threshold,
    }
