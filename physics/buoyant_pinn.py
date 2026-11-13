"""Gravity-aware PINN for steady buoyant flow: infers the buoyancy and thermal-Peclet coefficients from fields.

Replaces the 1D heat-equation prototype in cv/pinn_pipeline.py, which had no velocity field, no buoyancy and
no gravity dependence. The model here is the formulation PSI-115 itself solves (final report, eqs. 1, 2, 5),
reduced to steady, low-Mach, variable-density form with +y up:

  continuity  d(rho u)/dx + d(rho v)/dy = 0,            rho = 1/T*   (ideal gas, near-constant pressure)
  momentum    rho (u.grad) u_i = -dp/dx_i + (1/Re) d(tau_ij)/dx_j + G (rho - 1) delta_iy
  energy      rho (u.grad) T   = (1/Pe) div(mu* grad T) (+ optional source Q, zero without combustion)

Gravity enters only through G = -g Lo / Uo^2 (= -1/Fr^2): about -6.74 at Earth gravity, 0 in microgravity. The
network predicts (u, v, p, T) from (x, y); pressure is an unknown that appears only through its gradient.
G and 1/Pe are trainable scalars, so training is a parameter-estimation problem: fit the fields, then let the
physics residual decide which coefficients explain them.
"""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from typing import Callable

import numpy as np
import torch
from torch import nn

from physics.psi115 import FlowCase, load_case

FieldFn = Callable[[torch.Tensor], torch.Tensor]  # (N, 2) -> (N, 4) columns [u, v, p, T]


@dataclass
class TrainConfig:
    hidden: int = 64
    layers: int = 5
    n_data: int = 4096  # supervised points per step
    n_colloc: int = 2048  # physics points per step
    # "weak": continuity pointwise, momentum and energy as finite-volume cell balances (first derivatives only).
    # "strong": all four equations pointwise (second derivatives of the network bias 1/Pe and G low).
    residual_form: str = "weak"
    n_cells: int = 512  # weak-form cells per step
    cell_half_width: tuple[float, float] = (0.25, 0.6)  # in units of Lo; larger than the finest grid spacing
    warmup_steps: int = 1500  # fit the fields only, coefficients frozen
    steps: int = 3000  # joint data + physics, coefficients trainable
    lr: float = 2e-3
    coeff_lr: float = 2e-2
    data_weight: float = 10.0
    # Low on purpose: the data are exact simulation fields, so the physics term should not drag the network off them.
    # At 1.0 the fitted 1/Pe collapsed to 0.016-0.03 (nominal 0.063); at 0.05 it is 0.055-0.059. Adam is scale-invariant
    # per parameter, so the coefficients still learn at full speed.
    physics_weight: float = 0.05
    viscosity_exponent: float = 0.7  # mu* = T*^n for air
    infer_buoyancy: bool = True
    infer_peclet: bool = True
    init_buoyancy: float = 0.0  # deliberately the microgravity answer, so Earth recovery is not a given
    init_inverse_peclet: float = 0.1  # deliberately off the nominal 1/(Re Pr) = 0.063
    seed: int = 0
    log_every: int = 500


class FlowNet(nn.Module):
    """MLP (x, y) -> (u, v, p, T) with inputs scaled to [-1, 1] over the domain."""

    def __init__(self, lo: tuple[float, float], hi: tuple[float, float], hidden: int = 64, layers: int = 5):
        super().__init__()
        self.register_buffer("lo", torch.tensor(lo, dtype=torch.float32))
        self.register_buffer("hi", torch.tensor(hi, dtype=torch.float32))
        dims = [2] + [hidden] * layers

        def mlp() -> nn.Sequential:
            blocks: list[nn.Module] = []
            for a, b in zip(dims[:-1], dims[1:]):
                blocks += [nn.Linear(a, b), nn.Tanh()]
            return nn.Sequential(*blocks)

        # Pressure has no data: only the physics residual trains it. A separate branch keeps it from being starved
        # by a body that the data loss dominates (otherwise the fitted buoyancy absorbs the pressure error).
        self.body, self.head = mlp(), nn.Linear(hidden, 3)  # u, v, T - 1
        self.p_body, self.p_head = mlp(), nn.Linear(hidden, 1)

    def forward(self, xy: torch.Tensor) -> torch.Tensor:
        z = 2.0 * (xy - self.lo) / (self.hi - self.lo) - 1.0
        u, v, dt = self.head(self.body(z)).unbind(-1)
        p = self.p_head(self.p_body(z)).squeeze(-1)
        return torch.stack([u, v, p, 1.0 + dt], dim=-1)  # T* is 1 at the ambient inlet


