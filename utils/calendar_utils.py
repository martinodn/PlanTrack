"""
calendar_utils.py – Logica per il calendario di annaffiatura.

Genera una tabella "heat-map" e un Gantt-style timeline delle prossime
annaffiature usando Plotly.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import plotly.graph_objects as go

from utils.data_manager import get_next_watering, watering_status

# ──────────────────────────────────────────────
# Palette colori stato
# ──────────────────────────────────────────────
STATUS_COLOR = {
    "overdue": "#EF5350",   # rosso
    "today":   "#FF9800",   # arancione
    "upcoming": "#66BB6A",  # verde
    "never":   "#BDBDBD",   # grigio
}

STATUS_LABEL = {
    "overdue":  "In ritardo",
    "today":    "Oggi",
    "upcoming": "In programma",
    "never":    "Mai annaffiata",
}


# ──────────────────────────────────────────────
# Tabella riepilogativa
# ──────────────────────────────────────────────

def build_schedule_dataframe(plants: list[dict]) -> pd.DataFrame:
    """
    Costruisce un DataFrame con una riga per pianta contenente:
    nome, stanza, ultima annaffiatura, prossima annaffiatura, giorni mancanti, stato.
    """
    rows = []
    now = datetime.now()
    for p in plants:
        log = p.get("watering_log", [])
        last_dt = datetime.fromisoformat(log[-1]) if log else None
        next_dt = get_next_watering(p)
        status  = watering_status(p)

        if next_dt:
            days_left = (next_dt.date() - now.date()).days
        else:
            days_left = None

        rows.append({
            "ID":                  p["id"],
            "Pianta":              p["name"],
            "Stanza":              p["room"],
            "Freq. (giorni)":      p["watering_frequency_days"],
            "Ultima annaffiatura": last_dt.strftime("%d/%m/%Y %H:%M") if last_dt else "—",
            "Prossima":            next_dt.strftime("%d/%m/%Y") if next_dt else "—",
            "Giorni mancanti":     days_left,
            "Stato":               STATUS_LABEL.get(status, status),
            "_status":             status,
        })

    return pd.DataFrame(rows)


# ──────────────────────────────────────────────
# Gantt / Timeline
# ──────────────────────────────────────────────

def build_gantt_figure(plants: list[dict], days_ahead: int = 30) -> go.Figure:
    """
    Crea un grafico Gantt-style che mostra le prossime annaffiature nei
    prossimi `days_ahead` giorni per ciascuna pianta.
    """
    today = datetime.now().date()
    end_date = today + timedelta(days=days_ahead)

    fig = go.Figure()

    # Asse X: da oggi a end_date
    shapes: list[dict] = []
    annotations: list[dict] = []

    plant_names: list[str] = []

    for idx, p in enumerate(plants):
        name  = p["name"]
        freq  = p["watering_frequency_days"]
        log   = p.get("watering_log", [])
        status = watering_status(p)
        color  = STATUS_COLOR.get(status, "#90A4AE")

        plant_names.append(name)

        # Calcola tutte le date di annaffiatura nell'intervallo
        if log:
            last_dt = datetime.fromisoformat(log[-1]).date()
        else:
            # Nessuna annaffiatura: mostra un singolo marker = "da annaffiare subito"
            shapes.append(dict(
                type="rect",
                x0=today, x1=today + timedelta(days=1),
                y0=idx - 0.4, y1=idx + 0.4,
                fillcolor="#BDBDBD",
                line=dict(width=0),
                layer="above",
            ))
            continue

        # Proietta le future annaffiature verso end_date
        cursor = last_dt + timedelta(days=freq)
        while cursor <= end_date:
            bar_color = STATUS_COLOR["overdue"] if cursor < today else (
                STATUS_COLOR["today"] if cursor == today else STATUS_COLOR["upcoming"]
            )
            shapes.append(dict(
                type="rect",
                x0=str(cursor),
                x1=str(cursor + timedelta(days=1)),
                y0=idx - 0.35,
                y1=idx + 0.35,
                fillcolor=bar_color,
                line=dict(width=0),
                layer="above",
            ))
            annotations.append(dict(
                x=str(cursor + timedelta(hours=12)),
                y=idx,
                text="💧",
                showarrow=False,
                font=dict(size=14),
            ))
            cursor += timedelta(days=freq)

    # Traccia fantasma per gli assi
    fig.add_trace(go.Scatter(
        x=[str(today), str(end_date)],
        y=[0, max(len(plants) - 1, 0)],
        mode="markers",
        marker=dict(opacity=0),
        showlegend=False,
    ))

    # Linea "oggi"
    shapes.append(dict(
        type="line",
        x0=str(today), x1=str(today),
        y0=-0.5, y1=len(plants) - 0.5,
        line=dict(color="#1565C0", width=2, dash="dot"),
    ))

    fig.update_layout(
        shapes=shapes,
        annotations=annotations,
        xaxis=dict(
            type="date",
            title="Data",
            range=[str(today - timedelta(days=1)), str(end_date + timedelta(days=1))],
            tickformat="%d %b",
        ),
        yaxis=dict(
            tickvals=list(range(len(plant_names))),
            ticktext=plant_names,
            autorange="reversed",
        ),
        height=max(300, 60 * len(plants) + 80),
        margin=dict(l=10, r=10, t=40, b=40),
        title="📅 Calendario annaffiatura – prossimi 30 giorni",
        plot_bgcolor="#F9FBF9",
        paper_bgcolor="#F9FBF9",
    )
    return fig


# ──────────────────────────────────────────────
# Mini heatmap mensile
# ──────────────────────────────────────────────

def build_heatmap_figure(plants: list[dict]) -> go.Figure:
    """
    Heatmap: piante sull'asse Y, giorni del mese sull'asse X.
    Il colore indica quante piante vanno annaffiate quel giorno.
    """
    today = datetime.now().date()
    days_range = [today + timedelta(days=i) for i in range(30)]

    # Matrice piante × giorni
    plant_names: list[str] = [p["name"] for p in plants]
    matrix: list[list[int]] = []

    for p in plants:
        row: list[int] = []
        log = p.get("watering_log", [])
        freq = p["watering_frequency_days"]
        if not log:
            row = [0] * 30
        else:
            last_dt = datetime.fromisoformat(log[-1]).date()
            cursor = last_dt + timedelta(days=freq)
            for d in days_range:
                if d == cursor:
                    row.append(1)
                    cursor += timedelta(days=freq)
                else:
                    row.append(0)
        matrix.append(row)

    day_labels = [d.strftime("%d/%m") for d in days_range]

    fig = go.Figure(data=go.Heatmap(
        z=matrix,
        x=day_labels,
        y=plant_names,
        colorscale=[[0, "#E8F5E9"], [1, "#2E7D32"]],
        showscale=False,
        hoverongaps=False,
        hovertemplate="<b>%{y}</b><br>%{x}<br>💧 Annaffiatura: %{z}<extra></extra>",
    ))

    fig.update_layout(
        title="Mappa annaffiature – prossimi 30 giorni",
        xaxis=dict(title="Data", tickangle=-45),
        yaxis=dict(title=""),
        height=max(250, 40 * len(plants) + 100),
        margin=dict(l=10, r=10, t=50, b=60),
        plot_bgcolor="#F9FBF9",
        paper_bgcolor="#F9FBF9",
    )
    return fig
