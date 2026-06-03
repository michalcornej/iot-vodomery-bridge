# Multi-Source IoT Telemetry & ERP Integration Platform [WIP]

Podniková integrační platforma (vzorová architektura) postavená na frameworku **FastAPI**, která řeší reálné business scénáře v oblasti IT/OT integrací. Systém slouží jako asynchronní datová pumpa pro sběr telemetrických dat z průmyslových IoT zařízení (vodoměrů) do relační databáze a zároveň jako orchestrátor pro import obchodních dat do **Odoo ERP** pomocí XML-RPC protokolu.

## Hlavní Funkcionality & Ukázka Engineeringu

- **OT/IoT Telemetry Ingest (Time-Series):** Vysoce propustný endpoint pro příjem telemetrických dat s integrovanou vrstvou pro detekci anomálií (výpadky signálu, neplatné ústřely měření).
- **ERP Orchestrace (Odoo Integration):** Automatizované parsování legacy formátů (CSV s kódováním CP1250 z českého Excelu), validace entit (zákazník, produkt) uvnitř ERP systému a atomické zakládání prodejních objednávek (*Sale Orders*).
- **Clean Architecture:** Striktní oddělení vrstev. Tenké API routery, tlustá servisní vrstva (`Service Pattern`) a centralizovaný stav. Žádná duplikace připojení.
- **Enterprise-Ready Configuration & Logging:** Kompletní správa tajných klíčů a parametrů infrastruktury přes proměnné prostředí (`.env`, `Pydantic Settings`). Implementováno strukturované logování aplikace namísto `print()` výpisů.
- **Kompletní Infrastruktura v Dockeru:** Celé prostředí (API, PostgreSQL databáze, Odoo ERP) je plně kontejnerizováno a orchestrováno pomocí Docker Compose.

## Technologický Stack

- **Backend:** Python 3.11, FastAPI, Pydantic v2
- **Databáze:** PostgreSQL 15, Psycopg2 (Context Managers)
- **ERP Integrace:** XML-RPC (Odoo API Client)
- **Infrastruktura:** Docker, Docker Compose
- **Validace & Typování:** Typové anotace, Pydantic schémata

## Architektura Systému

```text
[ OT Edge Simulator ] --( HTTP POST / JSON )--> [ FastAPI Backend ]
                                                       │
                                        ┌──────────────┴──────────────┐
                                        ▼                             ▼
                            [ PostgreSQL Database ]         [ Odoo ERP (XML-RPC) ]
                            (Měření / Time-Series)          (Partneři / Objednávky)
