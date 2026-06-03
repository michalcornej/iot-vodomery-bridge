import xmlrpc.client

# --- TVOJE ÚDAJE Z ODOO ---
ODOO_URL = "http://localhost:8069"
ODOO_DB = "odoo_vodomery"
ODOO_USER = "admin"
ODOO_PASSWORD = "uno12xx"

try:
    common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
    models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
    
    print("Přihlášeno do Odoo. Zjišťuji sériová čísla a jejich UMÍSTĚNÍ...")
    
    # 1. Nejprve vytáhneme sériová čísla
    lots = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'stock.lot', 'search_read',
        [[]],
        {'fields': ['id', 'name', 'product_id'], 'limit': 10}
    )
    
    if lots:
        print("\nVýpis z Odoo:")
        for lot in lots:
            lot_id = lot['id']
            lot_name = lot['name']
            product_name = lot['product_id'][1]
            
            # 2. PRO KAŽDÉ SN SE ZEPTÁME: "Kde v systému ležíš?" (hledáme v stock.quant)
            quants = models.execute_kw(
                ODOO_DB, uid, ODOO_PASSWORD,
                'stock.quant', 'search_read',
                [[['lot_id', '=', lot_id], ['quantity', '>', 0]]], # chceme jen tam, kde je fyzicky skladem
                {'fields': ['location_id', 'quantity']}
            )
            
            # Pokud Odoo najde záznam o poloze
            if quants:
                # location_id vrací [ID, "Název umístění/Cesta"]
                location_name = quants[0]['location_id'][1]
                qty = quants[0]['quantity']
                print(f"-> SN: {lot_name} | Produkt: {product_name} | Umístění: {location_name} ({int(qty)} ks)")
            else:
                print(f"-> SN: {lot_name} | Produkt: {product_name} | Umístění: NENALEZENO (Nikde není skladem)")
    else:
        print("\nŽádná sériová čísla nenalezena.")

except Exception as e:
    print(f"\nChyba: {e}")