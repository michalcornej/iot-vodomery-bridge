import csv
import io
import logging
from dataclasses import dataclass, field

from app.exceptions import BridgeError, ConflictError, InvalidInputError, OdooUnavailableError
from app.services.odoo_service import OdooClient, odoo_client

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = ("objednavka_id", "zakaznik", "produkt", "mnozstvi")
OPTIONAL_COLUMNS = ("cena_za_kus",)


@dataclass
class OrderLine:
    row: int
    product_name: str
    quantity: float
    price_unit: float | None


@dataclass
class ParsedOrder:
    ext_order_id: str
    customer_name: str
    lines: list[OrderLine] = field(default_factory=list)


def _decode(content: bytes) -> str:
    """Excel ukládá CSV podle nastavení buď v UTF-8 (s BOM), nebo v CP1250."""
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return content.decode("cp1250")


def _detect_dialect(text: str):
    sample = text[:4096]
    try:
        return csv.Sniffer().sniff(sample, delimiters=";,\t")
    except csv.Error:
        # Český Excel používá jako oddělovač středník
        delimiter = ";" if sample.count(";") >= sample.count(",") else ","
        return type("ExcelDialect", (csv.excel,), {"delimiter": delimiter})


def _parse_number(raw: str | None, column: str, row: int) -> float | None:
    """Přijme desetinnou čárku i tečku a mezery jako oddělovač tisíců."""
    value = (raw or "").strip().replace(" ", "").replace(" ", "").replace(",", ".")
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        raise InvalidInputError(f"Řádek {row}: hodnota '{raw}' ve sloupci '{column}' není číslo.") from None


def parse_orders_csv(content: bytes) -> list[ParsedOrder]:
    """Rozparsuje CSV a seskupí řádky podle `objednavka_id` do objednávek."""
    text = _decode(content)
    if not text.strip():
        raise InvalidInputError("CSV soubor je prázdný.")

    reader = csv.DictReader(io.StringIO(text), dialect=_detect_dialect(text))
    if reader.fieldnames is None:
        raise InvalidInputError("CSV soubor je prázdný.")
    reader.fieldnames = [(name or "").strip().lower() for name in reader.fieldnames]

    missing = [col for col in REQUIRED_COLUMNS if col not in reader.fieldnames]
    if missing:
        raise InvalidInputError(f"V CSV chybí povinné sloupce: {', '.join(missing)}.")

    orders: dict[str, ParsedOrder] = {}
    # Řádek 1 je hlavička, data začínají na řádku 2
    for row_no, row in enumerate(reader, start=2):
        values = {key: (value or "").strip() for key, value in row.items() if key}
        if not any(values.values()):
            continue  # prázdný řádek

        for col in ("objednavka_id", "zakaznik", "produkt"):
            if not values.get(col):
                raise InvalidInputError(f"Řádek {row_no}: chybí hodnota ve sloupci '{col}'.")

        quantity = _parse_number(values.get("mnozstvi"), "mnozstvi", row_no)
        if quantity is None or quantity <= 0:
            raise InvalidInputError(f"Řádek {row_no}: množství musí být kladné číslo.")
        price_unit = _parse_number(values.get("cena_za_kus"), "cena_za_kus", row_no)
        if price_unit is not None and price_unit < 0:
            raise InvalidInputError(f"Řádek {row_no}: cena nesmí být záporná.")

        ext_id = values["objednavka_id"]
        order = orders.setdefault(ext_id, ParsedOrder(ext_order_id=ext_id, customer_name=values["zakaznik"]))
        if order.customer_name != values["zakaznik"]:
            raise InvalidInputError(
                f"Řádek {row_no}: objednávka '{ext_id}' má na různých řádcích různé zákazníky "
                f"('{order.customer_name}' a '{values['zakaznik']}')."
            )
        order.lines.append(OrderLine(row_no, values["produkt"], quantity, price_unit))

    if not orders:
        raise InvalidInputError("CSV soubor neobsahuje žádné objednávky.")
    return list(orders.values())


class OrderService:
    def __init__(self, odoo: OdooClient):
        self.odoo = odoo

    def import_from_csv(self, content: bytes) -> dict:
        """Import objednávek z CSV do Odoo.

        Nejdřív se ověří celý soubor (formát, existence zákazníků a produktů,
        duplicity) a teprve pak se objednávky zakládají. Chyba v datech tak
        nezpůsobí, že se naimportuje jen část souboru.
        """
        orders = parse_orders_csv(content)
        logger.info("CSV obsahuje %d objednávek, ověřuji data v Odoo...", len(orders))

        partner_cache: dict[str, int] = {}
        product_cache: dict[str, int] = {}
        prepared = []
        for order in orders:
            existing_id = self.odoo.find_sale_order_by_ref(order.ext_order_id)
            if existing_id:
                raise ConflictError(
                    f"Objednávka '{order.ext_order_id}' už v Odoo existuje (ID {existing_id}). Import byl zastaven."
                )
            if order.customer_name not in partner_cache:
                partner_cache[order.customer_name] = self.odoo.find_partner_id_by_name(order.customer_name)
            lines = []
            for line in order.lines:
                if line.product_name not in product_cache:
                    product_cache[line.product_name] = self.odoo.find_product_id_by_name(line.product_name)
                lines.append(
                    {
                        "product_id": product_cache[line.product_name],
                        "quantity": line.quantity,
                        "price_unit": line.price_unit,
                    }
                )
            prepared.append((order, partner_cache[order.customer_name], lines))

        created = []
        for order, partner_id, lines in prepared:
            try:
                odoo_order_id = self.odoo.create_sale_order(
                    partner_id=partner_id, client_ref=order.ext_order_id, order_lines=lines
                )
            except BridgeError as e:
                done = ", ".join(f"{c['csv_order_id']} (ID {c['odoo_order_id']})" for c in created) or "žádné"
                logger.error("Import přerušen u objednávky %s. Již vytvořené: %s", order.ext_order_id, done)
                raise OdooUnavailableError(
                    f"Vytvoření objednávky '{order.ext_order_id}' selhalo: {e.message} "
                    f"Již vytvořené objednávky: {done}."
                ) from e
            logger.info("Objednávka %s naimportována do Odoo, ID %s", order.ext_order_id, odoo_order_id)
            created.append({"csv_order_id": order.ext_order_id, "odoo_order_id": odoo_order_id, "lines": len(lines)})

        return {
            "status": "success",
            "message": f"Naimportováno objednávek: {len(created)}.",
            "orders": created,
        }


order_service = OrderService(odoo_client)
