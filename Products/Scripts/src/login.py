import os
import json
import string
import itertools
import time
from datetime import datetime
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

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
    
    print("Scegli la modalità di ricerca/scansione:")
    print("1. Tutte le combinazioni di 2 caratteri (1296 combinazioni)")
    print("2. Una singola combinazione o codice specifico")
    choice = input("Inserisci la tua scelta [1 o 2]: ").strip()

    if choice == '2':
        single_query = input("Inserisci il codice o combinazione da cercare: ").strip()
        if not single_query:
            print("Errore: nessun valore inserito.")
            return
        combinations = [single_query]
    else:
        chars = string.ascii_lowercase + string.digits
        combinations = [''.join(p) for p in itertools.product(chars, repeat=2)]
        combinations.reverse()
        
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
        
        if os.path.exists(RIEPILOGO_FILE):
            with open(RIEPILOGO_FILE, 'r', encoding='utf-8') as rf:
                for line in rf:
                    parts = line.split(':')
                    if parts:
                        combo_key = parts[0].strip()
                        completed_combos.add(combo_key)
                            
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
        
    print(f"Totale elementi/combinazioni da scansionare: {total_combinations} (Già completate: {len(completed_combos)})")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            channel='chrome',
            headless=False
        )
        
        if os.path.exists(AUTH_FILE):
            context = browser.new_context(storage_state=AUTH_FILE)
        else:
            context = browser.new_context()

        page = context.new_page()

        try:
            if not os.path.exists(AUTH_FILE):
                page.goto('https://industrial.omron.it/it/login')
                print("Effettua il login manualmente nel browser...")
                page.wait_for_url('https://industrial.omron.it/it/home', timeout=300000)
                context.storage_state(path=AUTH_FILE)
            
            page.goto('https://industrial.omron.it/it/dashboard/product-information')
            page.wait_for_load_state('networkidle')
            setup_ui_log(page)
            
            for index, combo in enumerate(combinations, start=1):
                if combo in completed_combos:
                    continue
                
                print(f"\n[Progresso] Ricerca {index}/{total_combinations} -> '{combo}'...")
                
                url = f'https://industrial.omron.it/it/api/product_information/products?name={combo}'
                
                success = False
                response = None
                
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
                    print(f"Errore di connessione persistente per '{combo}'. Attendo 20 secondi e salto alla combinazione successiva...")
                    with open(RIEPILOGO_FILE, 'a', encoding='utf-8') as rf:
                        rf.write(f"{combo}: ERRORE CONNESSIONE (SALTATO)\n")
                    time.sleep(20)
                    continue
                
                if response and response.status == 200:
                    product_data = response.json()
                    product_list = product_data.get('data', [])
                    found_count = len(product_list)
                    
                    new_count = 0
                    for item in product_list:
                        status_text = str(item.get('status_text') or item.get('statusText') or item.get('status') or '').strip()
                        if 'discontinued' in status_text.lower():
                            continue
                        
                        oc_code = item.get('oc_code') or item.get('name')
                        if not oc_code:
                            continue
                        
                        # Esegue il secondo endpoint per recuperare tutte le informazioni del singolo oc_code
                        detail_url = f'https://industrial.omron.it/it/api/product_information/products/{oc_code}'
                        try:
                            time.sleep(0.8)
                            detail_resp = page.request.get(detail_url, timeout=8000)
                            if detail_resp.status == 200:
                                detail_json = detail_resp.json()
                                prod_info = detail_json.get('data') if isinstance(detail_json, dict) and 'data' in detail_json else detail_json
                                
                                if isinstance(prod_info, dict):
                                    uid = prod_info.get('id') or prod_info.get('oc_code') or oc_code
                                    if uid and uid not in seen_ids:
                                        seen_ids.add(uid)
                                        all_products.append(prod_info)
                                        new_count += 1
                                else:
                                    if oc_code not in seen_ids:
                                        seen_ids.add(oc_code)
                                        all_products.append(item)
                                        new_count += 1
                        except Exception as e:
                            if oc_code not in seen_ids:
                                seen_ids.add(oc_code)
                                all_products.append(item)
                                new_count += 1
                    
                    print(f"Trovati {found_count} risultati per '{combo}' (Nuovi dettagli validi aggiunti: {new_count}, Totale accumulati: {len(all_products)})")
                    
                    with open(RIEPILOGO_FILE, 'a', encoding='utf-8') as rf:
                        rf.write(f"{combo}: {found_count} risultati (nuovi dettagli validi: {new_count})\n")
                    
                    completed_combos.add(combo)

                    if new_count > 0 or found_count > 0:
                        with open(LISTA_FILE, 'w', encoding='utf-8') as f:
                            json.dump({"data": all_products}, f, ensure_ascii=False, indent=4)
                        print(f"File {LISTA_FILE} aggiornato.")
                
                time.sleep(1.5)
            
            print(f"\nProcesso completato! Totale prodotti unici salvati in {LISTA_FILE}: {len(all_products)}")

        except Exception as e:
            print(f'Error: {e}')
        finally:
            browser.close()

if __name__ == "__main__":
    login()
