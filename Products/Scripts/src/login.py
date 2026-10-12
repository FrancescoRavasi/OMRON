import os
import json
import string
import itertools
import time
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
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    DATA_DIR = os.path.join(BASE_DIR, 'data', 'products')
    AUTH_FILE = os.path.join(BASE_DIR, 'auth.json')
    
    os.makedirs(DATA_DIR, exist_ok=True)
    
    print("Scegli la modalità di scansione:")
    print("1. Tutte le combinazioni (1296 combinazioni)")
    print("2. Una singola combinazione di 2 caratteri")
    choice = input("Inserisci la tua scelta [1 o 2]: ").strip()

    if choice == '2':
        single_combo = input("Inserisci la combinazione di 2 caratteri da cercare (es. 'ef'): ").strip().lower()
        if len(single_combo) != 2:
            print("Errore: la combinazione deve essere esattamente di 2 caratteri.")
            return
        combinations = [single_combo]
    else:
        chars = string.ascii_lowercase + string.digits
        combinations = [''.join(p) for p in itertools.product(chars, repeat=2)]
        
    total_combinations = len(combinations)
    
    seen_ids = set()
    all_products = []
    completed_combos = set()
    
    LISTA_FILE = None
    RIEPILOGO_FILE = None
    
    # Cerca un file di riepilogo esistente per riprendere la sessione
    existing_summaries = [f for f in os.listdir(DATA_DIR) if f.startswith('riepilogo_') and f.endswith('.txt')]
    if len(combinations) == 1:
        c = combinations[0]
        existing_summaries = [f for f in existing_summaries if f.startswith(f'riepilogo_{c}_')]
    existing_summaries.sort()
    
    if existing_summaries:
        latest_summary = existing_summaries[-1]
        RIEPILOGO_FILE = os.path.join(DATA_DIR, latest_summary)
        if len(combinations) == 1:
            prefix = f'riepilogo_{combinations[0]}_'
            timestamp_part = latest_summary[len(prefix):].replace('.txt', '')
            LISTA_FILE = os.path.join(DATA_DIR, f'lista_{combinations[0]}_{timestamp_part}.json')
        else:
            timestamp_part = latest_summary.replace('riepilogo_', '').replace('.txt', '')
            LISTA_FILE = os.path.join(DATA_DIR, f'lista_{timestamp_part}.json')
        
        print(f"Trovato file di riepilogo esistente: {RIEPILOGO_FILE}. Ripresa della sessione in corso...")
        
        # Leggi le combinazioni già completate
        if os.path.exists(RIEPILOGO_FILE):
            with open(RIEPILOGO_FILE, 'r', encoding='utf-8') as rf:
                for line in rf:
                    parts = line.split(':')
                    if parts:
                        combo_key = parts[0].strip()
                        if len(combo_key) == 2:
                            completed_combos.add(combo_key)
                            
        # Carica i prodotti esistenti dal file JSON corrispondente
        if os.path.exists(LISTA_FILE):
            try:
                with open(LISTA_FILE, 'r', encoding='utf-8') as f:
                    data_json = json.load(f)
                    all_products = data_json.get('data', [])
                    for item in all_products:
                        uid = item.get('id') or item.get('oc_code')
                        if uid:
                            seen_ids.add(uid)
                print(f"Caricati {len(all_products)} prodotti unici esistenti da {LISTA_FILE}.")
            except Exception as e:
                print(f"Impossibile leggere {LISTA_FILE}: {e}")
                
    if not RIEPILOGO_FILE:
        start_time_str = datetime.now().strftime("%Y%m%d_%H%M")
        if len(combinations) == 1:
            c = combinations[0]
            LISTA_FILE = os.path.join(DATA_DIR, f'lista_{c}_{start_time_str}.json')
            RIEPILOGO_FILE = os.path.join(DATA_DIR, f'riepilogo_{c}_{start_time_str}.txt')
        else:
            LISTA_FILE = os.path.join(DATA_DIR, f'lista_{start_time_str}.json')
            RIEPILOGO_FILE = os.path.join(DATA_DIR, f'riepilogo_{start_time_str}.txt')
        print(f"Avvio nuova ricerca. File di output: {LISTA_FILE} e {RIEPILOGO_FILE}")
        
    print(f"Totale combinazioni da scansionare: {total_combinations} (Già completate: {len(completed_combos)})")
    
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
                if combo in completed_combos:
                    continue
                
                remaining_combos = total_combinations - len(completed_combos) - 1
                print(f"\n[Progresso] Combinazione {index}/{total_combinations} (Rimanenti: {remaining_combos}) -> Cercando '{combo}'...")
                
                url = f'https://industrial.omron.it/it/api/product_information/products?name={combo}'
                
                success = False
                response = None
                
                # Retry logic: fino a 5 tentativi consecutivi con attesa di 10 secondi in caso di errore/blocco
                for attempt in range(1, 6):
                    try:
                        response = page.request.get(url)
                        if response.status == 200:
                            success = True
                            break
                        else:
                            print(f"Tentativo {attempt}/5: API Error {response.status} per '{combo}'. Attendendo 10 secondi...")
                    except Exception as req_err:
                        print(f"Tentativo {attempt}/5: Errore di rete ({req_err}) per '{combo}'. Attendendo 10 secondi...")
                    
                    if attempt < 5:
                        time.sleep(10)
                
                if not success:
                    print(f"Errore critico: impossibile completare la richiesta per '{combo}' dopo 5 tentativi consecutivi. Interruzione script.")
                    with open(RIEPILOGO_FILE, 'a', encoding='utf-8') as rf:
                        rf.write(f"{combo}: ERRORE CRITICO DOPO 5 TENTATIVI\n")
                    break
                
                if response and response.status == 200:
                    product_data = response.json()
                    product_list = product_data.get('data', [])
                    found_count = len(product_list)
                    
                    new_count = 0
                    for item in product_list:
                        status = str(item.get('status_text') or item.get('statusText') or '').strip()
                        if status.lower() not in ['stocked', 'non-stocked']:
                            continue
                        
                        item_id = item.get('id')
                        desc_text = None
                        
                        # Recupera i dettagli completi del singolo prodotto dall'endpoint di dettaglio per ottenere la descrizione corretta
                        if item_id:
                            detail_url = f'https://industrial.omron.it/it/api/product_information/products/{item_id}'
                            try:
                                detail_resp = page.request.get(detail_url)
                                if detail_resp.status == 200:
                                    detail_data = detail_resp.json()
                                    
                                    # Salva un file di debug per il primo prodotto trovato per ispezionare tutti i campi
                                    debug_path = os.path.join(DATA_DIR, 'debug_product.json')
                                    if not os.path.exists(debug_path):
                                        with open(debug_path, 'w', encoding='utf-8') as df:
                                            json.dump(detail_data, df, ensure_ascii=False, indent=4)
                                        print(f"[DEBUG] Salvato file di esempio in {debug_path}")
                                        
                                    prod_info = detail_data.get('data') if isinstance(detail_data, dict) and 'data' in detail_data else detail_data
                                    if isinstance(prod_info, dict):
                                        item.update(prod_info)
                                        
                                        # Cerca in vari campi possibili la descrizione dettagliata
                                        for key in ['long_description', 'subtitle', 'summary', 'description', 'text', 'features', 'product_description']:
                                            val = prod_info.get(key)
                                            if isinstance(val, dict):
                                                desc_text = val.get('text') or val.get('value')
                                                if desc_text:
                                                    break
                                            elif isinstance(val, str) and val.strip() and val != prod_info.get('oc_code'):
                                                desc_text = val
                                                break
                            except Exception as e:
                                print(f"[DEBUG] Errore recupero dettaglio: {e}")
                        
                        if not desc_text:
                            desc = item.get('description')
                            if isinstance(desc, dict):
                                desc_text = desc.get('text')
                            elif isinstance(desc, str):
                                desc_text = desc
                        
                        if desc_text:
                            item['text'] = desc_text
                            item['description_text'] = desc_text
                        
                        uid = item.get('id') or item.get('oc_code')
                        if uid and uid not in seen_ids:
                            seen_ids.add(uid)
                            all_products.append(item)
                            new_count += 1
                    
                    print(f"Trovati {found_count} risultati per '{combo}' (Nuovi aggiunti: {new_count}, Totale unici accumulati: {len(all_products)})")
                    
                    # Aggiorna il file di riepilogo con timestamp
                    with open(RIEPILOGO_FILE, 'a', encoding='utf-8') as rf:
                        rf.write(f"{combo}: {found_count} risultati (nuovi unici: {new_count})\n")
                    
                    completed_combos.add(combo)

                    # Aggiorna lista con timestamp man mano solo se ci sono nuovi prodotti
                    if new_count > 0:
                        with open(LISTA_FILE, 'w', encoding='utf-8') as f:
                            json.dump({"data": all_products}, f, ensure_ascii=False, indent=4)
                        print(f"File {LISTA_FILE} e {RIEPILOGO_FILE} aggiornati.")
                    else:
                        print(f"File {RIEPILOGO_FILE} aggiornato (nessun nuovo prodotto per '{combo}', salto scrittura lista).")
                
                # Ritardo di 1 secondo tra un'iterazione e l'altra
                time.sleep(1.0)
            
            print(f"\nProcesso completato! Totale prodotti unici salvati in {LISTA_FILE}: {len(all_products)}")
            print(f"Riepilogo per combinazione salvato in {RIEPILOGO_FILE}")

        except Exception as e:
            print(f'Error: {e}')
        finally:
            browser.close()

if __name__ == "__main__":
    login()
