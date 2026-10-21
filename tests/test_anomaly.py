from datetime import UTC, datetime, timedelta

from app.services.telemetry_service import (
    ANOMALY_DECREASE,
    ANOMALY_MISSING_VALUE,
    ANOMALY_SPIKE,
    detect_anomaly,
)

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
MAX_RATE = 10.0


def test_missing_value():
    assert detect_anomaly(None, T0, None, MAX_RATE) == ANOMALY_MISSING_VALUE


def test_first_reading_is_ok():
    assert detect_anomaly(999.999, T0, None, MAX_RATE) is None


def test_normal_increase():
    assert detect_anomaly(12.005, T0 + timedelta(seconds=5), (12.0, T0), MAX_RATE) is None


def test_decrease():
    assert detect_anomaly(11.9, T0 + timedelta(seconds=5), (12.0, T0), MAX_RATE) == ANOMALY_DECREASE


def test_spike():
    assert detect_anomaly(999.999, T0 + timedelta(seconds=5), (12.0, T0), MAX_RATE) == ANOMALY_SPIKE


def test_large_value_after_long_gap_is_ok():
    # Velký přírůstek za dlouhou dobu není anomálie – pevný práh by tu chybně alarmoval
    assert detect_anomaly(612.0, T0 + timedelta(days=30), (12.0, T0), MAX_RATE) is None


def test_same_timestamp_does_not_divide_by_zero():
    assert detect_anomaly(12.0, T0, (12.0, T0), MAX_RATE) is None
    assert detect_anomaly(13.0, T0, (12.0, T0), MAX_RATE) == ANOMALY_SPIKE
