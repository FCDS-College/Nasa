"""The PDE residuals must vanish on exact solutions and must respond to the buoyancy coefficient and its sign."""
import pytest

torch = pytest.importorskip("torch", reason="PyTorch is optional (physics/requirements.txt); CI does not install it")

from physics.buoyant_pinn import (  # noqa: E402
    Coefficients,
    TrainConfig,
    mass_residual,
    physics_residuals,
    weak_energy_residual,
    weak_residuals,
)

INV_RE = 1.0 / 22.3
G_EARTH = -6.744


def coefficients(buoyancy: float) -> Coefficients:
    return Coefficients(INV_RE, TrainConfig(init_buoyancy=buoyancy, init_inverse_peclet=0.063))


def points(n: int = 64) -> torch.Tensor:
    gen = torch.Generator().manual_seed(0)
    return torch.rand(n, 2, generator=gen) * 2 - 1


def hydrostatic(buoyancy: float, temperature: float = 1.3):
    """Fluid at rest with uniform T: dp/dy must balance G (rho - 1)."""
    rho = 1.0 / temperature

    def field(xy: torch.Tensor) -> torch.Tensor:
        zero = 0.0 * xy[:, 0]
        return torch.stack([zero, zero, buoyancy * (rho - 1.0) * xy[:, 1], temperature + zero], dim=-1)

    return field


def poiseuille(xy: torch.Tensor) -> torch.Tensor:
    """Channel flow u = 1 - y^2 with constant density: dp/dx = -2/Re balances the viscous stress."""
    x, y = xy[:, 0], xy[:, 1]
    zero = 0.0 * x
    return torch.stack([1.0 - y**2, zero, -2.0 * INV_RE * x, 1.0 + zero], dim=-1)


def test_hydrostatic_balance_has_zero_residual_when_coefficient_matches():
    res = physics_residuals(hydrostatic(G_EARTH), coefficients(G_EARTH), points())
    for name, r in res.items():
        assert r.abs().max() < 1e-5, name


def test_wrong_buoyancy_leaves_exactly_the_missing_body_force():
    rho = 1.0 / 1.3
    res = physics_residuals(hydrostatic(G_EARTH), coefficients(0.0), points())
    assert torch.allclose(res["mom_y"], torch.full_like(res["mom_y"], G_EARTH * (rho - 1.0)), atol=1e-5)
    assert res["mom_x"].abs().max() < 1e-5  # gravity acts in y only


def test_buoyancy_sign_matters():
    flipped = physics_residuals(hydrostatic(G_EARTH), coefficients(-G_EARTH), points())
    assert flipped["mom_y"].abs().min() > 1.0  # 2*|G|*|rho-1| is far from zero


def test_microgravity_ignores_density_variation():
    res = physics_residuals(hydrostatic(0.0, temperature=1.5), coefficients(0.0), points())
    assert res["mom_y"].abs().max() < 1e-6


def test_viscous_stress_balances_poiseuille_pressure_gradient():
    res = physics_residuals(poiseuille, coefficients(0.0), points())
    for name, r in res.items():
        assert r.abs().max() < 1e-5, name


def test_wrong_reynolds_breaks_poiseuille_balance():
    coeffs = Coefficients(2 * INV_RE, TrainConfig())
    res = physics_residuals(poiseuille, coeffs, points())
    assert res["mom_x"].abs().min() > 0.01


def test_source_term_enters_the_energy_equation_only():
    def source(state: torch.Tensor) -> torch.Tensor:
        return torch.full((state.shape[0],), 0.5)

    base = physics_residuals(hydrostatic(0.0), coefficients(0.0), points())
    with_q = physics_residuals(hydrostatic(0.0), coefficients(0.0), points(), source=source)
    assert torch.allclose(with_q["energy"], base["energy"] - 0.5)
    assert torch.allclose(with_q["mom_y"], base["mom_y"])


def smooth_field(xy: torch.Tensor) -> torch.Tensor:
    x, y = xy[:, 0], xy[:, 1]
    return torch.stack([0.5 + 0.2 * x * y, 0.1 * x, 0.0 * x, 1.2 + 0.2 * torch.sin(x) * torch.cos(y)], dim=-1)


