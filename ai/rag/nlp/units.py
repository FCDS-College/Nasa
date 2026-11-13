"""Unit table (version-stamped). Matching is case-sensitive: `K` is kelvin, `k` is not a unit here."""
from __future__ import annotations

UNIT_TABLE_VERSION = "units-1.0.0"

# symbol -> (dimension, scale to SI, offset to SI, SI unit)
UNITS: dict[str, tuple[str, float, float, str]] = {
    "Pa": ("pressure", 1.0, 0.0, "Pa"), "kPa": ("pressure", 1e3, 0.0, "Pa"), "MPa": ("pressure", 1e6, 0.0, "Pa"),
    "bar": ("pressure", 1e5, 0.0, "Pa"), "mbar": ("pressure", 100.0, 0.0, "Pa"), "atm": ("pressure", 101325.0, 0.0, "Pa"),
    "psi": ("pressure", 6894.757293168, 0.0, "Pa"), "psia": ("pressure", 6894.757293168, 0.0, "Pa"),
    # mmHg is the conventional value, the same factor `flame_api.ingest.convert_to_si` applies to NASA's tables.
    # Torr is defined as exactly 1/760 atm, so the two differ by about 1.4e-7 (relative).
    "mmHg": ("pressure", 133.322387415, 0.0, "Pa"),
    "torr": ("pressure", 101325.0 / 760.0, 0.0, "Pa"), "Torr": ("pressure", 101325.0 / 760.0, 0.0, "Pa"),
    "K": ("temperature", 1.0, 0.0, "K"), "°C": ("temperature", 1.0, 273.15, "K"),
    "m/s": ("velocity", 1.0, 0.0, "m/s"), "cm/s": ("velocity", 0.01, 0.0, "m/s"), "mm/s": ("velocity", 0.001, 0.0, "m/s"),
    "µm": ("length", 1e-6, 0.0, "m"), "μm": ("length", 1e-6, 0.0, "m"), "mm": ("length", 1e-3, 0.0, "m"),
    "cm": ("length", 1e-2, 0.0, "m"), "m": ("length", 1.0, 0.0, "m"),
    "ms": ("time", 1e-3, 0.0, "s"), "s": ("time", 1.0, 0.0, "s"), "min": ("time", 60.0, 0.0, "s"),
    "mg": ("mass", 1e-6, 0.0, "kg"), "g": ("mass", 1e-3, 0.0, "kg"), "kg": ("mass", 1.0, 0.0, "kg"),
    "Hz": ("frequency", 1.0, 0.0, "Hz"),
    "W": ("power", 1.0, 0.0, "W"), "kW": ("power", 1e3, 0.0, "W"),
    "J": ("energy", 1.0, 0.0, "J"), "kJ": ("energy", 1e3, 0.0, "J"),
    "%": ("fraction", 0.01, 0.0, "1"), "vol%": ("fraction", 0.01, 0.0, "1"), "vol %": ("fraction", 0.01, 0.0, "1"),
    "mol%": ("fraction", 0.01, 0.0, "1"),
}


def to_si(value: float, unit: str) -> tuple[float, str]:
    _, scale, offset, si_unit = UNITS[unit]
    return value * scale + offset, si_unit
