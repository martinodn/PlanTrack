"""
app.py – PlanTrack
Applicazione Streamlit per monitorare le piante di casa.

Struttura:
  ├─ Sidebar: navigazione + logo
  ├─ Dashboard:          panoramica piante con carte e stato annaffiatura
  ├─ Aggiungi Pianta:    form registrazione nuova pianta
  ├─ Registra Annaffiatura: log rapido annaffiatura per pianta
  ├─ Calendario:         Gantt e heatmap delle prossime annaffiature
  └─ Gestisci Piante:    modifica / elimina piante esistenti
"""

import sys
from pathlib import Path

# Aggiunge la root del progetto al path per rendere importabili i moduli utils
sys.path.insert(0, str(Path(__file__).parent))

from datetime import datetime

import streamlit as st

from utils.data_manager import (
    add_plant,
    delete_plant,
    delete_watering_log_entry,
    get_all_plants,
    get_last_watered,
    get_next_watering,
    log_watering,
    update_plant,
    watering_status,
)
from utils.calendar_utils import (
    STATUS_COLOR,
    STATUS_LABEL,
    build_gantt_figure,
    build_heatmap_figure,
    build_schedule_dataframe,
)

# ──────────────────────────────────────────────────────────────────────────────
# Autenticazione
# ──────────────────────────────────────────────────────────────────────────────

def check_password():
    """Restituisce True se l'utente ha inserito la password corretta."""

    def password_entered():
        """Controlla se la password inserita è corretta."""
        if st.session_state["password"] == st.secrets["PASSWORD"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # non conservare la password in chiaro
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # Prima esecuzione, mostra il form di login
        st.markdown(
            """
            <div style="text-align:center;padding:50px 0">
              <span style="font-size:5rem">🌿</span>
              <h1 style="color:#2E7D32">PlanTrack Login</h1>
              <p>Inserisci la password per gestire le tue piante</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        if "password_correct" in st.session_state and not st.session_state["password_correct"]:
            st.error("😕 Password errata")
        return False
    elif not st.session_state["password_correct"]:
        # Password errata, mostra di nuovo il form
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password errata")
        return False
    else:
        # Password corretta
        return True

if not check_password():
    st.stop()

# ──────────────────────────────────────────────────────────────────────────────
# Configurazione pagina
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PlanTrack 🌿",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────────────────────
# CSS personalizzato
# ──────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
/* ── Colori di base ── */
:root {
    --green-dark:  #2E7D32;
    --green-mid:   #4CAF50;
    --green-light: #C8E6C9;
    --brown:       #795548;
    --bg:          #F1F8E9;
}

/* ── Sfondo generale ── */
.main { background-color: var(--bg); }
section[data-testid="stSidebar"] { background-color: #1B5E20; }
section[data-testid="stSidebar"] * { color: #E8F5E9 !important; }
section[data-testid="stSidebar"] .stRadio label { color: #E8F5E9 !important; }

/* ── Card pianta ── */
.plant-card {
    background: #fff;
    border-radius: 16px;
    padding: 16px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.10);
    margin-bottom: 4px;
    transition: box-shadow .2s;
}
.plant-card:hover { box-shadow: 0 4px 18px rgba(46,125,50,.18); }

/* ── Badge stato ── */
.badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: .78rem;
    font-weight: 600;
    color: #fff;
}
.badge-overdue  { background: #EF5350; }
.badge-today    { background: #FF9800; }
.badge-upcoming { background: #4CAF50; }
.badge-never    { background: #9E9E9E; }

/* ── Titoli sezione ── */
.section-title {
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--green-dark);
    border-left: 5px solid var(--green-mid);
    padding-left: 12px;
    margin-bottom: 20px;
}

/* ── Form card ── */
.form-card {
    background: #fff;
    border-radius: 16px;
    padding: 28px 32px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08);
    margin-bottom: 24px;
}
</style>
""",
    unsafe_allow_html=True,
)


# ──────────────────────────────────────────────────────────────────────────────
# Helper UI
# ──────────────────────────────────────────────────────────────────────────────

def _badge(status: str) -> str:
    label = STATUS_LABEL.get(status, status)
    return f'<span class="badge badge-{status}">{label}</span>'


def _days_label(plant: dict) -> str:
    next_dt = get_next_watering(plant)
    if next_dt is None:
        return "Mai annaffiata"
    diff = (next_dt.date() - datetime.now().date()).days
    if diff < 0:
        return f"In ritardo di {abs(diff)} giorno/i"
    if diff == 0:
        return "Da annaffiare oggi!"
    return f"Tra {diff} giorno/i"


def _render_plant_card(plant: dict, col):
    """Renderizza la card di una singola pianta all'interno di una colonna."""
    status  = watering_status(plant)
    last    = get_last_watered(plant)
    next_dt = get_next_watering(plant)

    last_str = last.strftime("%d/%m/%Y %H:%M") if last else "—"
    next_str = next_dt.strftime("%d/%m/%Y") if next_dt else "—"

    notes_html = (
        f'<p style="font-size:.78rem;color:#9E9E9E;margin-top:4px">📝 {plant["notes"]}</p>'
        if plant.get("notes") else ""
    )

    image_html = ""
    if plant.get("image_url"):
        image_html = f'<img src="{plant["image_url"]}" style="width:100%; border-radius:12px; margin-bottom:12px; object-fit:cover; height:140px;">'

    with col:
        st.markdown(
            f"""
<div class="plant-card">
  {image_html}
  <h4 style="margin:0 0 4px 0;color:#2E7D32">{plant['name']}</h4>
  <p style="margin:0 0 6px 0;color:#757575;font-size:.85rem">🏠 {plant['room']} &nbsp;|&nbsp; 💧 ogni {plant['watering_frequency_days']} giorni</p>
  {_badge(status)}
  <p style="margin:6px 0 2px 0;font-size:.82rem;color:#555">
    ⏱ Ultima: <b>{last_str}</b><br>
    📅 Prossima: <b>{next_str}</b>
  </p>
  <p style="font-size:.80rem;color:#888;font-style:italic">{_days_label(plant)}</p>
  {notes_html}
</div>
""",
            unsafe_allow_html=True,
        )


# ──────────────────────────────────────────────────────────────────────────────
# Sidebar – navigazione
# ──────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        """
        <div style="text-align:center;padding:12px 0 18px 0">
          <span style="font-size:3rem">🌿</span>
          <h1 style="margin:0;font-size:1.8rem;letter-spacing:1px">PlanTrack</h1>
          <p style="margin:0;font-size:.85rem;opacity:.8">L'aiutante digitale per farle sopravvivere 🤞</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    page = st.radio(
        "Navigazione",
        [
            "🏠  Dashboard",
            "➕  Aggiungi Pianta",
            "💧  Registra Annaffiatura",
            "📅  Calendario",
            "✏️  Gestisci Piante",
        ],
        label_visibility="collapsed",
    )

    st.divider()
    plants_all = get_all_plants()
    st.metric("Piante registrate", len(plants_all))
    overdue_count = sum(1 for p in plants_all if watering_status(p) in ("overdue", "today"))
    st.metric("Da annaffiare oggi / in ritardo", overdue_count)