def test_weak_energy_vanishes_for_uniform_flow_and_hydrostatic_fluid():
    centers, h = points(16) * 0.5, torch.full((16,), 0.2)
    uniform = lambda xy: torch.stack([1 + 0 * xy[:, 0], 0 * xy[:, 0], 0 * xy[:, 0], 1.3 + 0 * xy[:, 0]], dim=-1)  # noqa: E731
    assert weak_energy_residual(uniform, coefficients(0.0), centers, h).abs().max() < 1e-5
    assert weak_energy_residual(hydrostatic(G_EARTH), coefficients(G_EARTH), centers, h).abs().max() < 1e-5


def test_weak_energy_matches_strong_form_plus_continuity_for_small_cells():
    # div(rho u T - c mu grad T) = rho u.grad T - c div(mu grad T) + T div(rho u)
    centers, h = points(16) * 0.5, torch.full((16,), 0.02)
    coeffs = coefficients(0.0)
    strong = physics_residuals(smooth_field, coeffs, centers)
    T = smooth_field(centers)[:, 3]
    expected = (strong["energy"] + T * strong["mass"]).detach()
    weak = weak_energy_residual(smooth_field, coeffs, centers, h).detach()
    assert torch.allclose(weak, expected, atol=2e-3)


def test_weak_energy_depends_on_inverse_peclet_and_accepts_a_source():
    centers, h = points(8) * 0.5, torch.full((8,), 0.2)
    a = weak_energy_residual(smooth_field, Coefficients(INV_RE, TrainConfig(init_inverse_peclet=0.05)), centers, h)
    b = weak_energy_residual(smooth_field, Coefficients(INV_RE, TrainConfig(init_inverse_peclet=0.10)), centers, h)
    assert (a - b).abs().max() > 1e-4
    q = weak_energy_residual(smooth_field, coefficients(0.0), centers, h, source=lambda s: torch.full((s.shape[0],), 0.5))
    base = weak_energy_residual(smooth_field, coefficients(0.0), centers, h)
    assert torch.allclose(q, base - 0.5, atol=1e-5)


def test_weak_momentum_vanishes_on_exact_solutions():
    centers, h = points(16) * 0.5, torch.full((16,), 0.2)
    res = weak_residuals(hydrostatic(G_EARTH), coefficients(G_EARTH), centers, h)
    assert res["mom_y"].abs().max() < 1e-5 and res["mom_x"].abs().max() < 1e-5
    res = weak_residuals(poiseuille, coefficients(0.0), centers, h)
    assert res["mom_x"].abs().max() < 1e-5 and res["mom_y"].abs().max() < 1e-5


def test_weak_momentum_sees_the_buoyancy_coefficient_and_its_sign():
    centers, h = points(16) * 0.5, torch.full((16,), 0.2)
    rho = 1.0 / 1.3
    missing = weak_residuals(hydrostatic(G_EARTH), coefficients(0.0), centers, h)["mom_y"]
    assert torch.allclose(missing, torch.full_like(missing, G_EARTH * (rho - 1.0)), atol=1e-5)
    flipped = weak_residuals(hydrostatic(G_EARTH), coefficients(-G_EARTH), centers, h)["mom_y"]
    assert flipped.abs().min() > 1.0


def test_weak_momentum_matches_strong_form_plus_continuity_for_small_cells():
    # div(rho u u_i) = rho u.grad u_i + u_i div(rho u)
    centers, h = points(16) * 0.5, torch.full((16,), 0.02)
    coeffs = coefficients(G_EARTH)
    strong = physics_residuals(smooth_field, coeffs, centers)
    u, v = smooth_field(centers)[:, 0], smooth_field(centers)[:, 1]
    weak = weak_residuals(smooth_field, coeffs, centers, h)
    assert torch.allclose(weak["mom_x"].detach(), (strong["mom_x"] + u * strong["mass"]).detach(), atol=3e-3)
    assert torch.allclose(weak["mom_y"].detach(), (strong["mom_y"] + v * strong["mass"]).detach(), atol=3e-3)


def test_mass_residual_matches_strong_continuity():
    xy = points(16)
    strong = physics_residuals(smooth_field, coefficients(0.0), xy)["mass"]
    assert torch.allclose(mass_residual(smooth_field, xy).detach(), strong.detach())


def test_inverse_peclet_stays_positive():
    coeffs = Coefficients(INV_RE, TrainConfig(init_inverse_peclet=0.2))
    with torch.no_grad():
        coeffs.log_inv_pe.fill_(-30.0)
    assert coeffs.inverse_peclet > 0
