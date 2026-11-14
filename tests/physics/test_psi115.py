"""Loader tests use tiny synthetic files in the real PSI-115 format; the real-data test skips when files are absent."""
from pathlib import Path

import numpy as np
import pytest

from physics.psi115 import DEFAULT_DATA_DIR, FlowConstants, load_case, read_field, read_grid

NX, NY = 6, 4
PREFIX = "PSI-115_Analyzed Data_8cm"


def write_field(path: Path, values: np.ndarray, nx=NX, ny=NY) -> None:
    path.write_text(f"{nx} {ny} 1 1\n" + "\n".join(f"{v:.17g}" for v in values.ravel()) + "\n", encoding="ascii")


def write_case_files(root: Path, tag: str, temperature: np.ndarray) -> None:
    x, y = np.linspace(0, 5, NX), np.linspace(-1, 1, NY)
    xx, yy = np.meshgrid(x, y)
    coords = np.concatenate([xx.ravel(), yy.ravel(), np.zeros(NX * NY)])
    (root / f"{PREFIX}_sGrid_grid3d.dat").write_text(f"{NX} {NY} 1\n" + " ".join(f"{c:.17g}" for c in coords), encoding="ascii")
    write_field(root / f"{PREFIX}{tag}Temperature.dat", temperature)
    write_field(root / f"{PREFIX}{tag}U.dat", np.ones(NX * NY))
    write_field(root / f"{PREFIX}{tag}V.dat", np.zeros(NX * NY))


def test_loader_reads_fields_grid_and_block_mask(tmp_path):
    temperature = np.ones((NY, NX))
    temperature[1:3, 2:4] = FlowConstants().source_temperature_ratio
    write_case_files(tmp_path, "Gravity", temperature)

    case = load_case("earth", tmp_path)

    assert case.shape == (NY, NX)
    assert case.x[-1] == pytest.approx(5.0) and case.y[0] == pytest.approx(-1.0)
    assert case.source_mask.sum() == 4 and case.source_mask[1:3, 2:4].all()
    assert np.allclose(case.u, 1.0) and np.allclose(case.v, 0.0)
    assert np.allclose(case.density[~case.source_mask], 1.0)


def test_buoyancy_coefficient_depends_on_gravity_only():
    constants = FlowConstants()
    assert constants.buoyancy_coefficient(0.0) == 0.0
    assert constants.buoyancy_coefficient(9.81) == pytest.approx(-9.81 * 0.0044 / 0.08**2)  # about -6.74
    assert constants.buoyancy_coefficient(9.81) < 0  # +y up, gravity pulls down


def test_missing_files_name_the_download_command(tmp_path):
    with pytest.raises(FileNotFoundError, match="psi_download.py"):
        load_case("micro", tmp_path)


def test_unknown_gravity_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="gravity"):
        load_case("moon", tmp_path)  # type: ignore[arg-type]


def test_field_header_must_match_grid(tmp_path):
    path = tmp_path / "f.dat"
    write_field(path, np.zeros(NX * NY), nx=NX + 1, ny=NY)
    with pytest.raises(ValueError, match="does not match grid"):
        read_field(path, (NY, NX))


def test_grid_must_be_tensor_product(tmp_path):
    path = tmp_path / "g.dat"
    coords = np.arange(3 * NX * NY, dtype=float)  # not a tensor-product layout
    path.write_text(f"{NX} {NY} 1\n" + " ".join(map(str, coords)), encoding="ascii")
    with pytest.raises(ValueError, match="tensor-product"):
        read_grid(path)


@pytest.mark.skipif(not (DEFAULT_DATA_DIR / f"{PREFIX}_sGrid_grid3d.dat").is_file(), reason="PSI-115 files not downloaded")
def test_real_psi115_case_has_expected_geometry_and_scales():
    case = load_case("earth")
    assert case.shape == (240, 960)
    assert case.temperature.max() == pytest.approx(473.2 / 300.0, abs=1e-6)
    assert case.source_mask.sum() == 3800
    assert np.all(case.u[case.source_mask] == 0) and np.all(case.v[case.source_mask] == 0)
    assert case.expected_buoyancy == pytest.approx(-6.744, abs=0.01)
    assert load_case("micro").expected_buoyancy == 0.0