class Coefficients(nn.Module):
    """Physical coefficients: Re is fixed; G and 1/Pe can be inferred (1/Pe through its log to stay positive)."""

    def __init__(self, inv_re: float, config: TrainConfig):
        super().__init__()
        self.inv_re = inv_re
        self.viscosity_exponent = config.viscosity_exponent
        self.buoyancy = nn.Parameter(torch.tensor(float(config.init_buoyancy)), requires_grad=config.infer_buoyancy)
        self.log_inv_pe = nn.Parameter(
            torch.tensor(math.log(config.init_inverse_peclet)), requires_grad=config.infer_peclet
        )

    @property
    def inverse_peclet(self) -> torch.Tensor:
        return self.log_inv_pe.exp()


def _grad(out: torch.Tensor, inp: torch.Tensor) -> torch.Tensor:
    return torch.autograd.grad(out, inp, torch.ones_like(out), create_graph=True)[0]


def physics_residuals(
    field_fn: FieldFn,
    coeffs: Coefficients,
    xy: torch.Tensor,
    source: Callable[[torch.Tensor], torch.Tensor] | None = None,
    include_energy: bool = True,
) -> dict[str, torch.Tensor]:
    """Pointwise residuals of continuity, x/y momentum and energy at the points `xy` (N, 2).

    `include_energy=False` skips the strong-form energy residual (it needs second derivatives of T); training uses
    `weak_energy_residual` instead, which does not shrink 1/Pe.

    `source` is an optional volumetric heat release Q(x, y, T) added to the energy equation; it is None for
    PSI-115 (no combustion). It is the hook for flame data, where Q would come from a reaction model.
    """
    xy = xy.detach().clone().requires_grad_(True)
    u, v, p, T = field_fn(xy).unbind(-1)
    rho = 1.0 / T
    mu = T**coeffs.viscosity_exponent

    ux, uy = _grad(u, xy).unbind(-1)
    vx, vy = _grad(v, xy).unbind(-1)
    Tx, Ty = _grad(T, xy).unbind(-1)
    px, py = _grad(p, xy).unbind(-1)
    div = ux + vy
    txx = mu * (2.0 * ux - 2.0 / 3.0 * div)
    tyy = mu * (2.0 * vy - 2.0 / 3.0 * div)
    txy = mu * (uy + vx)
    g_txx, g_tyy, g_txy = _grad(txx, xy), _grad(tyy, xy), _grad(txy, xy)

    mass = _grad(rho * u, xy)[:, 0] + _grad(rho * v, xy)[:, 1]
    mom_x = rho * (u * ux + v * uy) + px - coeffs.inv_re * (g_txx[:, 0] + g_txy[:, 1])
    mom_y = rho * (u * vx + v * vy) + py - coeffs.inv_re * (g_txy[:, 0] + g_tyy[:, 1]) - coeffs.buoyancy * (rho - 1.0)
    out = {"mass": mass, "mom_x": mom_x, "mom_y": mom_y}
    if include_energy:
        conduction = _grad(mu * Tx, xy)[:, 0] + _grad(mu * Ty, xy)[:, 1]
        energy = rho * (u * Tx + v * Ty) - coeffs.inverse_peclet * conduction
        if source is not None:
            energy = energy - source(torch.cat([xy.detach(), T.detach().unsqueeze(-1)], dim=-1))
        out["energy"] = energy
    return out


_GL_NODES = (-0.8611363115940526, -0.3399810435848563, 0.3399810435848563, 0.8611363115940526)
_GL_WEIGHTS = (0.3478548451374538, 0.6521451548625450, 0.6521451548625450, 0.3478548451374538)


