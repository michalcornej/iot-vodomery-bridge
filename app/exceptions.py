"""Doménové výjimky aplikace.

Služby vyhazují tyto výjimky a nevědí nic o HTTP. Převod na HTTP odpověď
zajišťuje exception handler v app/main.py podle atributu `status_code`.
"""


class BridgeError(Exception):
    status_code = 500

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class InvalidInputError(BridgeError):
    """Vstupní data (např. CSV soubor) nejsou platná."""

    status_code = 400


class NotFoundError(BridgeError):
    """Hledaná entita (zákazník, produkt) v Odoo neexistuje."""

    status_code = 404


class ConflictError(BridgeError):
    """Nejednoznačná shoda nebo duplicitní záznam."""

    status_code = 409


class PayloadTooLargeError(BridgeError):
    status_code = 413


class OdooAuthError(BridgeError):
    """Bridge se nedokázal přihlásit do Odoo (chybné ODOO_USER / ODOO_PASSWORD).

    Jde o chybu konfigurace na straně serveru, ne o chybu volajícího klienta,
    proto 502 – ale s jinou zprávou než nedostupnost Odoo.
    """

    status_code = 502


class OdooUnavailableError(BridgeError):
    """Odoo neodpovídá nebo vrátilo chybu."""

    status_code = 502


class StorageError(BridgeError):
    """Selhal zápis do databáze."""

    status_code = 503
