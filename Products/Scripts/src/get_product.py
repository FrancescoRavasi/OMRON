import os
import json
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

def main():
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    AUTH_FILE = os.path.join(BASE_DIR, 'auth.json')
    
    product_code = input("Inserisci il codice prodotto da cercare (es. NX1021000): ").strip()
    if not product_code:
        print("Codice non valido.")
        return

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
                print("File auth.json non trovato. Effettua il login manualmente...")
                page.goto('https://industrial.omron.it/it/login')
                page.wait_for_url('https://industrial.omron.it/it/home', timeout=300000)
                context.storage_state(path=AUTH_FILE)
            
            # Navigazione dashboard per stabilire la sessione API
            page.goto('https://industrial.omron.it/it/dashboard/product-information')
            page.wait_for_load_state('networkidle')

            print(f"Ricerca del prodotto '{product_code}'...")
            url = f'https://industrial.omron.it/it/api/product_information/products?name={product_code}'
            response = page.request.get(url)
            
            if response.status != 200:
                print(f"Errore API search: status {response.status}")
                return
            
            data = response.json()
            products = data.get('data', [])
            
            if not products:
                print("Nessun prodotto trovato.")
                return
            
            print(f"\nTrovati {len(products)} risultati:")
            for idx, item in enumerate(products, 1):
                name = item.get('item_name') or item.get('oc_code')
                oc_code = item.get('oc_code')
                price = item.get('list_price') or item.get('net_price_eur') or 'Non disponibile'
                stock = item.get('stock_quantity')
                status = item.get('status_text')
                
                # Recupera la descrizione ricca dall'endpoint di dettaglio
                description = item.get('description') # fallback
                if oc_code:
                    detail_url = f'https://industrial.omron.it/it/api/product_information/products/{oc_code}'
                    try:
                        detail_resp = page.request.get(detail_url)
                        if detail_resp.status == 200:
                            detail_json = detail_resp.json()
                            prod_info = detail_json.get('data') if isinstance(detail_json, dict) and 'data' in detail_json else detail_json
                            if isinstance(prod_info, dict):
                                description = prod_info.get('description') or prod_info.get('long_description') or description
                    except Exception as det_err:
                        print(f"Avviso: impossibile recuperare i dettagli per {oc_code}: {det_err}")

                print(f"\n--- Risultato {idx} ---")
                print(f"Codice: {name}")
                print(f"OC Code: {oc_code}")
                print(f"Descrizione: {description}")
                print(f"Prezzo di Listino: {price}")
                print(f"Quantità in Stock: {stock}")
                print(f"Stato: {status}")

        except Exception as e:
            print(f"Errore durante l'esecuzione: {e}")
        finally:
            browser.close()

if __name__ == '__main__':
    main()