def weak_residuals(
    field_fn: FieldFn,
    coeffs: Coefficients,
    centers: torch.Tensor,
    half_width: torch.Tensor,
    source: Callable[[torch.Tensor], torch.Tensor] | None = None,
) -> dict[str, torch.Tensor]:
    """Finite-volume residuals of x/y momentum and energy on square cells: net outward flux per unit area.

    With continuity, rho (u.grad) f = div(rho u f), so each equation is a flux balance over a cell:
      energy    div(rho u T   - (1/Pe) mu grad T) = Q
      momentum  div(rho u u_i + p e_i - (1/Re) tau_i.) = G (rho - 1) delta_iy
    Integrating leaves only values and *first* derivatives on the cell edges (4-point Gauss rule per edge) plus
    an area integral of (rho - 1) (4x4 Gauss). The strong forms need second derivatives of the network, whose
    noise biases the fitted coefficients toward zero: 1/Pe measured 0.019 from network derivatives vs 0.061 on
    exact data, and the buoyancy coefficient came out about 8 % low for the same reason (viscous term).

    centers: (M, 2) cell centres, half_width: (M,) half side lengths. Returns {"energy", "mom_x", "mom_y"}, each (M,).
    """
    nodes = torch.tensor(_GL_NODES, dtype=centers.dtype, device=centers.device)
    weights = torch.tensor(_GL_WEIGHTS, dtype=centers.dtype, device=centers.device)
    h = half_width[:, None]
    cx, cy = centers[:, :1], centers[:, 1:]
    t = h * nodes  # (M, K) offsets along an edge
    flat = torch.zeros_like(t)
    edges = [  # (x, y, nx, ny): right, left, top, bottom
        (cx + h + flat, cy + t, 1.0, 0.0),
        (cx - h + flat, cy + t, -1.0, 0.0),
        (cx + t, cy + h + flat, 0.0, 1.0),
        (cx + t, cy - h + flat, 0.0, -1.0),
    ]
    totals = {k: torch.zeros_like(h[:, 0]) for k in ("energy", "mom_x", "mom_y")}
    for x, y, nx, ny in edges:
        pts = torch.stack([x, y], dim=-1).reshape(-1, 2).detach().requires_grad_(True)
        u, v, p, T = field_fn(pts).unbind(-1)
        ux, uy = _grad(u, pts).unbind(-1)
        vx, vy = _grad(v, pts).unbind(-1)
        Tx, Ty = _grad(T, pts).unbind(-1)
        mu = T**coeffs.viscosity_exponent
        div = ux + vy
        txx = mu * (2.0 * ux - 2.0 / 3.0 * div)
        tyy = mu * (2.0 * vy - 2.0 / 3.0 * div)
        txy = mu * (uy + vx)
        un = u * nx + v * ny
        mass_flux = un / T  # rho (u.n)
        fluxes = {
            "energy": un - coeffs.inverse_peclet * mu * (Tx * nx + Ty * ny),  # rho T = 1
            "mom_x": mass_flux * u + p * nx - coeffs.inv_re * (txx * nx + txy * ny),
            "mom_y": mass_flux * v + p * ny - coeffs.inv_re * (txy * nx + tyy * ny),
        }
        for k, f in fluxes.items():  # edge length 2h, dl = h ds
            totals[k] = totals[k] + h[:, 0] * (f.reshape(-1, nodes.numel()) * weights).sum(dim=1)
    area = 4.0 * h[:, 0] ** 2
    out = {k: v / area for k, v in totals.items()}

    # Body force: mean of (rho - 1) over the cell by a 4x4 Gauss rule (values only, no derivatives).
    gx, gy = torch.meshgrid(nodes, nodes, indexing="ij")
    inner = torch.stack([cx + h * gx.reshape(1, -1), cy + h * gy.reshape(1, -1)], dim=-1).reshape(-1, 2)
    rho_m1 = (1.0 / field_fn(inner)[:, 3] - 1.0).reshape(-1, nodes.numel() ** 2)
    ww = (weights[:, None] * weights[None, :]).reshape(1, -1)
    out["mom_y"] = out["mom_y"] - coeffs.buoyancy * (rho_m1 * ww).sum(dim=1) / 4.0
    if source is not None:
        T_c = field_fn(centers.detach())[:, 3].detach().unsqueeze(-1)
        out["energy"] = out["energy"] - source(torch.cat([centers.detach(), T_c], dim=-1))
    return out


def weak_energy_residual(
    field_fn: FieldFn,
    coeffs: Coefficients,
    centers: torch.Tensor,
    half_width: torch.Tensor,
    source: Callable[[torch.Tensor], torch.Tensor] | None = None,
) -> torch.Tensor:
    """Energy entry of `weak_residuals`, kept as the single-equation entry point."""
    return weak_residuals(field_fn, coeffs, centers, half_width, source)["energy"]


