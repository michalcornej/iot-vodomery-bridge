import logging
from datetime import datetime

from app.config import settings
from app.database import get_db_cursor
from app.exceptions import StorageError

logger = logging.getLogger(__name__)

ANOMALY_MISSING_VALUE = "missing_value"
ANOMALY_DECREASE = "consumption_decrease"
ANOMALY_SPIKE = "consumption_spike"


def detect_anomaly(
    cumulative_consumption: float | None,
    timestamp: datetime,
    previous: tuple[float, datetime] | None,
    max_flow_rate: float,
) -> str | None:
    """Vrátí kód anomálie, nebo None, pokud je měření v pořádku.

    Stav vodoměru je kumulativní – nesmí klesat a nesmí růst rychleji, než
    dovoluje maximální průtok. Porovnává se s posledním platným měřením
    téhož vodoměru před tímto časem.
    """
    if cumulative_consumption is None:
        return ANOMALY_MISSING_VALUE
    if previous is None:
        return None  # první měření vodoměru není s čím porovnat

    prev_value, prev_timestamp = previous
    delta = cumulative_consumption - prev_value
    if delta < 0:
        return ANOMALY_DECREASE

    hours = (timestamp - prev_timestamp).total_seconds() / 3600
    # Minimálně 1 s, aby dvě měření se stejným časem nevedla k dělení nulou
    if delta / max(hours, 1 / 3600) > max_flow_rate:
        return ANOMALY_SPIKE
    return None


class TelemetryService:
    @staticmethod
    def process_reading(
        meter_id: str,
        timestamp: datetime,
        cumulative_consumption: float | None,
        battery_level: int,
        signal_strength: int,
    ) -> dict:
        """Zkontroluje měření na anomálie a uloží ho do DB i s výsledkem kontroly."""
        try:
            with get_db_cursor() as cur:
                cur.execute(
                    """
                    SELECT cumulative_consumption, timestamp
                    FROM meter_readings
                    WHERE meter_id = %s
                      AND timestamp < %s
                      AND cumulative_consumption IS NOT NULL
                      AND NOT is_anomaly
                    ORDER BY timestamp DESC
                    LIMIT 1
                    """,
                    (meter_id, timestamp),
                )
                row = cur.fetchone()
                previous = (float(row[0]), row[1]) if row else None

                anomaly = detect_anomaly(
                    cumulative_consumption, timestamp, previous, settings.MAX_FLOW_RATE_M3_PER_HOUR
                )

                cur.execute(
                    """
                    INSERT INTO meter_readings (
                        meter_id, timestamp, cumulative_consumption,
                        battery_level, signal_strength, is_anomaly, anomaly_reason
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        meter_id,
                        timestamp,
                        cumulative_consumption,
                        battery_level,
                        signal_strength,
                        anomaly is not None,
                        anomaly,
                    ),
                )
                reading_id = cur.fetchone()[0]
        except Exception as e:
            logger.error("Selhal zápis telemetrie do DB pro vodoměr %s: %s", meter_id, e)
            raise StorageError("Chyba při ukládání telemetrických dat do databáze.") from e

        if anomaly == ANOMALY_MISSING_VALUE:
            logger.warning("ANOMÁLIE: vodoměr %s poslal prázdnou hodnotu (výpadek senzoru?)", meter_id)
        elif anomaly:
            logger.error(
                "ANOMÁLIE (%s): vodoměr %s, hodnota %s m³, předchozí platná %s",
                anomaly,
                meter_id,
                cumulative_consumption,
                previous[0] if previous else None,
            )
        else:
            logger.info("Telemetrie uložena pro vodoměr %s (%s m³)", meter_id, cumulative_consumption)

        return {"status": "saved", "id": reading_id, "anomaly": anomaly}
