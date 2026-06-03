# Multi-Source IoT Telemetry & ERP Integration Platform `[Work in Progress]`

Integrační demonstrační platforma postavená na frameworku **FastAPI**, zaměřená na IT/OT integrace a práci s datovými toky. Systém slouží jako asynchronní služba pro sběr telemetrických dat z IoT zařízení (vodoměrů) do relační databáze a zároveň umožňuje integraci s **Odoo ERP** prostřednictvím XML-RPC.

## Hlavní funkcionality

- **OT/IoT Telemetry Ingest (time-series data):** API pro příjem telemetrických dat s jednoduchou detekcí anomálií (výpadky signálu, neplatné hodnoty měření).
- **ERP integrace (Odoo):** Parsování CSV (kódování CP1250 z Excelu), mapování zákazníků a produktů a vytváření prodejních objednávek (*Sale Orders*).
- **Oddělení vrstev aplikace:** API vrstva je důsledně oddělená od business logiky (*Service Layer Pattern*).
- **Konfigurace a logování:** Nastavení přes environment variables (`.env`, *Pydantic Settings*), základní strukturované logování aplikace namísto běžných `print()` výpisů.
- **Dockerizace:** Celé prostředí (API, PostgreSQL, Odoo) je plně kontejnerizováno a běží v *Docker Compose*.

## Technologie

- **Backend:** Python 3.11, FastAPI, Pydantic v2
- **Databáze:** PostgreSQL 15, Psycopg2
- **Integrace ERP:** XML-RPC (Odoo API Client)
- **Infrastruktura:** Docker, Docker Compose

## Architektura

```text
[ OT Edge Simulator ] --> [ FastAPI API ]
                                │
                ┌───────────────┴───────────────┐
                ▼                               ▼
     [ PostgreSQL (telemetry) ]     [ Odoo ERP (orders) ]
