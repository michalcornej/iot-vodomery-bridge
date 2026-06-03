from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import csv
import codecs
import xmlrpc.client
import traceback
import psycopg2  # Přidáno pro zápis do DB

app = FastAPI(title="Odoo Bridge & Telemetry")

# --- KONFIGURACE POSTGRESQL (Tady si doplň své heslo!) ---
DB_CONFIG = {
    "dbname": "postgres",           # <--- TADY ZMĚŇ "odoo_vodomery" NA "postgres"
    "user": "postgres",
    "password": "uno12xx", 
    "host": "127.0.0.1",
    "port": "5432"
}

class TelemetryData(BaseModel):
    meter_id: str
    timestamp: datetime
    cumulative_consumption: Optional[float] = None
    battery_level: int
    signal_strength: int

# --- 1. ENDPOINT PRO TELEMETRII (Teď už i zapisuje!) ---
@app.post("/api/v1/telemetry", status_code=201)
async def receive_telemetry(data: TelemetryData):
    conn = None
    try:
        # 1. Připojení k PostgreSQL
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # 2. SQL Příkaz pro vložení dat
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
            data.meter_id, 
            data.timestamp, 
            data.cumulative_consumption, 
            data.battery_level, 
            data.signal_strength
        ))

        # 3. Potvrzení změn
        conn.commit()
        cur.close()
        
        print(f"✅ DB ZÁPIS: {data.meter_id} | {data.cumulative_consumption} m3")
        return {"status": "saved"}

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ CHYBA ZÁPISU DO DB: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Chyba při zápisu do databáze.")
    finally:
        if conn:
            conn.close()

# --- 2. ENDPOINT PRO CSV IMPORT (Zůstává beze změn) ---
@app.post("/api/v1/import-order")
async def import_order_from_csv(file: UploadFile = File(...)):
    # ... (tady zůstává tvůj kód pro Odoo import, jak ho máš)
    pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)