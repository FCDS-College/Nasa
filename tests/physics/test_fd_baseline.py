"""The finite-difference baseline must recover the known gravity coefficient from the real PSI-115 fields."""
import pytest

from physics.fd_baseline import estimate_parameters_fd, fluid_interior_mask
from physics.psi115 import DEFAULT_DATA_DIR, load_case

pytestmark = pytest.mark.skipif(
    not (DEFAULT_DATA_DIR / "PSI-115_Analyzed Data_8cm_sGrid_grid3d.dat").is_file(), reason="PSI-115 files not downloaded"
)


@pytest.fixture(scope="module")
def earth():
    return load_case("earth")


@pytest.fixture(scope="module")
def micro():
    return load_case("micro")


def test_earth_gravity_buoyancy_recovered_with_correct_sign(earth):
    est = estimate_parameters_fd(earth)
    assert est.buoyancy < 0  # +y up
    assert est.buoyancy == pytest.approx(earth.expected_buoyancy, rel=0.10)  # observed: about -6.57 vs -6.74
    assert est.buoyancy_r2 > 0.4


def test_microgravity_buoyancy_is_zero(micro):
    est = estimate_parameters_fd(micro)
    assert abs(est.buoyancy) < 0.2  # observed: about 0.015


@pytest.mark.parametrize("fixture", ["earth", "micro"])
def test_thermal_peclet_matches_nominal_reynolds_prandtl(fixture, request):
    case = request.getfixturevalue(fixture)
    est = estimate_parameters_fd(case)
    assert est.inverse_peclet == pytest.approx(case.constants.inverse_peclet, rel=0.15)  # observed: within about 10%
    assert est.inverse_peclet_r2 > 0.7


def test_mask_excludes_block_surroundings_and_edges(earth):
    mask = fluid_interior_mask(earth, margin_cells=4, edge_cells=6)
    assert not mask[earth.source_mask].any()
    assert not mask[:6].any() and not mask[:, :6].any() and not mask[:, -6:].any()
    assert mask.sum() > 100_000