def mass_residual(field_fn: FieldFn, xy: torch.Tensor) -> torch.Tensor:
    """Pointwise continuity residual d(rho u)/dx + d(rho v)/dy (first derivatives only)."""
    xy = xy.detach().clone().requires_grad_(True)
    u, v, _, T = field_fn(xy).unbind(-1)
    rho = 1.0 / T
    return _grad(rho * u, xy)[:, 0] + _grad(rho * v, xy)[:, 1]


def physics_loss(residuals: dict[str, torch.Tensor]) -> torch.Tensor:
    return sum(r.pow(2).mean() for r in residuals.values())


@dataclass
class FitResult:
    case: str
    buoyancy: float
    expected_buoyancy: float
    inverse_peclet: float
    nominal_inverse_peclet: float
    rmse: dict[str, float]
    history: list[dict[str, float]]
    config: dict


class _Sampler:
    """Draws random grid cells: fluid cells for physics, fluid plus block cells for data."""

    def __init__(self, case: FlowCase, device: torch.device):
        yy, xx = np.meshgrid(case.y, case.x, indexing="ij")
        self.xy = torch.tensor(np.stack([xx.ravel(), yy.ravel()], axis=1), dtype=torch.float32, device=device)
        self.target = torch.tensor(
            np.stack([case.u.ravel(), case.v.ravel(), case.temperature.ravel()], axis=1), dtype=torch.float32, device=device
        )
        mask = case.source_mask.ravel()
        self.fluid = torch.tensor(np.flatnonzero(~mask), device=device)
        self.all = torch.arange(mask.size, device=device)
        self.bounds = (float(case.x.min()), float(case.x.max()), float(case.y.min()), float(case.y.max()))
        rows, cols = np.where(case.source_mask)
        self.block = (
            (float(case.x[cols.min()]), float(case.x[cols.max()]), float(case.y[rows.min()]), float(case.y[rows.max()]))
            if rows.size
            else None
        )

    def draw_cells(self, n: int, half_width: tuple[float, float], gen: torch.Generator) -> tuple[torch.Tensor, torch.Tensor]:
        """Random square cells that lie inside the domain and do not overlap the heated block."""
        xy, _ = self.draw(self.fluid, 4 * n, gen)
        lo, hi = half_width
        h = lo + (hi - lo) * torch.rand(4 * n, generator=gen, device=xy.device)
        x0, x1, y0, y1 = self.bounds
        ok = (xy[:, 0] - h > x0) & (xy[:, 0] + h < x1) & (xy[:, 1] - h > y0) & (xy[:, 1] + h < y1)
        if self.block is not None:
            bx0, bx1, by0, by1 = self.block
            ok &= ~((xy[:, 0] + h > bx0) & (xy[:, 0] - h < bx1) & (xy[:, 1] + h > by0) & (xy[:, 1] - h < by1))
        return xy[ok][:n], h[ok][:n]

    def draw(self, pool: torch.Tensor, n: int, gen: torch.Generator) -> tuple[torch.Tensor, torch.Tensor]:
        idx = pool[torch.randint(0, pool.numel(), (n,), generator=gen, device=pool.device)]
        return self.xy[idx], self.target[idx]


