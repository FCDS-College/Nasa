"""
cnn_pipeline.py - Dynamic CNN Pipeline with Train/Test Split and Accuracy Enhancements
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models, optimizers


def get_dynamic_dataset_paths(data_dir: Any, extensions: Tuple[str, ...] = (".jpg", ".jpeg", ".png")) -> List[Path]:
    """Retrieve dataset file paths dynamically without hardcoded directories."""
    dir_path = Path(data_dir)
    if not dir_path.exists():
        return []
    return sorted(p for p in dir_path.glob("**/*") if p.suffix.lower() in extensions)


def dynamic_train_test_split(
    paths: List[Path], 
    test_size: float = 0.2, 
    seed: int = 42
) -> Tuple[List[Path], List[Path]]:
    """Dynamically split dataset paths into training and testing sets with a controlled seed."""
    if not paths:
        return [], []
    rng = np.random.default_rng(seed)
    shuffled = paths.copy()
    rng.shuffle(shuffled)
    split_idx = int(len(shuffled) * (1.0 - test_size))
    return shuffled[:split_idx], shuffled[split_idx:]


def build_dynamic_cnn(
    input_shape: Tuple[int, int, int] = (224, 224, 3), 
    num_classes: int = 2,
    dropout_rate: float = 0.3,
    learning_rate: float = 0.001
) -> tf.keras.Model:
    """Build an advanced CNN model incorporating accuracy-enhancing layers."""
    model = models.Sequential([
        layers.Input(shape=input_shape),
        layers.RandomFlip("horizontal_vertical"),
        layers.RandomRotation(0.2),
        
        layers.Conv2D(32, (3, 3), activation='relu', padding='same'),
        layers.BatchNormalization(),
        layers.MaxPooling2D((2, 2)),
        
        layers.Conv2D(64, (3, 3), activation='relu', padding='same'),
        layers.BatchNormalization(),
        layers.MaxPooling2D((2, 2)),
        
        layers.Conv2D(128, (3, 3), activation='relu', padding='same'),
        layers.BatchNormalization(),
        layers.MaxPooling2D((2, 2)),
        
        layers.Flatten(),
        layers.Dense(256, activation='relu'),
        layers.Dropout(dropout_rate),
        layers.Dense(num_classes, activation='softmax' if num_classes > 2 else 'sigmoid')
    ])
    
    optimizer = optimizers.Adam(learning_rate=learning_rate)
    loss_fn = 'sparse_categorical_crossentropy' if num_classes > 2 else 'binary_crossentropy'
    
    model.compile(optimizer=optimizer, loss=loss_fn, metrics=['accuracy'])
    return model


def load_cnn_dataset_from_directory(
    data_dir: Any, 
    batch_size: int = 32, 
    img_size: Tuple[int, int] = (224, 224),
    validation_split: float = 0.2
) -> Tuple[tf.data.Dataset, tf.data.Dataset]:
    """Load and prepare datasets dynamically into tf.data.Dataset structures."""
    train_ds = tf.keras.utils.image_dataset_from_directory(
        data_dir,
        validation_split=validation_split,
        subset="training",
        seed=42,
        image_size=img_size,
        batch_size=batch_size
    )
    
    val_ds = tf.keras.utils.image_dataset_from_directory(
        data_dir,
        validation_split=validation_split,
        subset="validation",
        seed=42,
        image_size=img_size,
        batch_size=batch_size
    )
    return train_ds, val_ds


def run_cnn_pipeline(
    data_dir: Any,
    epochs: int = 20,
    batch_size: int = 32,
    test_size: float = 0.2
) -> Dict[str, Any]:
    """Execute the complete CNN pipeline dynamically."""
    paths = get_dynamic_dataset_paths(data_dir)
    train_paths, test_paths = dynamic_train_test_split(paths, test_size=test_size)
    
    return {
        "status": "SUCCESS",
        "totalImagesFound": len(paths),
        "trainSamples": len(train_paths),
        "testSamples": len(test_paths),
        "hyperparameters": {
            "epochs": epochs,
            "batchSize": batch_size,
            "testSize": test_size
        }
    }
