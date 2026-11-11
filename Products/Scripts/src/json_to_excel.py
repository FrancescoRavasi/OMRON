import os
import glob
import json
import pandas as pd

def main():
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    DATA_DIR = os.path.join(BASE_DIR, 'data', 'products')
    
    # Trova il file JSON più recente
    json_files = glob.glob(os.path.join(DATA_DIR, 'lista_*.json'))
    if not json_files:
        print("Nessun file JSON trovato nella cartella data/products/")
        return
        
    json_files.sort(key=os.path.getmtime, reverse=True)
    latest_json = json_files[0]
    
    print(f"Lettura del file JSON: {latest_json}")
    
    with open(latest_json, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    products = data.get('data', [])
    if not products:
        print("Il file JSON non contiene prodotti.")
        return
        
    df = pd.DataFrame(products)
    
    # Definisci il nome del file Excel di output
    timestamp_str = os.path.basename(latest_json).replace('lista_', '').replace('.json', '')
    excel_filename = os.path.join(DATA_DIR, f'prodotti_omron_{timestamp_str}.xlsx')
    
    print(f"Generazione del file Excel in corso: {excel_filename}")
    df.to_excel(excel_filename, index=False, engine='openpyxl')
    
    print(f"Conversione completata con successo! File salvato in: {excel_filename}")

if __name__ == '__main__':
    main()
