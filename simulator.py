import time
import random
import requests
from datetime import datetime, timezone

# URL adresa našeho Bridge (běží na portu 8000)
API_URL = "http://127.0.0.1:8000/api/v1/telemetry"

METER_ID = "vodomer111" 
INIT_CONSUMPTION = 0.000 

def run_simulator():
    print(f"Spouštím HTTP simulátor pro: {METER_ID}")
    
    current_consumption = INIT_CONSUMPTION
    battery = 100

    try:
        while True:
            # Simulace spotřeby
            water_flow = random.uniform(0.000, 0.005)
            current_consumption += water_flow
            
            battery = max(90, battery - random.choice([0, 0, 0, 0, 1]))
            signal = random.randint(-85, -75)
            
            now = datetime.now(timezone.utc)

            # JSON balíček pro Bridge
            payload = {
                "meter_id": METER_ID,
                "timestamp": now.isoformat(),
                "cumulative_consumption": round(current_consumption, 4),
                "battery_level": battery,
                "signal_strength": signal
            }

            try:
                response = requests.post(API_URL, json=payload)
                if response.status_code == 201:
                    print(f"[{now.strftime('%H:%M:%S')}] Odesláno -> {current_consumption:.4f} m³ | API: OK")
                else:
                    print(f"[{now.strftime('%H:%M:%S')}] Chyba API ({response.status_code}): {response.text}")
            except requests.exceptions.ConnectionError:
                print(f"[{now.strftime('%H:%M:%S')}] Chyba: Bridge na portu 8000 neběží!")
            
            time.sleep(5)

    except KeyboardInterrupt:
        print("\nSimulátor zastaven.")

if __name__ == "__main__":
    run_simulator()