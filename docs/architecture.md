# Architektura Integrační Platformy

Systém funguje jako vícezdrojový integrační bridge, který propojuje IoT/OT zařízení s ERP systémem Odoo a s lokálním úložištěm časových řad (PostgreSQL).

## Tok dat a komponenty

1. **Simulační vrstva (`simulator/`)**
   - Generuje telemetrii pro jeden nebo více vodoměrů (ID zařízení, čas, kumulativní spotřeba, baterie, signál).
   - Náhodně simuluje anomálie (skok hodnoty, chybějící hodnota), aby šla otestovat jejich detekce na straně API.

2. **API vrstva (`app/main.py`)**
   - Endpointy validují vstup Pydantic schématy, ověřují API klíč (`X-API-Key`) a předávají práci službám.
   - Endpointy jsou synchronní (`def`). psycopg2 i XML-RPC blokují, proto je FastAPI spouští ve vláknovém poolu a neblokují event loop.
   - Doménové výjimky (`app/exceptions.py`) převádí na HTTP odpovědi jeden exception handler. Služby tak nejsou svázané s FastAPI.

3. **Aplikační služby (`app/services/`)**
   - `TelemetryService` porovná měření s posledním platným měřením vodoměru (`detect_anomaly`) a uloží ho s příznakem `is_anomaly` / `anomaly_reason`.
   - `OrderService` rozparsuje CSV, seskupí řádky do objednávek, ověří všechny entity v Odoo a teprve potom objednávky založí.
   - `OdooClient` zapouzdřuje XML-RPC: línou autentizaci, timeouty, převod chyb na doménové výjimky a vyhledávání vyžadující jednoznačnou shodu. Pro každé volání vytváří nový `ServerProxy`, protože ten není thread-safe.

4. **Datová a ERP vrstva**
   - **PostgreSQL** (`db/init.sql`): tabulka `meter_readings` s indexem `(meter_id, timestamp DESC)` pro rychlé dohledání předchozího měření. Přístup jde přes pool spojení (`app/database.py`).
   - **Odoo ERP (XML-RPC):** modely `res.partner`, `product.product` a `sale.order`. Externí ID objednávky se ukládá do `client_order_ref` a slouží k ochraně proti duplicitnímu importu.

## Známá omezení

- Ochrana proti duplicitám není atomická: dva souběžné importy téhož souboru mohou projít kontrolou současně.
- Když Odoo selže uprostřed zakládání objednávek, již vytvořené objednávky zůstanou. Chybová zpráva je vyjmenuje.
- První měření nového vodoměru se nemá s čím porovnat, takže se na skok nekontroluje.