def _data_loss(net: FlowNet, xy: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    pred = net(xy)
    return ((pred[:, [0, 1, 3]] - target) ** 2).mean()


@torch.no_grad()
def evaluate_rmse(net: FlowNet, sampler: _Sampler, chunk: int = 20000) -> dict[str, float]:
    """RMSE of u, v, T over every fluid cell of the grid (the network never saw most of them)."""
    se = torch.zeros(3)
    for part in torch.split(sampler.fluid, chunk):
        pred = net(sampler.xy[part])[:, [0, 1, 3]]
        se += ((pred - sampler.target[part]) ** 2).sum(0).cpu()
    rmse = (se / sampler.fluid.numel()).sqrt()
    return {"u": float(rmse[0]), "v": float(rmse[1]), "T": float(rmse[2])}


def fit(case: FlowCase, config: TrainConfig | None = None, device: str = "cpu") -> FitResult:
    cfg = config or TrainConfig()
    torch.manual_seed(cfg.seed)
    dev = torch.device(device)
    gen = torch.Generator(device=dev).manual_seed(cfg.seed)

    sampler = _Sampler(case, dev)
    lo, hi = (float(case.x.min()), float(case.y.min())), (float(case.x.max()), float(case.y.max()))
    net = FlowNet(lo, hi, cfg.hidden, cfg.layers).to(dev)
    coeffs = Coefficients(1.0 / case.constants.reynolds, cfg).to(dev)

    opt = torch.optim.Adam(
        [{"params": net.parameters(), "lr": cfg.lr}, {"params": [p for p in coeffs.parameters() if p.requires_grad], "lr": cfg.coeff_lr}]
    )
    total = cfg.warmup_steps + cfg.steps
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: 0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * min(s, total) / total)))
    history: list[dict[str, float]] = []

    for step in range(1, total + 1):
        opt.zero_grad(set_to_none=True)
        xy_d, tgt = sampler.draw(sampler.all, cfg.n_data, gen)
        d_loss = _data_loss(net, xy_d, tgt)
        loss = cfg.data_weight * d_loss
        p_loss = torch.zeros(())
        if step > cfg.warmup_steps:
            xy_c, _ = sampler.draw(sampler.fluid, cfg.n_colloc, gen)
            if cfg.residual_form == "weak":
                centers, half = sampler.draw_cells(cfg.n_cells, cfg.cell_half_width, gen)
                p_loss = mass_residual(net, xy_c).pow(2).mean() + physics_loss(weak_residuals(net, coeffs, centers, half))
            else:
                p_loss = physics_loss(physics_residuals(net, coeffs, xy_c))
            loss = loss + cfg.physics_weight * p_loss
        loss.backward()
        opt.step()
        sched.step()
        if step % cfg.log_every == 0 or step == total:
            row = {
                "step": step,
                "data_loss": d_loss.item(),
                "physics_loss": p_loss.item(),
                "buoyancy": coeffs.buoyancy.item(),
                "inverse_peclet": coeffs.inverse_peclet.item(),
            }
            history.append(row)
            print(json.dumps(row), flush=True)

    return FitResult(
        case=case.name,
        buoyancy=coeffs.buoyancy.item(),
        expected_buoyancy=case.expected_buoyancy,
        inverse_peclet=coeffs.inverse_peclet.item(),
        nominal_inverse_peclet=case.constants.inverse_peclet,
        rmse=evaluate_rmse(net, sampler),
        history=history,
        config=asdict(cfg),
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Infer buoyancy and 1/Pe from PSI-115 fields with a PINN.")
    ap.add_argument("--gravity", choices=["earth", "micro"], required=True)
    ap.add_argument("--steps", type=int, default=TrainConfig.steps)
    ap.add_argument("--warmup-steps", type=int, default=TrainConfig.warmup_steps)
    ap.add_argument("--seed", type=int, default=TrainConfig.seed)
    ap.add_argument("--physics-weight", type=float, default=TrainConfig.physics_weight)
    ap.add_argument("--residual-form", choices=["weak", "strong"], default=TrainConfig.residual_form)
    ap.add_argument("--coeff-lr", type=float, default=TrainConfig.coeff_lr)
    ap.add_argument("--hidden", type=int, default=TrainConfig.hidden)
    ap.add_argument("--layers", type=int, default=TrainConfig.layers)
    ap.add_argument("--n-cells", type=int, default=TrainConfig.n_cells)
    ap.add_argument("--out", help="write the FitResult as JSON to this path")
    args = ap.parse_args()
    cfg = TrainConfig(
        hidden=args.hidden,
        layers=args.layers,
        n_cells=args.n_cells,
        steps=args.steps,
        warmup_steps=args.warmup_steps,
        seed=args.seed,
        physics_weight=args.physics_weight,
        residual_form=args.residual_form,
        coeff_lr=args.coeff_lr,
    )
    result = fit(load_case(args.gravity), cfg)
    print(f"\nbuoyancy G = {result.buoyancy:.3f} (expected {result.expected_buoyancy:.3f})")
    print(f"1/Pe       = {result.inverse_peclet:.4f} (nominal {result.nominal_inverse_peclet:.4f})")
    print(f"field RMSE = {result.rmse}")
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(asdict(result), fh, indent=2)


if __name__ == "__main__":
    main()
