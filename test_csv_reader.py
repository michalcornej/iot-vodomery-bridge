import csv
import os

CSV_FILE = "objednavka.csv"

print("--- Spouštím lokální test čtení CSV ---")

# 1. Nejprve zkontrolujeme, zda soubor vůbec fyzicky existuje
if not os.path.exists(CSV_FILE):
    print(f"Chyba: Soubor '{CSV_FILE}' nebyl v této složce nalezen!")
    print("Ujisti se, že jsi ho vytvořil a uložil.")
else:
    print(f"Soubor '{CSV_FILE}' nalezen. Pokouším se ho otevřít...")
    
    try:
        # 2. Otevřeme soubor s kódováním utf-8 (aby nám správně fungovala čeština, např. u jména Jan Novák)
        with open(CSV_FILE, mode='r', encoding='cp1250') as f:
            
            # 3. Použijeme DictReader, který automaticky vezme první řádek jako názvy sloupců
            csv_reader = csv.DictReader(f)
            
            print("\nÚspěšně načteno. Vypisuji řádky z CSV:\n")
            
            pocet_radku = 0
            for row in csv_reader:
                pocet_radku += 1
                print(f"--- Řádek č. {pocet_radku} ---")
                print(f"  * ID Objednávky:  {row.get('objednavka_id')}")
                print(f"  * Zákazník:       {row.get('zakaznik')}")
                print(f"  * Produkt:        {row.get('produkt')}")
                print(f"  * Množství:       {row.get('mnozstvi')} ks")
                print(f"  * Cena za kus:    {row.get('cena_za_kus')} Kč")
                print("-" * 20)
                
            print(f"\nTest dokončen. Celkem zpracováno řádků: {pocet_radku}")

    except Exception as e:
        print(f"\nNastala chyba při čtení CSV souboru: {e}")