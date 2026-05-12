"""Test pure threshold-evaluation logic.

`evaluate_thresholds()` from the service hits the DB to load the device.
Here we test only the inner range comparison helper `_exceeds`.
"""
import os

os.environ.setdefault("SECRET_KEY", "x" * 64)

from app.services.threshold_service import _exceeds


def test_within_range():
    assert _exceeds(0.5, -1.0, 1.0) is False


def test_below_min():
    assert _exceeds(-2.0, -1.0, 1.0) is True


def test_above_max():
    assert _exceeds(1.5, -1.0, 1.0) is True


def test_one_sided_max_only():
    # max-only threshold (no min)
    assert _exceeds(50.0, None, 80.0) is False
    assert _exceeds(90.0, None, 80.0) is True
    assert _exceeds(-100.0, None, 80.0) is False  # No lower bound


def test_one_sided_min_only():
    assert _exceeds(10.0, 5.0, None) is False
    assert _exceeds(2.0, 5.0, None) is True


def test_no_bounds():
    # No thresholds defined → never exceeds
    assert _exceeds(99999.0, None, None) is False


def test_exact_boundary():
    # Boundary value is NOT a breach (uses < and >, not <= / >=)
    assert _exceeds(1.0, -1.0, 1.0) is False
    assert _exceeds(-1.0, -1.0, 1.0) is False
