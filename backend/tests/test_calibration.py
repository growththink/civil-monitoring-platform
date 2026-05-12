"""Test calibration math used by ingestion service."""
import os

import pytest

os.environ.setdefault("SECRET_KEY", "x" * 64)


def calibrate(raw: float, offset: float, scale: float) -> float:
    """Mirror of the inline expression in ingest_one_reading()."""
    return (raw + offset) * scale


def test_identity_calibration():
    assert calibrate(123.456, 0.0, 1.0) == 123.456


def test_scale_only():
    assert calibrate(2.0, 0.0, 0.5) == pytest.approx(1.0)


def test_offset_only():
    assert calibrate(10.0, -5.0, 1.0) == pytest.approx(5.0)


def test_offset_and_scale():
    # Common ADC pattern: raw counts → engineering units
    assert calibrate(2048, -2048, 0.001) == pytest.approx(0.0)
    assert calibrate(4096, -2048, 0.001) == pytest.approx(2.048)


def test_negative_scale_inversion():
    assert calibrate(100, 0, -1) == -100
