"""Test Modbus register decoding logic (pure function, no I/O)."""
import os

import pytest

os.environ.setdefault("SECRET_KEY", "x" * 64)

from app.workers.modbus_poller import _decode_registers


def test_float32_decode():
    # 1.0 in IEEE 754 big-endian = 0x3F800000 = [0x3F80, 0x0000]
    assert _decode_registers([0x3F80, 0x0000], "float32") == pytest.approx(1.0)


def test_float32_negative():
    # -1.5 = 0xBFC00000 = [0xBFC0, 0x0000]
    assert _decode_registers([0xBFC0, 0x0000], "float32") == pytest.approx(-1.5)


def test_int32_decode():
    # 100000 = 0x000186A0 = [0x0001, 0x86A0]
    assert _decode_registers([0x0001, 0x86A0], "int32") == 100000.0


def test_int32_negative():
    # -1 = 0xFFFFFFFF
    assert _decode_registers([0xFFFF, 0xFFFF], "int32") == -1.0


def test_uint32():
    # 0xFFFFFFFF as unsigned = 4294967295
    assert _decode_registers([0xFFFF, 0xFFFF], "uint32") == 4294967295.0


def test_int16():
    assert _decode_registers([0x7FFF], "int16") == 32767.0
    assert _decode_registers([0x8000], "int16") == -32768.0


def test_uint16():
    assert _decode_registers([0x8000], "uint16") == 32768.0


def test_invalid_data_type():
    with pytest.raises(ValueError):
        _decode_registers([0, 0], "garbage")


def test_float32_too_few_registers():
    with pytest.raises(ValueError):
        _decode_registers([0x3F80], "float32")
