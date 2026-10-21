# Multi-Source IoT Telemetry & ERP Integration Platform `[Work in Progress]`

Integrační demonstrační platforma postavená na **FastAPI**, zaměřená na IT/OT integrace a práci s datovými toky. Sbírá telemetrii z IoT vodoměrů do PostgreSQL (včetně detekce anomálií) a importuje prodejní objednávky z CSV do **Odoo ERP** přes XML-RPC.

## Hlavní funkcionality

- **OT/IoT Telemetry Ingest:** příjem měření z vodoměrů s validací vstupu a detekcí anomálií (výpadek hodnoty, pokles kumulativního stavu, nereálný průtok). Každé měření se uloží a anomálie se v DB označí.
- **ERP integrace (Odoo):** import CSV z Excelu (CP1250 i UTF-8, oddělovač `;` i `,`, desetinná čárka), více objednávek i položek v jednom souboru, ověření zákazníků a produktů v Odoo a ochrana proti duplicitnímu importu.
- **Oddělení vrstev:** endpointy jen validují vstup, logika je ve službách, které o HTTP nic nevědí. Doménové výjimky převádí na HTTP odpovědi jeden exception handler.
- **Zabezpečení:** endpointy vyžadují API klíč v hlavičce `X-API-Key`.
- **Konfigurace a logování:** nastavení přes proměnné prostředí / `.env` (*Pydantic Settings*), strukturované logování.
- **Docker Compose:** API, PostgreSQL, Odoo a volitelně simulátor.

## Technologie

- **Backend:** Python 3.11, FastAPI, Pydantic v2
- **Databáze:** PostgreSQL 15, psycopg2 (pool spojení)
- **Integrace ERP:** Odoo XML-RPC
- **Infrastruktura:** Docker, Docker Compose, GitHub Actions (ruff + pytest)

## Architektura

```text
[ IoT simulátor / vodoměry ] ──X-API-Key──▶ [ FastAPI bridge ] ◀──X-API-Key── [ CSV import ]
                                                   │
                                   ┌───────────────┴───────────────┐
                                   ▼                               ▼
                       [ PostgreSQL (telemetrie) ]       [ Odoo ERP (objednávky) ]
```

Podrobnosti v [docs/architecture.md](docs/architecture.md).

## Spuštění

### Docker Compose (doporučeno)

```bash
cp .env.example .env          # vyplňte hesla a API_KEY
docker compose up -d --build
```

- API a dokumentace: http://localhost:8000/docs
- Odoo: http://localhost:8069. Při prvním spuštění vytvořte databázi s názvem z `ODOO_DB`, nainstalujte modul **Sales** a pro bridge založte uživatele s API klíčem (Preferences → Account Security → New API Key). Jeho login dejte do `ODOO_USER`, klíč do `ODOO_PASSWORD` a pak spusťte `docker compose restart api`.
- Simulátor tří vodoměrů: `docker compose --profile sim up -d`

Schéma telemetrie (`db/init.sql`) se v Compose založí automaticky při prvním startu databáze.

### Lokálně (bez Dockeru)

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
cp .env.example .env                                   # vyplňte připojení k PostgreSQL a Odoo
psql -h localhost -U <uživatel> -d <databáze> -f db/init.sql
uvicorn app.main:app --reload
```

Simulátor: `API_KEY=<klíč> python simulator/simulator.py` (další volby: `API_URL`, `METER_IDS`, `INTERVAL`).

`db/init.sql` je idempotentní, takže ho jde spustit i nad existující tabulkou `meter_readings` ze starší verze. Doplní nové sloupce.

## Konfigurace

| Proměnná | Povinná | Popis |
|---|---|---|
| `API_KEY` | ano | klíč, který klienti posílají v hlavičce `X-API-Key` |
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` | ne | připojení k PostgreSQL (výchozí `localhost:5432/postgres`, `postgres`) |
| `DB_PASSWORD` | ano | heslo k PostgreSQL |
| `ODOO_URL`, `ODOO_DB`, `ODOO_USER` | ano | připojení k Odoo |
| `ODOO_PASSWORD` | ano | heslo, nebo lépe API klíč uživatele Odoo |
| `ODOO_DB_PASSWORD` | jen Compose | heslo DB uživatele pro kontejner Odoo |
| `ODOO_TIMEOUT` | ne | timeout volání Odoo v sekundách (výchozí 15) |
| `MAX_FLOW_RATE_M3_PER_HOUR` | ne | práh pro detekci nereálného průtoku (výchozí 10 m³/h) |
| `MAX_UPLOAD_BYTES` | ne | limit velikosti CSV (výchozí 5 MB) |
| `DB_POOL_MIN`, `DB_POOL_MAX` | ne | velikost poolu spojení (výchozí 1–10) |

## API

### `POST /api/v1/telemetry`

```bash
curl -X POST http://localhost:8000/api/v1/telemetry \
  -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d '{"meter_id": "vodomer111", "timestamp": "2026-01-01T12:00:00+00:00",
       "cumulative_consumption": 12.3456, "battery_level": 95, "signal_strength": -80}'
```

Odpověď `201`: `{"status": "saved", "id": 1, "anomaly": null}`. Pole `anomaly` obsahuje jednu z hodnot:

| Kód | Význam |
|---|---|
| `missing_value` | `cumulative_consumption` je `null` (výpadek senzoru) |
| `consumption_decrease` | stav je nižší než poslední platné měření |
| `consumption_spike` | průtok od posledního platného měření je vyšší než `MAX_FLOW_RATE_M3_PER_HOUR` |

Porovnává se vždy s posledním **platným** měřením téhož vodoměru (bez anomálie) před daným časem. První měření vodoměru se nemá s čím porovnat a neoznačí se. Po výměně vodoměru (reset stavu na 0) je proto potřeba použít nové `meter_id`.

### `POST /api/v1/import-order`

```bash
curl -X POST http://localhost:8000/api/v1/import-order \
  -H "X-API-Key: $API_KEY" -F "file=@objednavky.csv"
```

Formát CSV (hlavička je povinná, na pořadí sloupců nezáleží):

```text
objednavka_id;zakaznik;produkt;mnozstvi;cena_za_kus
OBJ-1001;Vodárny Žďár;Vodoměr DN20;2;1 250,50
OBJ-1001;Vodárny Žďár;Kulový ventil;4;
OBJ-1002;Město Kolín;Vodoměr DN20;10;1 190
```

- Řádky se stejným `objednavka_id` tvoří jednu objednávku s více položkami.
- `cena_za_kus` je nepovinná. Když je prázdná, použije se cena z ceníku Odoo.
- Celý soubor se nejdřív ověří (formát, existence zákazníků a produktů, duplicity přes `client_order_ref`) a teprve pak se objednávky zakládají.
- Chybové kódy: `400` neplatné CSV, `404` zákazník nebo produkt v Odoo neexistuje, `409` objednávka už existuje nebo jméno není jednoznačné, `413` příliš velký soubor, `502` chyba Odoo.

## Vývoj

```bash
ruff check . && ruff format --check .
pytest                                    # jednotkové testy (bez DB a Odoo)
TEST_DB=1 pytest tests/test_telemetry_db.py   # integrační test, potřebuje PostgreSQL se schématem
```

CI (GitHub Actions) spouští lint i všechny testy včetně integračního proti PostgreSQL.
