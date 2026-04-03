# Configurazione Google Sheets per PlanTrack

Questa guida ti spiega come collegare PlanTrack a Google Sheets come database persistente.

---

## 1. Crea un progetto Google Cloud

1. Vai su [console.cloud.google.com](https://console.cloud.google.com)
2. Crea un nuovo progetto (es. `plantrack`)
3. Dal menu laterale vai su **API e servizi → Libreria**
4. Abilita **Google Sheets API**
5. Abilita **Google Drive API**

---

## 2. Crea un Service Account

1. Vai su **API e servizi → Credenziali**
2. Clicca **Crea credenziali → Account di servizio**
3. Dai un nome (es. `plantrack-bot`) e clicca **Crea e continua**
4. Salta i passaggi opzionali e clicca **Fine**
5. Clicca sul Service Account appena creato
6. Vai su **Chiavi → Aggiungi chiave → Crea nuova chiave → JSON**
7. Scarica il file `.json` — **tienilo al sicuro, non committarlo mai su Git!**

---

## 3. Crea il Google Sheet

1. Vai su [sheets.google.com](https://sheets.google.com) e crea un nuovo foglio
2. Chiamalo come vuoi (es. `PlanTrack Data`)
3. Copia l'**ID dello Spreadsheet** dall'URL:
   ```
   https://docs.google.com/spreadsheets/d/QUESTO_È_L_ID/edit
   ```
4. Condividi il foglio con l'email del Service Account (es. `plantrack-bot@...gserviceaccount.com`) come **Editor**

> L'app creerà automaticamente i fogli `plants` e `watering_log` al primo avvio.

---

## 4. Configura i Secrets

### In locale

Crea il file `.streamlit/secrets.toml` (è già in `.gitignore`):

```toml
SPREADSHEET_ID = "incolla-qui-l-id-dello-spreadsheet"

[gcp_service_account]
type = "service_account"
project_id = "nome-del-tuo-progetto"
private_key_id = "abc123..."
private_key = "-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----\n"
client_email = "plantrack-bot@nome-progetto.iam.gserviceaccount.com"
client_id = "123456789"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/plantrack-bot%40nome-progetto.iam.gserviceaccount.com"
```

Copia tutti i valori dal file JSON scaricato al passo 2.

> ⚠️ Attenzione al campo `private_key`: nel JSON le andate a capo sono `\n`, che devono rimanere `\n` nel TOML (non andate a capo reali).

### Su Streamlit Cloud

1. Vai su [share.streamlit.io](https://share.streamlit.io) → la tua app → **Settings → Secrets**
2. Incolla il contenuto del file `secrets.toml` nel campo di testo
3. Clicca **Save**

---

## 5. Avvia l'app

```bash
streamlit run app.py
```

Al primo avvio l'app creerà automaticamente i fogli `plants` e `watering_log` nel tuo Google Sheet.
