"""Integrační test proti skutečnému PostgreSQL.

Spustí se jen při nastavené proměnné TEST_DB=1 (a DB_* proměnných),
např. v CI se službou postgres. Vyžaduje schéma z db/init.sql.
"""

import os
from datetime import UTC, datetime, timedelta

import pytest

from app import database
from app.services.telemetry_service import TelemetryService

pytestmark = pytest.mark.skipif(os.getenv("TEST_DB") != "1", reason="Nastavte TEST_DB=1 pro test s databází")

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


@pytest.fixture
def meter_id():
    meter = f"test-{os.getpid()}"
    yield meter
    with database.get_db_cursor() as cur:
        cur.execute("DELETE FROM meter_readings WHERE meter_id = %s", (meter,))


def save(meter_id, seconds, value):
    return TelemetryService.process_reading(meter_id, T0 + timedelta(seconds=seconds), value, 95, -80)


def test_anomalies_are_flagged_and_excluded_from_baseline(meter_id):
    assert save(meter_id, 0, 10.0)["anomaly"] is None
    assert save(meter_id, 5, 999.999)["anomaly"] == "consumption_spike"
    assert save(meter_id, 10, None)["anomaly"] == "missing_value"
    # Porovnává se s 10.0, ne se skokem 999.999
    assert save(meter_id, 15, 10.004)["anomaly"] is None
    assert save(meter_id, 20, 9.0)["anomaly"] == "consumption_decrease"

    with database.get_db_cursor() as cur:
        cur.execute(
            "SELECT is_anomaly, anomaly_reason FROM meter_readings WHERE meter_id = %s ORDER BY timestamp",
            (meter_id,),
        )
        rows = cur.fetchall()
    assert rows == [
        (False, None),
        (True, "consumption_spike"),
        (True, "missing_value"),
        (False, None),
        (True, "consumption_decrease"),
    ]