# ──────────────────────────────────────────────────────────────────────────────
# PAGE 1 – Dashboard
# ──────────────────────────────────────────────────────────────────────────────

if "Dashboard" in page:
    st.markdown('<p class="section-title">🏠 Dashboard</p>', unsafe_allow_html=True)

    plants = get_all_plants()

    if not plants:
        st.info(
            "Non hai ancora registrato nessuna pianta. "
            "Vai su **➕ Aggiungi Pianta** per iniziare!",
            icon="🌱",
        )
    else:
        # Filtri rapidi
        col_f1, col_f2, col_f3 = st.columns([2, 2, 1])
        with col_f1:
            rooms = sorted({p["room"] for p in plants})
            room_filter = st.selectbox("Filtra per stanza", ["Tutte"] + rooms)
        with col_f2:
            status_options = ["Tutti", "In ritardo", "Oggi", "In programma", "Mai annaffiata"]
            status_filter = st.selectbox("Filtra per stato", status_options)
        with col_f3:
            cols_per_row = st.selectbox("Colonne", [2, 3, 4], index=1)

        # Applicazione filtri
        visible = plants
        if room_filter != "Tutte":
            visible = [p for p in visible if p["room"] == room_filter]
        status_map = {
            "In ritardo": "overdue",
            "Oggi": "today",
            "In programma": "upcoming",
            "Mai annaffiata": "never",
        }
        if status_filter != "Tutti" and status_filter in status_map:
            visible = [p for p in visible if watering_status(p) == status_map[status_filter]]

        if not visible:
            st.warning("Nessuna pianta corrisponde ai filtri selezionati.")
        else:
            # Render a griglia
            for row_start in range(0, len(visible), cols_per_row):
                row_plants = visible[row_start : row_start + cols_per_row]
                cols = st.columns(cols_per_row)
                for plant, col in zip(row_plants, cols):
                    _render_plant_card(plant, col)

        # Legenda stati
        st.divider()
        leg_cols = st.columns(4)
        for (s, lbl), lc in zip(STATUS_LABEL.items(), leg_cols):
            color = STATUS_COLOR[s]
            lc.markdown(
                f'<span style="background:{color};color:#fff;padding:4px 12px;'
                f'border-radius:20px;font-size:.8rem">{lbl}</span>',
                unsafe_allow_html=True,
            )


