"""
data_manager.py – Gestione persistente dei dati delle piante.
I dati vengono salvati in data/plants.json.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path

DATA_FILE = Path(__file__).parent.parent / "data" / "plants.json"


# ──────────────────────────────────────────────
# I/O di base
# ──────────────────────────────────────────────

def _load_raw() -> dict:
    """Carica il contenuto grezzo del file JSON."""
    if not DATA_FILE.exists():
        return {"plants": []}
    with DATA_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save_raw(data: dict) -> None:
    """Scrive il contenuto aggiornato nel file JSON."""
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ──────────────────────────────────────────────
# API pubblica
# ──────────────────────────────────────────────

def get_all_plants() -> list[dict]:
    """Restituisce la lista di tutte le piante."""
    return _load_raw().get("plants", [])


def get_plant_by_id(plant_id: str) -> dict | None:
    """Restituisce una singola pianta per ID, o None se non trovata."""
    return next((p for p in get_all_plants() if p["id"] == plant_id), None)


def add_plant(
    name: str,
    room: str,
    watering_frequency_days: int,
    notes: str = "",
) -> dict:
    """Aggiunge una nuova pianta e restituisce l'oggetto creato."""
    plant = {
        "id": str(uuid.uuid4()),
        "name": name.strip(),
        "room": room.strip(),
        "watering_frequency_days": watering_frequency_days,
        "notes": notes.strip(),
        "created_at": datetime.now().isoformat(),
        "watering_log": [],
    }
    data = _load_raw()
    data["plants"].append(plant)
    _save_raw(data)
    return plant


def update_plant(plant_id: str, **fields) -> bool:
    """
    Aggiorna i campi indicati per la pianta con l'ID specificato.
    Restituisce True se l'aggiornamento è andato a buon fine.
    """
    data = _load_raw()
    for plant in data["plants"]:
        if plant["id"] == plant_id:
            for key, value in fields.items():
                if key in plant and key not in ("id", "created_at", "watering_log"):
                    plant[key] = value
            _save_raw(data)
            return True
    return False


def delete_plant(plant_id: str) -> bool:
    """Elimina la pianta con l'ID specificato. Restituisce True se eliminata."""
    data = _load_raw()
    original_len = len(data["plants"])
    data["plants"] = [p for p in data["plants"] if p["id"] != plant_id]
    if len(data["plants"]) < original_len:
        _save_raw(data)
        return True
    return False


def log_watering(plant_id: str, timestamp: datetime | None = None) -> bool:
    """
    Registra un evento di annaffiatura per la pianta indicata.
    Se timestamp è None, usa la data/ora corrente.
    Restituisce True se l'operazione è riuscita.
    """
    ts = (timestamp or datetime.now()).isoformat()
    data = _load_raw()
    for plant in data["plants"]:
        if plant["id"] == plant_id:
            plant["watering_log"].append(ts)
            # Mantieni il log ordinato in ordine crescente
            plant["watering_log"].sort()
            _save_raw(data)
            return True
    return False


def delete_watering_log_entry(plant_id: str, index: int) -> bool:
    """Rimuove una singola voce del log di annaffiatura per posizione."""
    data = _load_raw()
    for plant in data["plants"]:
        if plant["id"] == plant_id:
            if 0 <= index < len(plant["watering_log"]):
                plant["watering_log"].pop(index)
                _save_raw(data)
                return True
    return False


# ──────────────────────────────────────────────
# Helper di stato
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
    from datetime import timedelta
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
