"""Test MQTT topic parsing."""
import os

os.environ.setdefault("SECRET_KEY", "x" * 64)

from app.workers.mqtt_subscriber import _parse_topic


def test_parse_data_topic():
    kind, site, sensor = _parse_topic("sites/SITE-001/sensors/INC-X/data")
    assert kind == "data"
    assert site == "SITE-001"
    assert sensor == "INC-X"


def test_parse_heartbeat_topic():
    kind, site, sensor_or_device = _parse_topic("sites/SITE-001/devices/DL-001/heartbeat")
    assert kind == "heartbeat"
    assert site == "SITE-001"
    assert sensor_or_device == "DL-001"


def test_parse_unknown_topic():
    kind, _, _ = _parse_topic("garbage/topic")
    assert kind == "unknown"


def test_parse_too_few_parts():
    kind, _, _ = _parse_topic("sites/x/sensors")
    assert kind == "unknown"
