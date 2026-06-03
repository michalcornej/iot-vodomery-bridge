import logging
from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

# Importy našich vlastních služeb a konfigurace
from app.services.telemetry_service import TelemetryService
from app.services.order_service import OrderService

# Nastavení profesionálního logování
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("odoo_bridge")

app = FastAPI(
    title="Odoo Bridge & Telemetry Platform",
    description="Enterprise-ready integrační platforma pro ingest IoT telemetrie a synchronizaci objednávek do Odoo ERP.",
    version="1.0.0"
)

# --- PYDANTIC SCHÉMATA PRO VALIDACI VSTUPŮ ---

class TelemetryInput(BaseModel):
    meter_id: str = Field(..., description="Unikátní ID vodoměru", example="vodomer111")
    timestamp: datetime = Field(..., description="Čas měření v ISO formátu")
    cumulative_consumption: Optional[float] = Field(None, description="Celková kumulativní spotřeba v m³", example=12.3456)
    battery_level: int = Field(..., description="Stav baterie v % (0-100)", ge=0, le=100, example=95)
    signal_strength: int = Field(..., description="Síla signálu v dBm", example=-80)

# --- 1. ENDPOINT PRO TELEMETRII (IoT Ingest) ---

@app.post("/api/v1/telemetry", status_code=201, tags=["IoT Telemetry"])
async def receive_telemetry(data: TelemetryInput):
    """
    Endpoint pro příjem dat z IoT vodoměrů.
    Validuje vstup, kontroluje anomálie a ukládá data do PostgreSQL databáze.
    """
    logger.info(f"Přijat HTTP POST požadavek na telemetrii od zařízení: {data.meter_id}")
    
    response = TelemetryService.process_reading(
        meter_id=data.meter_id,
        timestamp=data.timestamp,
        cumulative_consumption=data.cumulative_consumption,
        battery_level=data.battery_level,
        signal_strength=data.signal_strength
    )
    return response

# --- 2. ENDPOINT PRO CSV IMPORT (ERP Integrace) ---

@app.post("/api/v1/import-order", tags=["ERP Integration"])
async def import_order_from_csv(file: UploadFile = File(..., description="CSV soubor s objednávkou v kódování CP1250")):
    """
    Endpoint pro hromadný nebo kusový import prodejních objednávek z externího CSV souboru.
    Zajistí validaci entit v Odoo a vytvoří prodejní objednávku (Sale Order).
    """
    logger.info(f"Přijat požadavek na CSV import souboru: {file.filename}")
    
    response = OrderService.import_from_csv(file)
    return response

# Spuštění aplikace v debug režimu, pokud skript pustíš napřímo přes Python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)