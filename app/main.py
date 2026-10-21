import logging
import secrets
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from pydantic import AwareDatetime, BaseModel, Field

from app import database
from app.config import settings
from app.exceptions import BridgeError, InvalidInputError, PayloadTooLargeError
from app.services.order_service import order_service
from app.services.telemetry_service import TelemetryService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("odoo_bridge")


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_pool()
    yield
    database.close_pool()


app = FastAPI(
    title="Odoo Bridge & Telemetry Platform",
    description="Integrační platforma pro ingest IoT telemetrie a synchronizaci objednávek do Odoo ERP.",
    version="1.1.0",
    lifespan=lifespan,
)


@app.exception_handler(BridgeError)
async def bridge_error_handler(request: Request, exc: BridgeError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


# --- AUTENTIZACE ---

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(api_key: Annotated[str | None, Depends(api_key_header)]) -> None:
    expected = settings.API_KEY.get_secret_value()
    if not api_key or not secrets.compare_digest(api_key.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Chybí nebo je neplatný API klíč (hlavička X-API-Key).")


# --- PYDANTIC SCHÉMATA PRO VALIDACI VSTUPŮ ---


class TelemetryInput(BaseModel):
    meter_id: str = Field(
        ...,
        description="Unikátní ID vodoměru",
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9_.-]+$",
        examples=["vodomer111"],
    )
    timestamp: AwareDatetime = Field(..., description="Čas měření v ISO 8601 včetně časové zóny")
    cumulative_consumption: float | None = Field(
        None, description="Celková kumulativní spotřeba v m³ (null = výpadek senzoru)", ge=0, examples=[12.3456]
    )
    battery_level: int = Field(..., description="Stav baterie v % (0-100)", ge=0, le=100, examples=[95])
    signal_strength: int = Field(..., description="Síla signálu v dBm", ge=-150, le=0, examples=[-80])


class TelemetryResponse(BaseModel):
    status: str
    id: int
    anomaly: str | None = Field(None, description="Kód zjištěné anomálie, nebo null")


# --- ENDPOINTY ---
# Endpointy jsou záměrně synchronní (def): psycopg2 i XML-RPC blokují,
# FastAPI je proto spouští ve vláknovém poolu a neblokují event loop.


@app.get("/health", tags=["System"])
def health():
    return {"status": "ok"}


@app.post(
    "/api/v1/telemetry",
    status_code=201,
    response_model=TelemetryResponse,
    tags=["IoT Telemetry"],
    dependencies=[Depends(require_api_key)],
)
def receive_telemetry(data: TelemetryInput):
    """Příjem dat z IoT vodoměrů. Měření se uloží vždy, anomálie se označí."""
    logger.info("Přijata telemetrie od zařízení %s", data.meter_id)
    return TelemetryService.process_reading(
        meter_id=data.meter_id,
        timestamp=data.timestamp,
        cumulative_consumption=data.cumulative_consumption,
        battery_level=data.battery_level,
        signal_strength=data.signal_strength,
    )


@app.post("/api/v1/import-order", tags=["ERP Integration"], dependencies=[Depends(require_api_key)])
def import_order_from_csv(
    file: Annotated[UploadFile, File(description="CSV soubor s objednávkami (CP1250 nebo UTF-8)")],
):
    """Import jedné nebo více prodejních objednávek z CSV do Odoo (Sale Order)."""
    logger.info("Přijat požadavek na CSV import souboru: %s", file.filename)

    if not (file.filename or "").lower().endswith(".csv"):
        raise InvalidInputError("Soubor musí být ve formátu CSV.")

    content = file.file.read(settings.MAX_UPLOAD_BYTES + 1)
    if len(content) > settings.MAX_UPLOAD_BYTES:
        raise PayloadTooLargeError(f"Soubor je větší než povolený limit {settings.MAX_UPLOAD_BYTES} B.")

    return order_service.import_from_csv(content)


# Spuštění v režimu vývoje: python -m app.main
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
