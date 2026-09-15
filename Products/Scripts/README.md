# OMRON Product Data Automation

Questo progetto contiene uno script Python che automatizza il recupero di informazioni sui prodotti dal portale OMRON, sfruttando le API interne dopo aver gestito l'autenticazione.

## Requisiti

*   Python 3.x
*   Google Chrome installato
*   Dipendenze Python (Playwright, python-dotenv)

## Installazione

1.  Clona o scarica il progetto.
2.  Installa le dipendenze:
    ```bash
    pip install playwright python-dotenv
    ```
3.  Installa i driver del browser necessari per Playwright:
    ```bash
    python -m playwright install chromium
    ```

## Configurazione

Assicurati di avere un file `.env` nella directory principale con le tue credenziali OMRON:

```env
OMRON_USERNAME=tua_email@esempio.com
OMRON_PASSWORD=tua_password
```

## Utilizzo

Esegui lo script principale:

```bash
python src/login.py
```

### Autenticazione Persistente (storageState)

Lo script utilizza un sistema di sessione persistente (`auth.json`) per evitare di dover ripetere il login ad ogni esecuzione:

1.  **Prima esecuzione:** Lo script non troverà il file `auth.json`. Aprirà Chrome e ti chiederà di effettuare il **login manualmente**. Una volta effettuato l'accesso e raggiunta la homepage, lo script salverà automaticamente i cookie in `auth.json`.
2.  **Esecuzioni successive:** Lo script caricherà `auth.json` e procederà direttamente alla ricerca del prodotto senza richiedere ulteriori interazioni.

Se hai bisogno di rifare il login (ad esempio se la sessione scade), basta eliminare il file `auth.json` e rieseguire lo script.

## Funzionalità

*   Login automatizzato (tramite sessione persistente).
*   Input dinamico del codice prodotto via terminale.
*   Ricerca prodotto tramite API Omron.
*   Salvataggio dei dati ricevuti (JSON) nella cartella `data/products/`.
