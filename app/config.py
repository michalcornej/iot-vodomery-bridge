import os

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Zabezpečení API – klíč, který klienti posílají v hlavičce X-API-Key
    API_KEY: SecretStr

    # PostgreSQL
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "postgres"
    DB_USER: str = "postgres"
    DB_PASSWORD: SecretStr
    DB_POOL_MIN: int = Field(1, ge=1)
    DB_POOL_MAX: int = Field(10, ge=1)

    # Odoo
    ODOO_URL: str
    ODOO_DB: str
    ODOO_USER: str
    ODOO_PASSWORD: SecretStr  # heslo nebo (lépe) API klíč uživatele
    ODOO_TIMEOUT: float = Field(15.0, gt=0)

    # Detekce anomálií – maximální realistický průtok vodoměrem v m³/h
    MAX_FLOW_RATE_M3_PER_HOUR: float = Field(10.0, gt=0)

    # Import CSV – maximální velikost nahraného souboru v bajtech
    MAX_UPLOAD_BYTES: int = Field(5 * 1024 * 1024, gt=0)

    # Načtení .env souboru z kořene projektu
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Jeden globální konfigurační objekt
settings = Settings()
