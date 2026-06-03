import logging
from app.database import get_db_cursor
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class TelemetryService:
    @staticmethod
    def process_reading(meter_id: str, timestamp, cumulative_consumption: float, battery_level: int, signal_strength: int):
        """Zpracuje telemetrická data, zkontroluje anomálie a uloží je do DB."""
        
        # --- BUSINESS LOGIKA / DETEKCE ANOMÁLIÍ ---
        if cumulative_consumption is None:
            logger.warning(f"⚠️ ANOMÁLIE: Vodoměr {meter_id} poslal prázdnou hodnotu (NULL). Výpadek senzoru?")
        elif cumulative_consumption > 500.0:  # Tvůj simulátor posílá 999.999 jako ústřel
            logger.error(f"❌ KRITICKÁ ANOMÁLIE: Vodoměr {meter_id} detekoval nereálný ústřel spotřeby: {cumulative_consumption} m³!")
            # Tady by v reálném systému mohl být trigger na poslání e-mailu/notifikace správci
        
        # --- ZÁPIS DO DATABÁZE ---
        try:
            with get_db_cursor() as cur:
                query = """
                    INSERT INTO meter_readings (
                        meter_id, 
                        timestamp, 
                        cumulative_consumption, 
                        battery_level, 
                        signal_strength
                    ) VALUES (%s, %s, %s, %s, %s)
                """
                cur.execute(query, (
                    meter_id, 
                    timestamp, 
                    cumulative_consumption, 
                    battery_level, 
                    signal_strength
                ))
            
            logger.info(f"✅ Telemetrie úspěšně uložena pro vodoměr: {meter_id} ({cumulative_consumption} m³)")
            return {"status": "saved"}

        except Exception as e:
            logger.error(f"Selhal zápis telemetrie do DB pro vodoměr {meter_id}: {e}")
            raise HTTPException(status_code=500, detail="Chyba při ukládání telemetrických dat do databáze.")