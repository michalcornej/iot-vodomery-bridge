import os

# Konfigurace musí existovat dřív, než se importuje aplikace.
# Proměnné z prostředí (např. DB_* v CI) mají přednost.
for key, value in {
    "API_KEY": "test-key",
    "DB_PASSWORD": "test",
    "ODOO_URL": "http://odoo.invalid:8069",
    "ODOO_DB": "test",
    "ODOO_USER": "test",
    "ODOO_PASSWORD": "test",
}.items():
    os.environ.setdefault(key, value)
