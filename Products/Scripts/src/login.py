import os
import json
import string
import itertools
from datetime import datetime
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

# Helper to inject log container
def setup_ui_log(page):
    page.evaluate("""() => {
        if (document.getElementById('automation-log')) return;
        const div = document.createElement('div');
        div.id = 'automation-log';
        div.style.position = 'fixed';
        div.style.top = '10px';
        div.style.right = '10px';
        div.style.backgroundColor = 'rgba(0, 0, 0, 0.8)';
        div.style.color = '#fff';
        div.style.padding = '10px';
        div.style.zIndex = '999999';
        div.style.borderRadius = '5px';
        div.style.fontSize = '12px';
        div.style.maxWidth = '300px';
        div.innerHTML = '<strong>Automation Log:</strong>';
        document.body.appendChild(div);
    }""")

def login():
    AUTH_FILE = 'auth.json'
    
    # Genera il timestamp di inizio (anno, mese, giorno, ora, minuto)
    start_time_str = datetime.now().strftime("%Y%m%d_%H%M")
    
    LISTA_FILE = f'data/products/lista_{start_time_str}.json'
    RIEPILOGO_FILE = f'data/products/riepilogo_{start_time_str}.txt'
    
    print(f"Avvio ricerca. File di output: {LISTA_FILE} e {RIEPILOGO_FILE}")
    
    # Genera tutte le combinazioni alfanumeriche di 2 caratteri (es. aa, ab, ..., 99)
    chars = string.ascii_lowercase + string.digits
    combinations = [''.join(p) for p in itertools.product(chars, repeat=2)]
    total_combinations = len(combinations)
    
    print(f"Totale combinazioni da scansionare: {total_combinations}")
    
    seen_ids = set()
    all_products = []
    
    os.makedirs('data/products', exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            channel='chrome',
            headless=False
        )
        
        if os.path.exists(AUTH_FILE):
            print("Caricamento sessione esistente...")
            context = browser.new_context(storage_state=AUTH_FILE)
        else:
            print("Nessuna sessione trovata. Eseguire il login manuale...")
            context = browser.new_context()

        page = context.new_page()

        try:
            if not os.path.exists(AUTH_FILE):
                page.goto('https://industrial.omron.it/it/login')
                print("Effettua il login manualmente nel browser...")
                page.wait_for_url('https://industrial.omron.it/it/home', timeout=300000)
                context.storage_state(path=AUTH_FILE)
                print("Login effettuato e sessione salvata.")
            
            # Naviga alla pagina dashboard una volta
            page.goto('https://industrial.omron.it/it/dashboard/product-information')
            page.wait_for_load_state('networkidle')
            setup_ui_log(page)
            
            for index, combo in enumerate(combinations, start=1):
                remaining_combos = total_combinations - index
                print(f"\n[Progresso] Combinazione {index}/{total_combinations} ({remaining_combos} rimanenti) -> Cercando '{combo}'...")
                
                url = f'https://industrial.omron.it/it/api/product_information/products?name={combo}'
                response = page.request.get(url)
                
                if response.status == 200:
                    product_data = response.json()
                    product_list = product_data.get('data', [])
                    found_count = len(product_list)
                    
                    new_count = 0
                    for item in product_list:
                        uid = item.get('id') or item.get('oc_code')
                        if uid and uid not in seen_ids:
                            seen_ids.add(uid)
                            all_products.append(item)
                            new_count += 1
                    
                    print(f"Trovati {found_count} risultati per '{combo}' (Nuovi aggiunti: {new_count}, Totale unici accumulati: {len(all_products)})")
                    
                    # Aggiorna il file di riepilogo con timestamp
                    with open(RIEPILOGO_FILE, 'a', encoding='utf-8') as rf:
                        rf.write(f"{combo}: {found_count} risultati (nuovi unici: {new_count})\n")

                    # Aggiorna lista con timestamp man mano solo se ci sono nuovi prodotti
                    if new_count > 0:
                        with open(LISTA_FILE, 'w', encoding='utf-8') as f:
                            json.dump({"data": all_products}, f, ensure_ascii=False, indent=4)
                        print(f"File {LISTA_FILE} e {RIEPILOGO_FILE} aggiornati.")
                    else:
                        print(f"File {RIEPILOGO_FILE} aggiornato (nessun nuovo prodotto per '{combo}', salto scrittura lista).")
                else:
                    print(f"API Error {response.status} per la combinazione '{combo}'")
                    with open(RIEPILOGO_FILE, 'a', encoding='utf-8') as rf:
                        rf.write(f"{combo}: ERRORE API {response.status}\n")
            
            print(f"\nProcesso completato! Totale prodotti unici salvati in {LISTA_FILE}: {len(all_products)}")
            print(f"Riepilogo per combinazione salvato in {RIEPILOGO_FILE}")

        except Exception as e:
            print(f'Error: {e}')
        finally:
            browser.close()

if __name__ == "__main__":
    login()
