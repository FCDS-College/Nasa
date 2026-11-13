"""Smoke tests for training: a tiny PINN on a synthetic case must run, stay finite and report its coefficients."""
import math

import numpy as np
import pytest

pytest.importorskip("torch", reason="PyTorch is optional (physics/requirements.txt); CI does not install it")

from physics.buoyant_pinn import TrainConfig, fit  # noqa: E402
from physics.psi115 import FlowCase  # noqa: E402


def synthetic_case() -> FlowCase:
    x, y = np.linspace(0, 4, 20), np.linspace(-1, 1, 10)
    yy, xx = np.meshgrid(y, x, indexing="ij")
    temperature = 1.0 + 0.3 * np.exp(-((xx - 2) ** 2 + yy**2))
    u = 1.0 - 0.2 * yy**2
    return FlowCase("synthetic", 9.81, x, y, temperature, u, np.zeros_like(u), np.zeros_like(u, dtype=bool))


def test_fit_runs_and_reports_finite_coefficients():
    cfg = TrainConfig(hidden=16, layers=2, n_data=64, n_colloc=64, warmup_steps=5, steps=5, log_every=5)
    result = fit(synthetic_case(), cfg)
    assert result.history and result.history[-1]["step"] == 10
    assert all(math.isfinite(v) for v in (result.buoyancy, result.inverse_peclet, *result.rmse.values()))
    assert result.inverse_peclet > 0
    assert result.expected_buoyancy < 0


def test_frozen_coefficients_do_not_move():
    cfg = TrainConfig(
        hidden=16, layers=2, n_data=64, n_colloc=64, warmup_steps=2, steps=4, log_every=3,
        infer_buoyancy=False, infer_peclet=False, init_buoyancy=-1.5, init_inverse_peclet=0.07,
    )
    result = fit(synthetic_case(), cfg)
    assert result.buoyancy == -1.5
    assert math.isclose(result.inverse_peclet, 0.07, rel_tol=1e-6)


def test_same_seed_is_reproducible():
    cfg = TrainConfig(hidden=16, layers=2, n_data=64, n_colloc=64, warmup_steps=3, steps=3, log_every=6, seed=7)
    a, b = fit(synthetic_case(), cfg), fit(synthetic_case(), cfg)
    assert a.buoyancy == b.buoyancy and a.rmse == b.rmse
