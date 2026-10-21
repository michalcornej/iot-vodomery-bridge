import xmlrpc.client
from unittest import mock

import pytest

from app.exceptions import ConflictError, NotFoundError, OdooAuthError, OdooUnavailableError
from app.services.odoo_service import OdooClient


def make_client():
    return OdooClient(url="http://odoo.invalid:8069", db="db", user="u", password="p", timeout=1)


def patch_proxy(client, common=None, obj=None):
    def proxy(endpoint):
        return {"common": common, "object": obj}[endpoint]

    return mock.patch.object(client, "_proxy", side_effect=proxy)


def test_wrong_credentials_raise_auth_error_not_unavailable():
    client = make_client()
    common = mock.Mock()
    common.authenticate.return_value = False
    with patch_proxy(client, common=common), pytest.raises(OdooAuthError):
        client.find_partner_id_by_name("A")


def test_connection_refused_raises_unavailable():
    client = make_client()
    common = mock.Mock()
    common.authenticate.side_effect = ConnectionRefusedError()
    with patch_proxy(client, common=common), pytest.raises(OdooUnavailableError):
        client.find_partner_id_by_name("A")


def test_fault_raises_unavailable():
    client = make_client()
    common, obj = mock.Mock(), mock.Mock()
    common.authenticate.return_value = 2
    obj.execute_kw.side_effect = xmlrpc.client.Fault(1, "boom")
    with patch_proxy(client, common, obj), pytest.raises(OdooUnavailableError):
        client.find_partner_id_by_name("A")


@pytest.mark.parametrize("ids, exc", [([], NotFoundError), ([1, 2], ConflictError)])
def test_partner_lookup_must_be_unique(ids, exc):
    client = make_client()
    common, obj = mock.Mock(), mock.Mock()
    common.authenticate.return_value = 2
    obj.execute_kw.return_value = ids
    with patch_proxy(client, common, obj), pytest.raises(exc):
        client.find_partner_id_by_name("A")


def test_create_sale_order_omits_missing_price():
    client = make_client()
    common, obj = mock.Mock(), mock.Mock()
    common.authenticate.return_value = 2
    obj.execute_kw.return_value = 42
    lines = [{"product_id": 10, "quantity": 1, "price_unit": None}, {"product_id": 11, "quantity": 2, "price_unit": 5}]
    with patch_proxy(client, common, obj):
        assert client.create_sale_order(1, "OBJ-1", lines) == 42
    args = obj.execute_kw.call_args.args
    assert args[3:5] == ("sale.order", "create")
    assert args[5][0]["order_line"] == [
        (0, 0, {"product_id": 10, "product_uom_qty": 1}),
        (0, 0, {"product_id": 11, "product_uom_qty": 2, "price_unit": 5}),
    ]
