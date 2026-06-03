from fastapi import FastAPI, UploadFile, File, HTTPException
import csv
import codecs
import xmlrpc.client

app = FastAPI(title="Odoo Order Integration Bridge")

# Tvůj DB_CONFIG se přesunul sem do Ingest vrstvy
DB_CONFIG = {
    "dbname": "postgres",
    "user": "postgres",
    "password": "uno12xx",
    "host": "localhost",
    "port": 5432
}

def get_odoo_client():
    """Pomocná funkce pro přihlášení do Odoo."""
    common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
    if not uid:
        raise HTTPException(status_code=401, detail="Autentizace do Odoo selhala.")
    models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
    return uid, models

@app.post("/api/v1/import-order")
async def import_order_from_csv(file: UploadFile = File(...)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Soubor musí být ve formátu CSV.")

    try:
        csv_reader = csv.DictReader(codecs.iterdecode(file.file, 'cp1250'))
        rows = list(csv_reader)
        
        if not rows:
            raise HTTPException(status_code=400, detail="CSV soubor je prázdný.")

        ext_order_id = rows[0].get('objednavka_id')
        customer_name = rows[0].get('zakaznik')
        product_name = rows[0].get('produkt')
        quantity = float(rows[0].get('mnozstvi', 1))
        price_unit = float(rows[0].get('cena_za_kus', 0))

        uid, models = get_odoo_client()

        # Ověření zákazníka
        partner_ids = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD, 
            'res.partner', 'search', 
            [[['name', '=', customer_name]]]
        )
        if not partner_ids:
            raise HTTPException(status_code=404, detail=f"Zákazník '{customer_name}' nebyl v Odoo nalezen.")
        partner_id = partner_ids[0]

        # Ověření produktu
        product_ids = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD, 
            'product.product', 'search', 
            [[['name', '=', product_name]]]
        )
        if not product_ids:
            raise HTTPException(status_code=404, detail=f"Produkt '{product_name}' nebyl v Odoo nalezen.")
        product_id = product_ids[0]

        # Příprava položky
        order_line = (0, 0, {
            'product_id': product_id,
            'product_uom_qty': quantity,
            'price_unit': price_unit
        })

        # Sestavení objednávky
        order_data = {
            'partner_id': partner_id,
            'client_order_ref': ext_order_id,
            'order_line': [order_line]
        }

        # Vytvoření v Odoo
        odoo_order_id = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD, 
            'sale.order', 'create', 
            [order_data]
        )
        
        return {
            "status": "success",
            "message": "Objednávka úspěšně naimportována do Odoo.",
            "csv_order_id": ext_order_id,
            "odoo_order_id": odoo_order_id
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Interní chyba bridge: {str(e)}")