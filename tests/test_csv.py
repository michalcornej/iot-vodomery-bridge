import pytest

from app.exceptions import InvalidInputError
from app.services.order_service import parse_orders_csv


def test_czech_excel_cp1250_semicolon_decimal_comma():
    content = (
        "objednavka_id;zakaznik;produkt;mnozstvi;cena_za_kus\r\nOBJ-1;Vodárny Žďár;Vodoměr DN20;2;1 250,50\r\n"
    ).encode("cp1250")
    [order] = parse_orders_csv(content)
    assert order.ext_order_id == "OBJ-1"
    assert order.customer_name == "Vodárny Žďár"
    [line] = order.lines
    assert line.product_name == "Vodoměr DN20"
    assert line.quantity == 2
    assert line.price_unit == 1250.5


def test_utf8_bom_comma_delimited():
    content = "﻿objednavka_id,zakaznik,produkt,mnozstvi,cena_za_kus\nOBJ-1,Žluťoučký kůň,Ventil,1,10.5\n".encode()
    [order] = parse_orders_csv(content)
    assert order.customer_name == "Žluťoučký kůň"
    assert order.lines[0].price_unit == 10.5


def test_multiple_rows_and_orders_are_grouped():
    content = (
        "objednavka_id;zakaznik;produkt;mnozstvi;cena_za_kus\n"
        "OBJ-1;Firma A;Vodoměr;1;100\n"
        "OBJ-1;Firma A;Ventil;3;20\n"
        ";;;;\n"
        "OBJ-2;Firma B;Vodoměr;5;\n"
    ).encode("cp1250")
    orders = parse_orders_csv(content)
    assert [o.ext_order_id for o in orders] == ["OBJ-1", "OBJ-2"]
    assert [line.product_name for line in orders[0].lines] == ["Vodoměr", "Ventil"]
    assert orders[1].lines[0].price_unit is None  # prázdná cena = cena z ceníku Odoo


def test_header_is_case_and_whitespace_insensitive():
    content = b"Objednavka_ID ; Zakaznik ; Produkt ; Mnozstvi\nOBJ-1;A;B;1\n"
    assert parse_orders_csv(content)[0].customer_name == "A"


@pytest.mark.parametrize(
    "content, message",
    [
        (b"", "prázdný"),
        (b"objednavka_id;zakaznik;produkt;mnozstvi\n", "žádné objednávky"),
        (b"objednavka_id;zakaznik;produkt\nOBJ-1;A;B\n", "mnozstvi"),
        (b"objednavka_id;zakaznik;produkt;mnozstvi\nOBJ-1;A;B;abc\n", "Řádek 2"),
        (b"objednavka_id;zakaznik;produkt;mnozstvi\nOBJ-1;A;B;0\n", "kladné"),
        (b"objednavka_id;zakaznik;produkt;mnozstvi\nOBJ-1;;B;1\n", "zakaznik"),
        (b"objednavka_id;zakaznik;produkt;mnozstvi\nOBJ-1;A;B;1\nOBJ-1;C;B;1\n", "různé zákazníky"),
    ],
)
def test_invalid_csv(content, message):
    with pytest.raises(InvalidInputError, match=message):
        parse_orders_csv(content)
