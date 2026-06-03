import xmlrpc.client

# --- SEM DOPLŇ SVOJE REÁLNÉ ÚDAJE Z ODOO ---
ODOO_URL = "http://localhost:8069"
ODOO_DB = "odoo_vodomery"
ODOO_USER = "admin"
ODOO_PASSWORD = "uno12xx"

print("Pokouším se připojit k Odoo...")

try:
    # 1. Navážeme kontakt s ověřovacím serverem Odoo
    common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
    
    # 2. Požádáme o ověření jména a hesla. Odoo nám vrátí unikátní ID uživatele (UID)
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
    
    if uid:
        print(f"-> Úspěch! Jsi přihlášen. Tvoje Odoo User ID je: {uid}")
        
        # 3. Pokud jsme přihlášeni, vytvoříme si spojení pro práci s daty (objekty)
        models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
        
        print("\nHledám v Odoo zákazníka jménem 'Jan Novák'...")
        
        # 4. Zavoláme Odoo a řekneme: "V modelu 'res.partner' (Kontakty) najdi řádek, kde name = 'Jan Novák'"
        partner_ids = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'res.partner', 'search',
            [[['name', '=', 'Jan Novák']]]
        )
        
        if partner_ids:
            print(f"-> Nalezen! Jan Novák má v Odoo vnitřní ID: {partner_ids[0]}")
            
            # 5. Pojďme si o něm vytáhnout detaily, abychom viděli, že čtení funguje
            partner_data = models.execute_kw(
                ODOO_DB, uid, ODOO_PASSWORD,
                'res.partner', 'read',
                [partner_ids],
                {'fields': ['name', 'email', 'phone']}
            )
            print(f"-> Data z Odoo karty zákazníka: {partner_data[0]}")
            
        else:
            print("-> Chyba: Jan Novák nebyl v Odoo nalezen. Zkontroluj, zda se v Odoo jmenuje přesně takto.")
            
    else:
        print("-> Chyba: Autentizace selhala. Zkontroluj název DB, e-mail nebo heslo.")

except Exception as e:
    print(f"\nNastala chyba při komunikaci s Odoo: {e}")