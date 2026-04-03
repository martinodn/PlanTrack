"""
data_manager.py – Gestione persistente dei dati delle piante via Google Sheets.

Struttura dello Spreadsheet (due fogli):
  - plants       : id | name | room | watering_frequency_days | notes | image_url | house | created_at
  - watering_log : id | plant_id | watered_at

Le credenziali vengono lette da st.secrets["gcp_service_account"].
L'ID dello Spreadsheet viene letto da st.secrets["SPREADSHEET_ID"].
"""

import uuid
from datetime import datetime, timedelta

import gspread
import streamlit as st
from google.oauth2.service_account import Credentials

# ──────────────────────────────────────────────
# Costanti
# ──────────────────────────────────────────────

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

PLANTS_SHEET = "plants"
WATERING_SHEET = "watering_log"

PLANTS_HEADERS = [
    "id", "name", "room", "watering_frequency_days",
    "notes", "image_url", "house", "created_at",
]
WATERING_HEADERS = ["id", "plant_id", "watered_at"]


# ──────────────────────────────────────────────
# Connessione (singleton via cache_resource)
# ──────────────────────────────────────────────

@st.cache_resource
def _get_spreadsheet() -> gspread.Spreadsheet:
    """Crea e restituisce il client gspread (singleton)."""
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES,
    )
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(st.secrets["SPREADSHEET_ID"])
    _ensure_sheets(spreadsheet)
    return spreadsheet


def _ensure_sheets(spreadsheet: gspread.Spreadsheet) -> None:
    """Crea i fogli con intestazioni se non esistono già."""
    existing = {ws.title for ws in spreadsheet.worksheets()}

    if PLANTS_SHEET not in existing:
        ws = spreadsheet.add_worksheet(PLANTS_SHEET, rows=1000, cols=len(PLANTS_HEADERS))
        ws.append_row(PLANTS_HEADERS)

    if WATERING_SHEET not in existing:
        ws = spreadsheet.add_worksheet(WATERING_SHEET, rows=5000, cols=len(WATERING_HEADERS))
        ws.append_row(WATERING_HEADERS)


# ──────────────────────────────────────────────
# Lettura dati (con cache breve)
# ──────────────────────────────────────────────

@st.cache_data(ttl=30)
def _read_plants_rows() -> list[dict]:
    """Legge tutti i record dal foglio plants."""
    ws = _get_spreadsheet().worksheet(PLANTS_SHEET)
    return ws.get_all_records()


@st.cache_data(ttl=30)
def _read_watering_rows() -> list[dict]:
    """Legge tutti i record dal foglio watering_log."""
    ws = _get_spreadsheet().worksheet(WATERING_SHEET)
    return ws.get_all_records()


def _invalidate_cache() -> None:
    """Invalida la cache dei dati dopo ogni scrittura."""
    _read_plants_rows.clear()
    _read_watering_rows.clear()


# ──────────────────────────────────────────────
# Costruzione oggetto pianta arricchito
# ──────────────────────────────────────────────

def _build_plant(row: dict, watering_rows: list[dict]) -> dict:
    """Assembla un dict pianta con watering_log annidato."""
    plant_id = row["id"]
    log = sorted(
        r["watered_at"]
        for r in watering_rows
        if r["plant_id"] == plant_id and r["watered_at"]
    )
    return {
        "id": plant_id,
        "name": row.get("name", ""),
        "room": row.get("room", ""),
        "watering_frequency_days": int(row.get("watering_frequency_days", 7)),
        "notes": row.get("notes", ""),
        "image_url": row.get("image_url", ""),
        "house": row.get("house") or "Vali",
        "created_at": row.get("created_at", ""),
        "watering_log": log,
    }


# ──────────────────────────────────────────────
# API pubblica – CRUD piante
# ──────────────────────────────────────────────

def get_all_plants() -> list[dict]:
    """Restituisce la lista di tutte le piante con il loro watering_log."""
    plant_rows = _read_plants_rows()
    watering_rows = _read_watering_rows()
    return [_build_plant(r, watering_rows) for r in plant_rows]


def get_plant_by_id(plant_id: str) -> dict | None:
    """Restituisce una singola pianta per ID, o None se non trovata."""
    return next((p for p in get_all_plants() if p["id"] == plant_id), None)


