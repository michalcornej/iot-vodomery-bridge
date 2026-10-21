from unittest import mock

import pytest
from fastapi.testclient import TestClient

from app.exceptions import NotFoundError
from app.main import app

HEADERS = {"X-API-Key": "test-key"}
READING = {
    "meter_id": "vodomer111",
    "timestamp": "2026-01-01T12:00:00+00:00",
    "cumulative_consumption": 12.3456,
    "battery_level": 95,
    "signal_strength": -80,
}


@pytest.fixture
def client():
    # Bez `with` se nespouští lifespan, takže se nepřipojuje k databázi
    return TestClient(app)


def test_health_needs_no_key(client):
    assert client.get("/health").json() == {"status": "ok"}


@pytest.mark.parametrize("headers", [{}, {"X-API-Key": "wrong"}])
def test_endpoints_require_api_key(client, headers):
    assert client.post("/api/v1/telemetry", json=READING, headers=headers).status_code == 401
    files = {"file": ("a.csv", b"x", "text/csv")}
    assert client.post("/api/v1/import-order", files=files, headers=headers).status_code == 401


def test_telemetry_saved(client):
    result = {"status": "saved", "id": 7, "anomaly": None}
    with mock.patch("app.main.TelemetryService.process_reading", return_value=result) as process:
        response = client.post("/api/v1/telemetry", json=READING, headers=HEADERS)
    assert response.status_code == 201
    assert response.json() == result
    assert process.call_args.kwargs["meter_id"] == "vodomer111"


def test_telemetry_null_consumption_is_accepted(client):
    result = {"status": "saved", "id": 8, "anomaly": "missing_value"}
    with mock.patch("app.main.TelemetryService.process_reading", return_value=result):
        response = client.post("/api/v1/telemetry", json=READING | {"cumulative_consumption": None}, headers=HEADERS)
    assert response.status_code == 201


@pytest.mark.parametrize(
    "override",
    [
        {"timestamp": "2026-01-01T12:00:00"},  # bez časové zóny
        {"cumulative_consumption": -1},
        {"battery_level": 101},
        {"signal_strength": 10},
        {"meter_id": ""},
        {"meter_id": "vodoměr 1"},
    ],
)
def test_telemetry_validation(client, override):
    assert client.post("/api/v1/telemetry", json=READING | override, headers=HEADERS).status_code == 422


@pytest.mark.parametrize("filename", ["objednavka.txt", "objednavka"])
def test_import_rejects_non_csv(client, filename):
    files = {"file": (filename, b"x", "text/plain")}
    response = client.post("/api/v1/import-order", files=files, headers=HEADERS)
    assert response.status_code == 400


def test_import_accepts_uppercase_extension(client):
    with mock.patch("app.main.order_service.import_from_csv", return_value={"status": "success"}) as imp:
        files = {"file": ("OBJEDNAVKA.CSV", b"data", "text/csv")}
        response = client.post("/api/v1/import-order", files=files, headers=HEADERS)
    assert response.status_code == 200
    imp.assert_called_once_with(b"data")


def test_import_too_large(client):
    with mock.patch("app.main.settings.MAX_UPLOAD_BYTES", 10):
        files = {"file": ("a.csv", b"x" * 11, "text/csv")}
        response = client.post("/api/v1/import-order", files=files, headers=HEADERS)
    assert response.status_code == 413


def test_domain_errors_are_mapped_to_http(client):
    error = NotFoundError("Zákazník 'X' nebyl v Odoo nalezen.")
    with mock.patch("app.main.order_service.import_from_csv", side_effect=error):
        files = {"file": ("a.csv", b"data", "text/csv")}
        response = client.post("/api/v1/import-order", files=files, headers=HEADERS)
    assert response.status_code == 404
    assert response.json() == {"detail": "Zákazník 'X' nebyl v Odoo nalezen."}
