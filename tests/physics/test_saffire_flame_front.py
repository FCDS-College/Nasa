"""The front tracker must recover a known moving step and chain two shifted cameras (synthetic profiles, no image data needed)."""
import numpy as np

from physics.saffire_flame_front import (
    Profiles,
    camera_offset,
    combine,
    fit_line,
    lit_edges,
    moving_part,
)

W = 400


def synthetic(start_col: float, speed: float, n: int = 600, dt: float = 0.5, lit_every: int = 3) -> Profiles:
    """Bright fabric left of a front that moves left at `speed` columns/s; only every `lit_every`-th frame is lit."""
    t = np.arange(n) * dt
    cols = np.arange(W)
    green = np.full((n, W), 2.5, dtype=np.float32)
    mean_green = np.full(n, 2.4, dtype=np.float32)
    for i in range(0, n, lit_every):
        front = start_col - speed * t[i]
        green[i] = np.where(cols < front, 190.0, 20.0)
        mean_green[i] = green[i].mean()
    return Profiles((1_000_000 + t * 1000).astype(np.int64), mean_green, green, np.full((n, W), 3.0, dtype=np.float32))


def test_lit_edge_recovers_a_linear_front():
    t, edge = lit_edges(synthetic(380.0, 1.0))
    slope, resid, _ = fit_line(t, edge, t.min(), t.max())
    assert abs(slope + 1.0) < 0.01 and resid < 0.6


def test_unlit_frames_are_ignored():
    prof = synthetic(380.0, 1.0, lit_every=3)
    t, _ = lit_edges(prof)
    assert len(t) == len(range(0, 600, 3))


def test_moving_part_drops_the_card_margin_plateau():
    t = np.arange(10.0)
    edge = np.array([380, 380, 370, 300, 200, 100, 60, 60, 60, 60.0])
    kept_t, kept_e = moving_part(t, edge, 65, 365)
    assert kept_t.tolist() == [3.0, 4.0, 5.0] and kept_e.tolist() == [300.0, 200.0, 100.0]


def test_two_cameras_chain_into_one_track_with_the_shift_removed():
    shift = 220.0
    ta = np.arange(0, 300.0, 0.5)
    ea = 370 - 1.0 * ta  # camera 1 sees the front for 0..300 s
    tb = np.arange(100, 400.0, 0.5)
    eb = (370 - 1.0 * tb) + shift  # camera 2 sees the same front, shifted by +220 columns
    off, sd = camera_offset(ta, ea, tb, eb, window=(150.0, 250.0))
    assert abs(off - shift) < 0.5 and sd < 0.5
    t, e = combine(ta, ea, tb, eb, off, handover=250.0)
    slope, resid, _ = fit_line(t, e, 10, 390)
    assert abs(slope + 1.0) < 0.01 and resid < 0.6
    assert np.all(np.diff(t) >= 0)