def add_plant(
    name: str,
    room: str,
    watering_frequency_days: int,
    notes: str = "",
    image_url: str = "",
    house: str = "Vali",
) -> dict:
    """Aggiunge una nuova pianta e restituisce l'oggetto creato."""
    plant_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()
    ws = _get_spreadsheet().worksheet(PLANTS_SHEET)
    ws.append_row([
        plant_id,
        name.strip(),
        room.strip(),
        watering_frequency_days,
        notes.strip(),
        image_url,
        house.strip(),
        created_at,
    ])
    _invalidate_cache()
    return {
        "id": plant_id,
        "name": name.strip(),
        "room": room.strip(),
        "watering_frequency_days": watering_frequency_days,
        "notes": notes.strip(),
        "image_url": image_url,
        "house": house.strip(),
        "created_at": created_at,
        "watering_log": [],
    }


def update_plant(plant_id: str, **fields) -> bool:
    """
    Aggiorna i campi indicati per la pianta con l'ID specificato.
    Restituisce True se l'aggiornamento è andato a buon fine.
    """
    ws = _get_spreadsheet().worksheet(PLANTS_SHEET)
    records = ws.get_all_records()

    for i, row in enumerate(records, start=2):  # riga 1 = intestazioni
        if row["id"] == plant_id:
            for key, value in fields.items():
                if key in PLANTS_HEADERS and key not in ("id", "created_at"):
                    col = PLANTS_HEADERS.index(key) + 1
                    ws.update_cell(i, col, value)
            _invalidate_cache()
            return True
    return False


def delete_plant(plant_id: str) -> bool:
    """Elimina la pianta e tutto il suo watering_log. Restituisce True se eliminata."""
    deleted = False

    # Elimina dal foglio plants
    ws_plants = _get_spreadsheet().worksheet(PLANTS_SHEET)
    records = ws_plants.get_all_records()
    for i, row in enumerate(records, start=2):
        if row["id"] == plant_id:
            ws_plants.delete_rows(i)
            deleted = True
            break

    # Elimina le righe di watering_log associate (in ordine inverso)
    ws_log = _get_spreadsheet().worksheet(WATERING_SHEET)
    log_records = ws_log.get_all_records()
    rows_to_delete = [
        i for i, r in enumerate(log_records, start=2)
        if r["plant_id"] == plant_id
    ]
    for i in reversed(rows_to_delete):
        ws_log.delete_rows(i)

    if deleted:
        _invalidate_cache()
    return deleted


# ──────────────────────────────────────────────
# API pubblica – Log annaffiature
# ──────────────────────────────────────────────

def log_watering(plant_id: str, timestamp: datetime | None = None) -> bool:
    """
    Registra un evento di annaffiatura per la pianta indicata.
    Se timestamp è None, usa la data/ora corrente.
    Restituisce True se l'operazione è riuscita.
    """
    ts = (timestamp or datetime.now()).isoformat()
    ws = _get_spreadsheet().worksheet(WATERING_SHEET)
    ws.append_row([str(uuid.uuid4()), plant_id, ts])
    _invalidate_cache()
    return True


def delete_watering_log_entry(plant_id: str, index: int) -> bool:
    """Rimuove una singola voce del log di annaffiatura per posizione (0‑based, ordine crescente)."""
    ws = _get_spreadsheet().worksheet(WATERING_SHEET)
    records = ws.get_all_records()

    # Filtra solo le righe di questa pianta, ordinate per timestamp
    plant_log = sorted(
        [(i, r) for i, r in enumerate(records, start=2) if r["plant_id"] == plant_id],
        key=lambda x: x[1]["watered_at"],
    )

    if 0 <= index < len(plant_log):
        row_number = plant_log[index][0]
        ws.delete_rows(row_number)
        _invalidate_cache()
        return True
    return False


# ──────────────────────────────────────────────
# Helper di stato (identici alla versione JSON)
# ──────────────────────────────────────────────

def get_last_watered(plant: dict) -> datetime | None:
    """Restituisce la data/ora dell'ultima annaffiatura, o None."""
    log = plant.get("watering_log", [])
    if not log:
        return None
    return datetime.fromisoformat(log[-1])


def get_next_watering(plant: dict) -> datetime | None:
    """
    Calcola la prossima data di annaffiatura in base all'ultima registrazione
    e alla frequenza impostata. Restituisce None se non è mai stata annaffiata.
    """
    last = get_last_watered(plant)
    if last is None:
        return None
    return last + timedelta(days=plant["watering_frequency_days"])


def watering_status(plant: dict) -> str:
    """
    Restituisce lo stato di annaffiatura:
    - 'never'    : mai annaffiata
    - 'overdue'  : in ritardo
    - 'today'    : da annaffiare oggi
    - 'upcoming' : in programma nei prossimi giorni
    """
    next_dt = get_next_watering(plant)
    if next_dt is None:
        return "never"
    now = datetime.now()
    diff = (next_dt.date() - now.date()).days
    if diff < 0:
        return "overdue"
    if diff == 0:
        return "today"
    return "upcoming"
