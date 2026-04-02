# 🌿 PlanTrack

> L'aiutante digitale per far sopravvivere le tue piante di casa 🤞

PlanTrack è una web app costruita con **Streamlit** che ti permette di tenere traccia delle annaffiature delle tue piante. Registra ogni pianta, monitora quando è stata annaffiata l'ultima volta, scopri quali sono in ritardo e pianifica le prossime annaffiature con un calendario visivo.

---

## ✨ Funzionalità

### 🏠 Dashboard
Panoramica di tutte le piante in un colpo d'occhio, organizzata a griglia.
- Badge colorati per lo stato di ogni pianta (**In ritardo** / **Oggi** / **In programma** / **Mai annaffiata**)
- Filtri rapidi per **stanza** e **stato**
- Numero di colonne configurabile (2, 3 o 4)
- Contatore rapido in sidebar: piante totali e da annaffiare urgentemente

### ➕ Aggiungi Pianta
Form per registrare una nuova pianta con:
- Nome, stanza, frequenza di annaffiatura (giorni), note libere
- Anteprima della card subito dopo la registrazione

### 💧 Registra Annaffiatura
- Annaffia una singola pianta con **un click**, con le più urgenti mostrate per prime
- Seleziona **più piante contemporaneamente** e registrale in un colpo solo
- Specifica opzionalmente una **data e ora personalizzata** (utile se hai dimenticato di registrare)
- **Storico annaffiature** espandibile per ogni pianta, con possibilità di eliminare singole voci

### 📅 Calendario
Tre viste per pianificare le annaffiature future:

| Tab | Descrizione |
|-----|-------------|
| 📊 **Timeline** | Grafico Gantt con le future annaffiature, slider da 7 a 60 giorni, linea "oggi" evidenziata |
| 🗓 **Heatmap** | Mappa a colori dei prossimi 30 giorni: vedi a colpo d'occhio i giorni più intensi |
| 📋 **Tabella** | Riepilogo ordinato con colorazione condizionale dello stato |

### ✏️ Gestisci Piante
- **Modifica** nome, stanza, frequenza e note di una pianta esistente
- **Elimina** definitivamente una pianta (con doppia conferma per evitare errori)

---

## 🗂 Struttura del progetto

```
PlanTrack/
├── app.py                  # Entry point – interfaccia Streamlit
├── requirements.txt        # Dipendenze Python
├── data/
│   └── plants.json         # Persistenza dati (JSON locale)
└── utils/
    ├── data_manager.py     # CRUD piante e log annaffiature
    └── calendar_utils.py   # Generazione grafici Plotly (Gantt, heatmap, tabella)
```

---

## 🚀 Avvio rapido

### 1. Clona la repo
```bash
git clone https://github.com/tuo-utente/plantrack.git
cd plantrack
```

### 2. Crea un ambiente virtuale e installa le dipendenze
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Avvia l'app
```bash
streamlit run app.py
```

L'app si apre automaticamente nel browser su `http://localhost:8501`.

---

## 🛠 Stack tecnologico

| Libreria | Utilizzo |
|----------|----------|
| [Streamlit](https://streamlit.io) | Framework per l'interfaccia web |
| [Plotly](https://plotly.com/python/) | Grafici interattivi (Gantt, heatmap) |
| [pandas](https://pandas.pydata.org) | Gestione tabelle e DataFrame |
| JSON (stdlib) | Persistenza dati locale, senza database |

---

## 📌 Note

- I dati vengono salvati localmente in `data/plants.json`. Non è richiesto nessun database esterno.
- L'app è pensata per uso personale/locale. Per un deploy pubblico si consiglia di aggiungere autenticazione.
