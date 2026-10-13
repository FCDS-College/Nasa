"""
pinn_pipeline.py - Dynamic Physics-Informed Neural Network (PINN) Pipeline for Flame/Thermal Physics
"""
from __future__ import annotations

from typing import Any, Dict, Tuple
import numpy as np
import tensorflow as tf


def generate_dynamic_collocation_points(
    num_points: int = 1000, 
    spatial_bounds: Tuple[float, float] = (0.0, 1.0),
    time_bounds: Tuple[float, float] = (0.0, 1.0),
    seed: int = 42
) -> Tuple[tf.Tensor, tf.Tensor]:
    """Generate collocation points dynamically to enforce physical laws without hardcoded points."""
    rng = np.random.default_rng(seed)
    x = rng.uniform(spatial_bounds[0], spatial_bounds[1], (num_points, 1))
    t = rng.uniform(time_bounds[0], time_bounds[1], (num_points, 1))
    return tf.convert_to_tensor(x, dtype=tf.float32), tf.convert_to_tensor(t, dtype=tf.float32)


def build_dynamic_pinn(
    num_hidden_layers: int = 4, 
    num_neurons: int = 64,
    learning_rate: float = 0.001
) -> Tuple[tf.keras.Model, tf.keras.optimizers.Optimizer]:
    """Build a dynamic PINN model for thermal and combustion differential equations."""
    model = tf.keras.Sequential()
    model.add(tf.keras.layers.Input(shape=(2,)))
    
    for _ in range(num_hidden_layers):
        model.add(tf.keras.layers.Dense(num_neurons, activation='tanh'))
        
    model.add(tf.keras.layers.Dense(1))
    
    optimizer = tf.keras.optimizers.Adam(learning_rate=learning_rate)
    return model, optimizer


def physics_residual_loss(
    model: tf.keras.Model, 
    x: tf.Tensor, 
    t: tf.Tensor, 
    thermal_diffusivity: float = 0.01
) -> tf.Tensor:
    """Compute the PDE residual loss based on the heat equation: du/dt = alpha * d^2u/dx^2"""
    with tf.GradientTape(persistent=True) as tape2:
        tape2.watch(x)
        tape2.watch(t)
        with tf.GradientTape(persistent=True) as tape1:
            tape1.watch(x)
            tape1.watch(t)
            inputs = tf.concat([x, t], axis=1)
            u = model(inputs)
        u_x = tape1.gradient(u, x)
        u_t = tape1.gradient(u, t)
    u_xx = tape2.gradient(u_x, x)
    
    del tape1
    del tape2
    
    residual = u_t - thermal_diffusivity * u_xx
    return tf.reduce_mean(tf.square(residual))


def train_pinn_step(
    model: tf.keras.Model, 
    optimizer: tf.keras.optimizers.Optimizer, 
    x_data: tf.Tensor, 
    t_data: tf.Tensor, 
    u_data: tf.Tensor, 
    x_colloc: tf.Tensor, 
    t_colloc: tf.Tensor,
    lambda_physics: float = 1.0,
    thermal_diffusivity: float = 0.01
) -> Dict[str, float]:
    """Execute a single training step combining data loss and physics loss."""
    with tf.GradientTape() as tape:
        pred_data = model(tf.concat([x_data, t_data], axis=1))
        data_loss = tf.reduce_mean(tf.square(pred_data - u_data))
        
        phys_loss = physics_residual_loss(model, x_colloc, t_colloc, thermal_diffusivity)
        
        total_loss = data_loss + (lambda_physics * phys_loss)
        
    grads = tape.gradient(total_loss, model.trainable_variables)
    optimizer.apply_gradients(zip(grads, model.trainable_variables))
    
    return {
        "totalLoss": float(total_loss.numpy()),
        "dataLoss": float(data_loss.numpy()),
        "physicsLoss": float(phys_loss.numpy())
    }


def run_pinn_pipeline(
    x_measured: np.ndarray,
    t_measured: np.ndarray,
    u_measured: np.ndarray,
    epochs: int = 100,
    num_colloc_points: int = 1000,
    lambda_physics: float = 1.0,
    thermal_diffusivity: float = 0.01
) -> Dict[str, Any]:
    """Execute the complete PINN training pipeline dynamically."""
    x_data = tf.convert_to_tensor(x_measured, dtype=tf.float32)
    t_data = tf.convert_to_tensor(t_measured, dtype=tf.float32)
    u_data = tf.convert_to_tensor(u_measured, dtype=tf.float32)
    
    x_colloc, t_colloc = generate_dynamic_collocation_points(num_points=num_colloc_points)
    model, optimizer = build_dynamic_pinn()
    
    loss_history = []
    for epoch in range(epochs):
        metrics = train_pinn_step(
            model, optimizer, x_data, t_data, u_data, x_colloc, t_colloc, 
            lambda_physics=lambda_physics, thermal_diffusivity=thermal_diffusivity
        )
        loss_history.append(metrics)
        
    return {
        "status": "SUCCESS",
        "epochsTrained": epochs,
        "finalMetrics": loss_history[-1] if loss_history else {}
    }
