import time
import random
import requests
import logging
from datetime import datetime, timezone

# Nastavení čistého logování pro simulátor
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] IoT-Sim: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("simulator")

# URL adresa naší nové FastAPI platformy
API_URL = "http://127.0.0.1:8000/api/v1/telemetry"
METER_ID = "vodomer111" 
INIT_CONSUMPTION = 0.000 

def run_simulator():
    logger.info(f"🚀 Spouštím IoT simulátor pro zařízení: {METER_ID}")
    logger.info(f"📡 Cílové API: {API_URL}")
    
    current_consumption = INIT_CONSUMPTION
    battery = 100

    try:
        while True:
            # 1. Standardní simulace spotřeby vody
            water_flow = random.uniform(0.000, 0.005)
            current_consumption += water_flow
            
            # Simulace pomalého vybíjení baterie
            battery = max(90, battery - random.choice([0, 0, 0, 0, 1]))
            signal = random.randint(-85, -75)
            now = datetime.now(timezone.utc)

            # --- LOGIKA ANOMÁLIÍ (Testování robustnosti bridge) ---
            error_chance = random.randint(0, 100)
            display_consumption = round(current_consumption, 4)

            if error_chance < 5:  # 5% šance na totální ústřel (neplatná data)
                display_consumption = 999.999
                logger.warning("🚨 [SIMULACE ANOMÁLIE] Generuji kritický ústřel měření (999.999 m³)...")
                
            elif error_chance < 10:  # Dalších 5% šance na výpadek signálu/dat
                display_consumption = None
                logger.warning("🚨 [SIMULACE ANOMÁLIE] Generuji výpadek hodnoty (NULL)...")

            # --- SESTAVENÍ PAYLOADU ---
            payload = {
                "meter_id": METER_ID,
                "timestamp": now.isoformat(),
                "cumulative_consumption": display_consumption,
                "battery_level": battery,
                "signal_strength": signal
            }

            # --- ODESLÁNÍ DO BRIDGE ---
            try:
                response = requests.post(API_URL, json=payload, timeout=5)
                if response.status_code == 201:
                    logger.info(f"Odesláno -> {current_consumption:.4f} m³ | Odpověď API: 201 Saved")
                else:
                    logger.error(f"Chyba API ({response.status_code}): {response.text}")
            except requests.exceptions.ConnectionError:
                logger.critical("❌ Chyba spojení: Integrační Bridge na portu 8000 neběží!")
            
            # Interval odesílání telemetrie
            time.sleep(5)

    except KeyboardInterrupt:
        logger.info("\n🛑 Jednotka simulátoru byla ručně vypnuta.")

if __name__ == "__main__":
    run_simulator()