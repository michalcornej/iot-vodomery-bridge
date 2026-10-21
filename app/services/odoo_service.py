import http.client
import logging
import threading
import xmlrpc.client

from app.config import settings
from app.exceptions import ConflictError, NotFoundError, OdooAuthError, OdooUnavailableError

logger = logging.getLogger(__name__)


class _TimeoutTransport(xmlrpc.client.Transport):
    def __init__(self, timeout: float):
        super().__init__()
        self._timeout = timeout

    def make_connection(self, host):
        conn = super().make_connection(host)
        conn.timeout = self._timeout
        return conn


class _TimeoutSafeTransport(xmlrpc.client.SafeTransport):
    def __init__(self, timeout: float):
        super().__init__()
        self._timeout = timeout

    def make_connection(self, host):
        conn = super().make_connection(host)
        conn.timeout = self._timeout
        return conn


class OdooClient:
    """Klient pro Odoo XML-RPC API.

    `ServerProxy` není thread-safe, proto se pro každé volání vytváří nový
    (je to levné). Sdílí se jen UID získané při přihlášení.
    """

    def __init__(self, url: str, db: str, user: str, password: str, timeout: float):
        self.url = url.rstrip("/")
        self.db = db
        self.user = user
        self._password = password
        self._timeout = timeout
        self._uid: int | None = None
        self._lock = threading.Lock()

    def _proxy(self, endpoint: str) -> xmlrpc.client.ServerProxy:
        if self.url.startswith("https://"):
            transport = _TimeoutSafeTransport(self._timeout)
        else:
            transport = _TimeoutTransport(self._timeout)
        return xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/{endpoint}", transport=transport, allow_none=True)

    def _authenticate(self) -> int:
        """Líná autentizace – při prvním volání získá a uloží UID."""
        with self._lock:
            if self._uid:
                return self._uid
            logger.info("Připojování k Odoo ERP přes XML-RPC (%s)...", self.url)
            try:
                uid = self._proxy("common").authenticate(self.db, self.user, self._password, {})
            except (OSError, http.client.HTTPException, xmlrpc.client.Error) as e:
                logger.error("Odoo je nedostupné: %s", e)
                raise OdooUnavailableError("Odoo ERP služba je nedostupná.") from e
            if not uid:
                logger.error("Autentizace do Odoo selhala – zkontrolujte ODOO_USER / ODOO_PASSWORD.")
                raise OdooAuthError("Bridge se nedokázal přihlásit do Odoo (chybná konfigurace přihlašovacích údajů).")
            self._uid = uid
            logger.info("Úspěšně připojeno k Odoo. UID: %s", uid)
            return uid

    def _execute(self, model: str, method: str, *args, **kwargs):
        uid = self._authenticate()
        try:
            return self._proxy("object").execute_kw(self.db, uid, self._password, model, method, list(args), kwargs)
        except xmlrpc.client.Fault as e:
            logger.error("Odoo vrátilo chybu při %s.%s: %s", model, method, e.faultString)
            raise OdooUnavailableError(f"Odoo odmítlo požadavek ({model}.{method}).") from e
        except (OSError, http.client.HTTPException, xmlrpc.client.Error) as e:
            logger.error("Chyba komunikace s Odoo při %s.%s: %s", model, method, e)
            raise OdooUnavailableError("Odoo ERP služba je nedostupná.") from e

    def _find_unique_id(self, model: str, name: str, label: str) -> int:
        ids = self._execute(model, "search", [["name", "=", name]], limit=2)
        if not ids:
            raise NotFoundError(f"{label} '{name}' nebyl v Odoo nalezen.")
        if len(ids) > 1:
            raise ConflictError(f"{label} '{name}' není v Odoo jednoznačný (existuje více záznamů se stejným jménem).")
        return ids[0]

    def find_partner_id_by_name(self, name: str) -> int:
        return self._find_unique_id("res.partner", name, "Zákazník")

    def find_product_id_by_name(self, name: str) -> int:
        return self._find_unique_id("product.product", name, "Produkt")

    def find_sale_order_by_ref(self, client_ref: str) -> int | None:
        """Vrátí ID existující objednávky se stejnou externí referencí (kvůli idempotenci)."""
        ids = self._execute("sale.order", "search", [["client_order_ref", "=", client_ref]], limit=1)
        return ids[0] if ids else None

    def create_sale_order(self, partner_id: int, client_ref: str, order_lines: list[dict]) -> int:
        """Vytvoří prodejní objednávku v Odoo a vrátí její ID.

        Položka bez `price_unit` převezme cenu z ceníku v Odoo.
        """
        formatted_lines = []
        for line in order_lines:
            values = {"product_id": line["product_id"], "product_uom_qty": line["quantity"]}
            if line.get("price_unit") is not None:
                values["price_unit"] = line["price_unit"]
            formatted_lines.append((0, 0, values))

        return self._execute(
            "sale.order",
            "create",
            {"partner_id": partner_id, "client_order_ref": client_ref, "order_line": formatted_lines},
        )


# Jedna instance klienta pro celou aplikaci
odoo_client = OdooClient(
    url=settings.ODOO_URL,
    db=settings.ODOO_DB,
    user=settings.ODOO_USER,
    password=settings.ODOO_PASSWORD.get_secret_value(),
    timeout=settings.ODOO_TIMEOUT,
)
