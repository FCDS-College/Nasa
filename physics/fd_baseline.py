"""Finite-difference recovery of the buoyancy and thermal-Peclet coefficients from a PSI-115 case.

No training involved, so it is fast and deterministic. It serves two purposes: a sanity check that the
data really contains the physics the PINN is asked to find, and a reference the PINN result is compared to.

Equations (steady, dimensionless, low-Mach variable density rho = 1/T*, +y up):
  momentum   rho (u.grad) u_i = -dp/dx_i + (1/Re) d(tau_ij)/dx_j + G (rho - 1) delta_iy
  energy     rho (u.grad) T   = (1/Pe) div(mu* grad T)            (mu* = T*^n, k*/mu* constant)
Taking the curl of the momentum equation removes the pressure, leaving a relation that is linear in G:
  d/dx[R_y] - d/dy[R_x] = G d(rho)/dx,   R_i = rho (u.grad) u_i - (1/Re) d(tau_ij)/dx_j
Both coefficients then follow from a one-parameter least-squares fit over the fluid interior.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from physics.psi115 import FlowCase


@dataclass(frozen=True)
class FDEstimate:
    buoyancy: float
    buoyancy_r2: float
    inverse_peclet: float
    inverse_peclet_r2: float
    n_points: int


def fluid_interior_mask(case: FlowCase, margin_cells: int = 4, edge_cells: int = 6) -> np.ndarray:
    """Fluid cells at least `margin_cells` away from the heated block and `edge_cells` from the domain edge."""
    mask = ~case.source_mask
    for _ in range(margin_cells):
        mask = mask & np.roll(mask, 1, 0) & np.roll(mask, -1, 0) & np.roll(mask, 1, 1) & np.roll(mask, -1, 1)
    mask[:edge_cells] = mask[-edge_cells:] = False
    mask[:, :edge_cells] = mask[:, -edge_cells:] = False
    return mask


def _fit(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    """Least-squares coefficient c in b ~ c*a and the coefficient of determination of that fit."""
    coeff = float(a @ b / (a @ a))
    total = float(((b - b.mean()) ** 2).sum())
    r2 = 1.0 - float(((b - coeff * a) ** 2).sum()) / total if total > 0 else 0.0
    return coeff, r2


def estimate_parameters_fd(case: FlowCase, viscosity_exponent: float = 0.7, margin_cells: int = 4) -> FDEstimate:
    x, y = case.x, case.y
    T, u, v = case.temperature, case.u, case.v

    def ddx(f: np.ndarray) -> np.ndarray:
        return np.gradient(f, x, axis=1)

    def ddy(f: np.ndarray) -> np.ndarray:
        return np.gradient(f, y, axis=0)

    rho = 1.0 / T
    mu = T**viscosity_exponent
    div = ddx(u) + ddy(v)
    txx = mu * (2 * ddx(u) - 2 / 3 * div)
    tyy = mu * (2 * ddy(v) - 2 / 3 * div)
    txy = mu * (ddy(u) + ddx(v))
    inv_re = 1.0 / case.constants.reynolds
    r_x = rho * (u * ddx(u) + v * ddy(u)) - inv_re * (ddx(txx) + ddy(txy))
    r_y = rho * (u * ddx(v) + v * ddy(v)) - inv_re * (ddx(txy) + ddy(tyy))
    curl_momentum = ddx(r_y) - ddy(r_x)

    mask = fluid_interior_mask(case, margin_cells)
    g_coeff, g_r2 = _fit(ddx(rho)[mask], curl_momentum[mask])

    diffusion = ddx(mu * ddx(T)) + ddy(mu * ddy(T))
    convection = rho * (u * ddx(T) + v * ddy(T))
    pe_coeff, pe_r2 = _fit(diffusion[mask], convection[mask])
    return FDEstimate(g_coeff, g_r2, pe_coeff, pe_r2, int(mask.sum()))
