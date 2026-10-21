"""Simulátor IoT vodoměrů – posílá telemetrii do bridge včetně občasných anomálií.

Konfigurace přes proměnné prostředí:
  API_URL     adresa endpointu (výchozí http://127.0.0.1:8000/api/v1/telemetry)
  API_KEY     API klíč bridge (povinné)
  METER_IDS   ID vodoměrů oddělená čárkou (výchozí vodomer111)
  INTERVAL    interval odesílání v sekundách (výchozí 5)
"""

import logging
import os
import random
import sys
import time
from datetime import UTC, datetime

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] IoT-Sim: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("simulator")

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1/telemetry")
API_KEY = os.getenv("API_KEY", "")
METER_IDS = [m.strip() for m in os.getenv("METER_IDS", "vodomer111").split(",") if m.strip()]
INTERVAL = float(os.getenv("INTERVAL", "5"))

SPIKE_CHANCE = 0.05  # nereálný skok hodnoty
NULL_CHANCE = 0.05  # výpadek hodnoty


class Meter:
    def __init__(self, meter_id: str):
        self.meter_id = meter_id
        self.consumption = 0.0
        self.battery = 100

    def next_payload(self) -> dict:
        # Průtok 0–3,6 m³/h nezávisle na intervalu odesílání
        self.consumption += random.uniform(0.0, 0.001) * INTERVAL
        # Pomalé vybíjení baterie
        self.battery = max(90, self.battery - random.choice([0, 0, 0, 0, 1]))

        value = round(self.consumption, 4)
        roll = random.random()
        if roll < SPIKE_CHANCE:
            value = 999.999
            logger.warning("[%s] SIMULACE ANOMÁLIE: skok měření na 999.999 m³", self.meter_id)
        elif roll < SPIKE_CHANCE + NULL_CHANCE:
            value = None
            logger.warning("[%s] SIMULACE ANOMÁLIE: výpadek hodnoty (null)", self.meter_id)

        return {
            "meter_id": self.meter_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "cumulative_consumption": value,
            "battery_level": self.battery,
            "signal_strength": random.randint(-85, -75),
        }


def send(session: requests.Session, payload: dict) -> None:
    try:
        response = session.post(API_URL, json=payload, timeout=5)
    except requests.RequestException as e:
        logger.critical("Chyba spojení s bridge (%s): %s", API_URL, e)
        return
    if response.status_code == 201:
        anomaly = response.json().get("anomaly")
        logger.info(
            "[%s] Odesláno %s m³ -> 201%s",
            payload["meter_id"],
            payload["cumulative_consumption"],
            f" (bridge hlásí anomálii: {anomaly})" if anomaly else "",
        )
    else:
        logger.error("[%s] Chyba API (%s): %s", payload["meter_id"], response.status_code, response.text)


def run_simulator() -> None:
    if not API_KEY:
        sys.exit("Nastavte proměnnou prostředí API_KEY (stejná hodnota jako v .env bridge).")

    meters = [Meter(meter_id) for meter_id in METER_IDS]
    logger.info("Spouštím IoT simulátor pro zařízení: %s", ", ".join(METER_IDS))
    logger.info("Cílové API: %s", API_URL)

    session = requests.Session()
    session.headers["X-API-Key"] = API_KEY
    try:
        while True:
            for meter in meters:
                send(session, meter.next_payload())
            time.sleep(INTERVAL)
    except KeyboardInterrupt:
        logger.info("Simulátor byl ručně vypnut.")


if __name__ == "__main__":
    run_simulator()
