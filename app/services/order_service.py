import csv
import codecs
import logging
from fastapi import UploadFile, HTTPException
from app.services.odoo_service import odoo_client

logger = logging.getLogger(__name__)

class OrderService:
    @staticmethod
    def import_from_csv(file: UploadFile) -> dict:
        """Zpracuje nahraný CSV soubor a provede orchestraci importu do Odoo ERP."""
        
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Soubor musí být ve formátu CSV.")

        try:
            # Dekódování streamu souboru z Windows-1250 (Český Excel)
            csv_reader = csv.DictReader(codecs.iterdecode(file.file, 'cp1250'))
            rows = list(csv_reader)
            
            if not rows:
                raise HTTPException(status_code=400, detail="CSV soubor je prázdný.")

            # Vezmeme data z prvního řádku (předpokládáme zjednodušenou single-order strukturu)
            row = rows[0]
            ext_order_id = row.get('objednavka_id')
            customer_name = row.get('zakaznik')
            product_name = row.get('produkt')
            
            try:
                quantity = float(row.get('mnozstvi', 1))
                price_unit = float(row.get('cena_za_kus', 0))
            except ValueError:
                raise HTTPException(status_code=400, detail="Chyba validace dat v CSV: Množství nebo cena nejsou čísla.")

            logger.info(f"Spouštím import objednávky {ext_order_id} pro zákazníka {customer_name} do Odoo...")

            # 1. Krok: Ověření a získání ID partnera z Odoo
            partner_id = odoo_client.find_partner_id_by_name(customer_name)
            
            # 2. Krok: Ověření a získání ID produktu z Odoo
            product_id = odoo_client.find_product_id_by_name(product_name)

            # 3. Krok: Sestavení položek objednávky
            order_lines = [{
                'product_id': product_id,
                'quantity': quantity,
                'price_unit': price_unit
            }]

            # 4. Krok: Vytvoření objednávky v ERP systému
            odoo_order_id = odoo_client.create_sale_order(
                partner_id=partner_id,
                client_ref=ext_order_id,
                order_lines=order_lines
            )

            logger.info(f"🎉 Objednávka úspěšně naimportována do Odoo. ID v Odoo: {odoo_order_id}")

            return {
                "status": "success",
                "message": "Objednávka úspěšně naimportována do Odoo.",
                "csv_order_id": ext_order_id,
                "odoo_order_id": odoo_order_id
            }

        except HTTPException as he:
            # Propustíme FastAPI HTTP výjimky ven (404 apod.)
            raise he
        except Exception as e:
            logger.error(f"Neočekávaná chyba při zpracování CSV importu: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Interní chyba bridge při zpracování CSV: {str(e)}")