# ──────────────────────────────────────────────────────────────────────────────
# PAGE 2 – Aggiungi Pianta
# ──────────────────────────────────────────────────────────────────────────────

elif "Aggiungi" in page:
    st.markdown('<p class="section-title">➕ Aggiungi una nuova pianta</p>', unsafe_allow_html=True)

    with st.form("add_plant_form", clear_on_submit=True):
        st.markdown('<div class="form-card">', unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("🌿 Nome della pianta *", placeholder="es. Monstera, Orchidea…")
            room = st.text_input("🏠 Stanza *", placeholder="es. Soggiorno, Camera…")
        with c2:
            freq = st.number_input(
                "💧 Frequenza di annaffiatura (giorni) *",
                min_value=1, max_value=365, value=7, step=1,
            )

        notes = st.text_area("📝 Note (opzionale)", placeholder="es. Annaffia il sottovaso, evita ristagni…", height=90)
        image_url = st.text_input(
            "🖼 URL Immagine (opzionale)", 
            placeholder="https://.../immagine.jpg",
            help="Assicurati che sia un link diretto all'immagine (deve finire con .jpg, .png, .webp, ecc.)"
        )

        st.markdown("<br>", unsafe_allow_html=True)
        submitted = st.form_submit_button("✅ Registra pianta", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    if submitted:
        if not name.strip() or not room.strip():
            st.error("Nome e stanza sono campi obbligatori.")
        else:
            plant = add_plant(
                name=name,
                room=room,
                watering_frequency_days=int(freq),
                notes=notes,
                image_url=image_url,
            )
            st.success(f"✅ **{plant['name']}** aggiunta con successo!")

            # Preview card
            preview_col, _ = st.columns([1, 2])
            _render_plant_card(plant, preview_col)


# ──────────────────────────────────────────────────────────────────────────────
# PAGE 3 – Registra Annaffiatura
# ──────────────────────────────────────────────────────────────────────────────

elif "Annaffiatura" in page:
    st.markdown('<p class="section-title">💧 Registra un\'annaffiatura</p>', unsafe_allow_html=True)

    plants = get_all_plants()
    if not plants:
        st.info("Nessuna pianta registrata. Prima aggiungi una pianta!", icon="🌱")
    else:
        # Ordinamento: prima le urgenti
        priority = {"overdue": 0, "today": 1, "never": 2, "upcoming": 3}
        plants_sorted = sorted(plants, key=lambda p: priority.get(watering_status(p), 9))

        st.markdown("### Annaffia con un click")

        for plant in plants_sorted:
            status = watering_status(plant)
            last   = get_last_watered(plant)
            next_dt = get_next_watering(plant)

            c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
            with c1:
                st.markdown(
                    f'<b style="font-size:1rem">{plant["name"]}</b> '
                    f'<span style="color:#888;font-size:.85rem">({plant["room"]})</span>&nbsp;'
                    f'{_badge(status)}',
                    unsafe_allow_html=True,
                )
            with c2:
                st.caption(f"Ultima: {last.strftime('%d/%m/%Y %H:%M') if last else '—'}")
            with c3:
                st.caption(f"Prossima: {next_dt.strftime('%d/%m/%Y') if next_dt else '—'}")
            with c4:
                if st.button("💧 Annaffia", key=f"water_{plant['id']}"):
                    log_watering(plant["id"])
                    st.success(f"✅ {plant['name']} annaffiata!")
                    st.rerun()

            st.divider()

        # ── Annaffia multiple piante in una volta ──────────────
        st.markdown("### Annaffia più piante contemporaneamente")
        plant_names_map = {p["name"]: p["id"] for p in plants}
        selected_names  = st.multiselect(
            "Seleziona le piante da annaffiare",
            options=list(plant_names_map.keys()),
        )

        custom_ts = st.checkbox("Specifica data e ora manualmente", value=False)
        if custom_ts:
            col_d, col_t = st.columns(2)
            with col_d:
                chosen_date = st.date_input("📅 Data", value=datetime.now().date())
            with col_t:
                chosen_time = st.time_input("⏰ Ora", value=datetime.now().time())
            ts = datetime.combine(chosen_date, chosen_time)
        else:
            ts = None  # usa now()

        if st.button("💧 Registra annaffiatura selezionate", use_container_width=True):
            if not selected_names:
                st.warning("Seleziona almeno una pianta.")
            else:
                for n in selected_names:
                    log_watering(plant_names_map[n], ts)
                ts_label = ts.strftime("%d/%m/%Y %H:%M") if ts else datetime.now().strftime("%d/%m/%Y %H:%M")
                st.success(f"✅ {len(selected_names)} piante annaffiate il {ts_label}!")
                st.rerun()

        # ── Storico log (espandibile) ──────────────────────────
        st.divider()
        with st.expander("📋 Storico annaffiature (modifica / elimina voci)"):
            plants_refresh = get_all_plants()
            for plant in plants_refresh:
                log = plant.get("watering_log", [])
                if not log:
                    continue
                st.markdown(f"**{plant['name']}**")
                for i, entry in enumerate(reversed(log)):
                    idx_real = len(log) - 1 - i
                    dt = datetime.fromisoformat(entry)
                    ec1, ec2 = st.columns([4, 1])
                    ec1.text(f"  {dt.strftime('%d/%m/%Y %H:%M')}")
                    if ec2.button("🗑", key=f"del_{plant['id']}_{idx_real}"):
                        delete_watering_log_entry(plant["id"], idx_real)
                        st.rerun()


# ──────────────────────────────────────────────────────────────────────────────
# PAGE 4 – Calendario
# ──────────────────────────────────────────────────────────────────────────────

elif "Calendario" in page:
    st.markdown('<p class="section-title">📅 Calendario annaffiature</p>', unsafe_allow_html=True)

    plants = get_all_plants()
    if not plants:
        st.info("Nessuna pianta registrata. Prima aggiungi una pianta!", icon="🌱")
    else:
        tab1, tab2, tab3 = st.tabs(["📊 Timeline", "🗓 Heatmap", "📋 Tabella"])

        with tab1:
            days_ahead = st.slider("Giorni da visualizzare", 7, 60, 30)
            fig_gantt = build_gantt_figure(plants, days_ahead)
            st.plotly_chart(fig_gantt, use_container_width=True)

        with tab2:
            fig_heat = build_heatmap_figure(plants)
            st.plotly_chart(fig_heat, use_container_width=True)

        with tab3:
            df = build_schedule_dataframe(plants)
            if not df.empty:
                # Rimuovi colonne interne
                display_df = df.drop(columns=["ID", "_status"], errors="ignore")

                # Colorazione condizionale per la colonna "Stato"
                def color_status(val):
                    color_map = {
                        "In ritardo":    "#FFCDD2",
                        "Oggi":          "#FFE0B2",
                        "In programma":  "#C8E6C9",
                        "Mai annaffiata":"#F5F5F5",
                    }
                    return f"background-color: {color_map.get(val, 'white')}"

                styled = display_df.style.map(color_status, subset=["Stato"])
                st.dataframe(styled, use_container_width=True, hide_index=True)


# ──────────────────────────────────────────────────────────────────────────────
# PAGE 5 – Gestisci Piante
# ──────────────────────────────────────────────────────────────────────────────

elif "Gestisci" in page:
    st.markdown('<p class="section-title">✏️ Gestisci le piante</p>', unsafe_allow_html=True)

    plants = get_all_plants()
    if not plants:
        st.info("Nessuna pianta registrata.", icon="🌱")
    else:
        plant_options = {p["name"]: p["id"] for p in plants}
        selected_name = st.selectbox("Seleziona una pianta da modificare o eliminare", list(plant_options.keys()))
        selected_id   = plant_options[selected_name]
        plant         = next(p for p in plants if p["id"] == selected_id)

        tab_edit, tab_delete = st.tabs(["✏️ Modifica", "🗑 Elimina"])

        # ── Modifica ──
        with tab_edit:
            with st.form("edit_form"):
                c1, c2 = st.columns(2)
                with c1:
                    new_name  = st.text_input("Nome", value=plant["name"])
                    new_room  = st.text_input("Stanza", value=plant["room"])
                with c2:
                    new_freq  = st.number_input("Frequenza (giorni)", min_value=1, max_value=365,
                                                value=plant["watering_frequency_days"])
                new_notes = st.text_area("Note", value=plant.get("notes", ""), height=80)
                new_image = st.text_input(
                    "URL Immagine", 
                    value=plant.get("image_url", ""),
                    help="Assicurati che sia un link diretto all'immagine (deve finire con .jpg, .png, .webp, ecc.)"
                )

                save = st.form_submit_button("💾 Salva modifiche", use_container_width=True)

            if save:
                update_plant(
                    selected_id,
                    name=new_name,
                    room=new_room,
                    watering_frequency_days=int(new_freq),
                    notes=new_notes,
                    image_url=new_image,
                )
                st.success("✅ Pianta aggiornata!")
                st.rerun()

        # ── Elimina ──
        with tab_delete:
            st.warning(
                f"Sei sicuro di voler eliminare **{plant['name']}**? "
                "Questa operazione è irreversibile e cancellerà anche tutto lo storico.",
                icon="⚠️",
            )
            confirm = st.checkbox("Sì, voglio eliminare questa pianta")
            if st.button("🗑 Elimina definitivamente", disabled=not confirm, use_container_width=True):
                delete_plant(selected_id)
                st.success(f"✅ **{plant['name']}** eliminata.")
                st.rerun()
