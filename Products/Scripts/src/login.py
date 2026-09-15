import os
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

# Helper to update log container
def update_ui_log(page, message):
    print(message)  # Still log to console for debugging
    page.evaluate("""(msg) => {
        const log = document.getElementById('automation-log');
        if (log) {
            const entry = document.createElement('div');
            entry.innerText = `> ${msg}`;
            log.appendChild(entry);
        }
    }""", message)

def login():
    # Input dinamico con validazione
    while True:
        PRODUCT_CODE = input("Inserisci il codice prodotto da cercare (almeno 2 caratteri): ").strip()
        if len(PRODUCT_CODE) >= 2:
            break
        print("Errore: il codice deve avere almeno 2 caratteri.")
    
    AUTH_FILE = 'auth.json'
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            channel='chrome',
            headless=False
        )
        
        # Se esiste il file di autenticazione, caricalo, altrimenti crea un contesto vuoto
        if os.path.exists(AUTH_FILE):
            print("Caricamento sessione esistente...")
            context = browser.new_context(storage_state=AUTH_FILE)
        else:
            print("Nessuna sessione trovata. Eseguire il login manuale...")
            context = browser.new_context()

        page = context.new_page()

        try:
            # Se non eravamo loggati, vai alla pagina di login
            if not os.path.exists(AUTH_FILE):
                page.goto('https://industrial.omron.it/it/login')
                # Metti in pausa per permettere il login manuale
                print("Effettua il login manualmente nel browser...")
                page.wait_for_url('https://industrial.omron.it/it/home', timeout=300000)
                # Salva lo stato dopo il login
                context.storage_state(path=AUTH_FILE)
                print("Login effettuato e sessione salvata.")
            
            # Naviga alla pagina dashboard
            page.goto('https://industrial.omron.it/it/dashboard/product-information')
            page.wait_for_load_state('networkidle')
            
            # Perform API call
            search_term = PRODUCT_CODE.lower()
            url = f'https://industrial.omron.it/it/api/product_information/products?name={search_term}'
            response = page.request.get(url)
            
            if response.status == 200:
                product_data = response.json()
                product_list = product_data.get('data', [])

                if isinstance(product_list, list) and len(product_list) > 0:
                    print(f'API Data retrieved. Found {len(product_list)} results.')
                    
                    # Salvataggio dati in data/products
                    import json
                    os.makedirs('data/products', exist_ok=True)
                    file_path = f'data/products/{PRODUCT_CODE}.json'
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(product_data, f, ensure_ascii=False, indent=4)
                    print(f'Data saved to {file_path}')
                else:
                    print('No products found. Skipping file save.')
            else:
                print(f'API Error: {response.status}')
            
            print('Process completed.')

        except Exception as e:
            print(f'Error: {e}')
        finally:
            # Chiudi il browser dopo l'operazione
            browser.close()

if __name__ == "__main__":
    login()
