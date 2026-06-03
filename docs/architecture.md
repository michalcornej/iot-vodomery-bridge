# Architektura Integrační Platformy

Tento systém funguje jako vícezdrojový integrační bridge (Multi-source Integration Platform) propojující svět průmyslových IoT/OT zařízení s podnikovým ERP systémem Odoo a lokálním datovým skladem (PostgreSQL).

## Tok Dat & Komponenty

1. **Simulační vrstva (OT Edge Simulator)**
   - Generuje telemetrická data z vodoměrů (ID zařízení, časové razítko, kumulativní spotřeba, stav baterie, signál).
   - Pravidelně simuluje anomálie (ústřely dat, prázdné hodnoty/NULL) pro otestování robustnosti validačních mechanismů na straně API.

2. **Ingest vrstva (FastAPI Backend)**
   - **Tenká kontrolerová vrstva:** Endpointy pouze validují strukturu dat pomocí Pydantic schémat a řídí HTTP odpovědi.
   - **Izolované aplikační služby:** `TelemetryService` zpracovává telemetrii a vyhodnocuje anomálie, `OrderService` spravuje importy.

3. **Datová a ERP vrstva**
   - **PostgreSQL:** Uchovává kompletní časové řady (Time-series data) telemetrických měření pro pozdější business analýzu a reporting.
   - **Odoo ERP (XML-RPC):** Integrační most provádí orchestraci objednávek z externích prodejních kanálů (CSV) do ERP modulů `res.partner`, `product.product` a `sale.order`.