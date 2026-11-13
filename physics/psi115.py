"""Loader and constants for the NASA PSI-115 smoke-aerosol simulation fields.

PSI-115 ("Utilization of the SAME data for advanced modeling and simulation of smoke generation in
microgravity", Garrick) ships the steady 2D flow solution for air blown past a heated block, once at
Earth gravity and once at microgravity. That makes it the only local dataset with temperature and
velocity fields for the *same* geometry at two gravity levels, which is what a gravity-aware model needs.

What the data is (and is not):
  * Numerical simulation output, not a measurement. Parameters recovered from it validate the physics
    formulation; they are not an experimental result.
  * A heated surface expelling vapour (pre-combustion smoke), so there is no chemical heat release.
  * Dimensionless: lengths by Lo = 4.4 mm, velocity by Uo = 0.08 m/s, temperature by To = 300 K.
  * 960 x 240 non-uniform grid, x in [0, 40], y in [-3.41, 3.41], +y up. Heated block near x in [11, 12].

Download the files with
    python knowledge/ingestion/psi_download.py datasets/manifests/psi115_pinn_selection.csv
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[1] / "datasets" / "raw" / "psi_api" / "PSI-115" / "Analyzed Data"
EARTH_GRAVITY_MS2 = 9.81

_PREFIX = "PSI-115_Analyzed Data_8cm"
_GRID_NAME = "PSI-115_Analyzed Data_8cm_sGrid_grid3d.dat"
_GRAVITY_TAG = {"earth": "Gravity", "micro": "NoGravity"}
_DOWNLOAD_HINT = "python knowledge/ingestion/psi_download.py datasets/manifests/psi115_pinn_selection.csv"

Gravity = Literal["earth", "micro"]


@dataclass(frozen=True)
class FlowConstants:
    """Reference scales of PSI-115 Case 1 (final report, section 4.2)."""

    reynolds: float = 22.3
    # Not stated in the report; standard value for air. The Peclet number is inferred from data anyway.
    prandtl: float = 0.71
    length_m: float = 0.0044
    inlet_velocity_ms: float = 0.08
    ambient_temperature_k: float = 300.0
    source_temperature_k: float = 473.2

    @property
    def source_temperature_ratio(self) -> float:
        return self.source_temperature_k / self.ambient_temperature_k

    @property
    def inverse_peclet(self) -> float:
        return 1.0 / (self.reynolds * self.prandtl)

    def buoyancy_coefficient(self, gravity_ms2: float) -> float:
        """Signed coefficient G of the y-momentum body force G*(rho* - 1), i.e. -1/Fr^2 with +y up.

        G = -g*Lo/Uo^2. It is negative at Earth gravity (about -6.74) and exactly 0 in microgravity.
        """
        return -gravity_ms2 * self.length_m / self.inlet_velocity_ms**2


@dataclass(frozen=True)
class FlowCase:
    """One gravity level: coordinates, dimensionless fields on the (ny, nx) grid, and the heated-block mask."""

    name: str
    gravity_ms2: float
    x: np.ndarray  # (nx,)
    y: np.ndarray  # (ny,)
    temperature: np.ndarray  # (ny, nx), T / To
    u: np.ndarray  # (ny, nx), u / Uo
    v: np.ndarray  # (ny, nx), v / Uo
    source_mask: np.ndarray  # (ny, nx) bool, True inside the heated block
    constants: FlowConstants = FlowConstants()

    @property
    def shape(self) -> tuple[int, int]:
        return self.temperature.shape

    @property
    def expected_buoyancy(self) -> float:
        return self.constants.buoyancy_coefficient(self.gravity_ms2)

    @property
    def density(self) -> np.ndarray:
        """Dimensionless density rho/rho_o = 1/T*, valid for low-Mach flow at near-constant pressure."""
        return 1.0 / self.temperature


def read_field(path: Path, shape: tuple[int, int]) -> np.ndarray:
    """Read one Tecplot-style field file: a header 'ni nj 1 1' then ni*nj values with x varying fastest."""
    ny, nx = shape
    with path.open(encoding="ascii") as fh:
        header = fh.readline().split()
        if [int(h) for h in header[:2]] != [nx, ny]:
            raise ValueError(f"{path.name}: header {header} does not match grid {nx}x{ny}")
        values = np.array(fh.read().split(), dtype=float)
    if values.size != nx * ny:
        raise ValueError(f"{path.name}: expected {nx * ny} values, found {values.size}")
    return values.reshape(ny, nx)


def read_grid(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Return 1D (x, y) coordinates from the stacked x/y/z grid file (a tensor-product grid)."""
    tokens = path.read_text(encoding="ascii").split()
    nx, ny, nz = (int(t) for t in tokens[:3])
    if nz != 1:
        raise ValueError(f"{path.name}: expected a 2D grid, got nz={nz}")
    coords = np.asarray(tokens[3:], dtype=float)
    if coords.size != 3 * nx * ny:
        raise ValueError(f"{path.name}: expected {3 * nx * ny} coordinates, found {coords.size}")
    xs, ys = coords[: nx * ny].reshape(ny, nx), coords[nx * ny : 2 * nx * ny].reshape(ny, nx)
    if not (np.allclose(xs, xs[0]) and np.allclose(ys, ys[:, :1])):
        raise ValueError(f"{path.name}: grid is not a tensor-product grid")
    return xs[0].copy(), ys[:, 0].copy()


def load_case(
    gravity: Gravity,
    data_dir: Path | str = DEFAULT_DATA_DIR,
    constants: FlowConstants = FlowConstants(),
) -> FlowCase:
    """Load the Case-1 (Uo = 0.08 m/s) fields for 'earth' or 'micro' gravity."""
    if gravity not in _GRAVITY_TAG:
        raise ValueError(f"gravity must be one of {sorted(_GRAVITY_TAG)}, got {gravity!r}")
    root = Path(data_dir)
    tag = _GRAVITY_TAG[gravity]
    paths = {k: root / f"{_PREFIX}{tag}{k}.dat" for k in ("Temperature", "U", "V")}
    missing = [p.name for p in [root / _GRID_NAME, *paths.values()] if not p.is_file()]
    if missing:
        raise FileNotFoundError(f"PSI-115 files missing in {root}: {missing}. Download with: {_DOWNLOAD_HINT}")

    x, y = read_grid(root / _GRID_NAME)
    shape = (y.size, x.size)
    temperature = read_field(paths["Temperature"], shape)
    u, v = read_field(paths["U"], shape), read_field(paths["V"], shape)
    # The block is isothermal at Ts and no-slip; the nearest-float tolerance absorbs file rounding.
    source_mask = np.isclose(temperature, constants.source_temperature_ratio, rtol=0, atol=1e-6)
    g = EARTH_GRAVITY_MS2 if gravity == "earth" else 0.0
    return FlowCase(f"psi115-case1-{gravity}", g, x, y, temperature, u, v, source_mask, constants)
