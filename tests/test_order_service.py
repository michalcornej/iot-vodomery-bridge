import pytest

from app.exceptions import ConflictError, NotFoundError, OdooUnavailableError
from app.services.order_service import OrderService

CSV = (
    "objednavka_id;zakaznik;produkt;mnozstvi;cena_za_kus\n"
    "OBJ-1;Firma A;Vodoměr;1;100\n"
    "OBJ-1;Firma A;Ventil;3;20\n"
    "OBJ-2;Firma B;Vodoměr;5;\n"
).encode("cp1250")


class FakeOdoo:
    def __init__(self, partners=None, products=None, existing_refs=None, fail_on_create=None):
        self.partners = partners or {"Firma A": 1, "Firma B": 2}
        self.products = products or {"Vodoměr": 10, "Ventil": 11}
        self.existing_refs = existing_refs or {}
        self.fail_on_create = fail_on_create
        self.created = []

    def find_sale_order_by_ref(self, ref):
        return self.existing_refs.get(ref)

    def find_partner_id_by_name(self, name):
        if name not in self.partners:
            raise NotFoundError(f"Zákazník '{name}' nebyl v Odoo nalezen.")
        return self.partners[name]

    def find_product_id_by_name(self, name):
        if name not in self.products:
            raise NotFoundError(f"Produkt '{name}' nebyl v Odoo nalezen.")
        return self.products[name]

    def create_sale_order(self, partner_id, client_ref, order_lines):
        if client_ref == self.fail_on_create:
            raise OdooUnavailableError("Odoo ERP služba je nedostupná.")
        self.created.append((partner_id, client_ref, order_lines))
        return 100 + len(self.created)


def test_imports_all_orders():
    odoo = FakeOdoo()
    result = OrderService(odoo).import_from_csv(CSV)
    assert result["orders"] == [
        {"csv_order_id": "OBJ-1", "odoo_order_id": 101, "lines": 2},
        {"csv_order_id": "OBJ-2", "odoo_order_id": 102, "lines": 1},
    ]
    assert odoo.created[0] == (
        1,
        "OBJ-1",
        [
            {"product_id": 10, "quantity": 1.0, "price_unit": 100.0},
            {"product_id": 11, "quantity": 3.0, "price_unit": 20.0},
        ],
    )
    assert odoo.created[1][2] == [{"product_id": 10, "quantity": 5.0, "price_unit": None}]


def test_unknown_product_creates_nothing():
    odoo = FakeOdoo(products={"Vodoměr": 10})
    with pytest.raises(NotFoundError, match="Ventil"):
        OrderService(odoo).import_from_csv(CSV)
    assert odoo.created == []


def test_duplicate_order_is_rejected():
    odoo = FakeOdoo(existing_refs={"OBJ-2": 55})
    with pytest.raises(ConflictError, match="OBJ-2"):
        OrderService(odoo).import_from_csv(CSV)
    assert odoo.created == []


def test_partial_failure_reports_created_orders():
    odoo = FakeOdoo(fail_on_create="OBJ-2")
    with pytest.raises(OdooUnavailableError, match=r"OBJ-1 \(ID 101\)"):
        OrderService(odoo).import_from_csv(CSV)
