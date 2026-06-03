import xmlrpc.client
import logging
from fastapi import HTTPException
from app.config import settings

logger = logging.getLogger(__name__)

class OdooClient:
    def __init__(self):
        self.url = settings.ODOO_URL
        self.db = settings.ODOO_DB
        self.user = settings.ODOO_USER
        self.password = settings.ODOO_PASSWORD
        self._uid = None
        self._models = None

    def _connect(self):
        """Interní metoda pro línou (lazy) autentizaci k Odoo."""
        if self._uid and self._models:
            return  # Už jsme připojeni

        try:
            logger.info("Připojování k Odoo ERP přes XML-RPC...")
            common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
            self._uid = common.authenticate(self.db, self.user, self.password, {})
            
            if not self._uid:
                logger.error("Autentizace do Odoo selhala (špatné přihlašovací údaje).")
                raise HTTPException(status_code=401, detail="Autentizace do Odoo selhala.")
            
            self._models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")
            logger.info(f"Úspěšně připojeno k Odoo. UID: {self._uid}")
        except Exception as e:
            logger.error(f"Kritická chyba při komunikaci s Odoo: {e}")
            raise HTTPException(status_code=502, detail="Odoo ERP služba je nedostupná.")

    def find_partner_id_by_name(self, name: str) -> int:
        """Najde ID zákazníka podle jména. Pokud neexistuje, vyhodí 404."""
        self._connect()
        partner_ids = self._models.execute_kw(
            self.db, self._uid, self.password,
            'res.partner', 'search',
            [[['name', '=', name]]]
        )
        if not partner_ids:
            raise HTTPException(status_code=404, detail=f"Zákazník '{name}' nebyl v Odoo nalezen.")
        return partner_ids[0]

    def find_product_id_by_name(self, name: str) -> int:
        """Najde ID produktu podle jména. Pokud neexistuje, vyhodí 404."""
        self._connect()
        product_ids = self._models.execute_kw(
            self.db, self._uid, self.password,
            'product.product', 'search',
            [[['name', '=', name]]]
        )
        if not product_ids:
            raise HTTPException(status_code=404, detail=f"Produkt '{name}' nebyl v Odoo nalezen.")
        return product_ids[0]

    def create_sale_order(self, partner_id: int, client_ref: str, order_lines: list) -> int:
        """Vytvoří prodejní objednávku v Odoo a vrátí její ID."""
        self._connect()
        
        # Transformace položek do Odoo formátu (0, 0, {data})
        formatted_lines = [
            (0, 0, {
                'product_id': line['product_id'],
                'product_uom_qty': line['quantity'],
                'price_unit': line['price_unit']
            }) for line in order_lines
        ]

        order_data = {
            'partner_id': partner_id,
            'client_order_ref': client_ref,
            'order_line': formatted_lines
        }

        odoo_order_id = self._models.execute_kw(
            self.db, self._uid, self.password,
            'sale.order', 'create',
            [order_data]
        )
        return odoo_order_id

# Inicializujeme jednu instanci klienta pro celou aplikaci (Singleton)
odoo_client = OdooClient()