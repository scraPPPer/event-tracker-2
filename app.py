import streamlit as st
import pandas as pd
from supabase import create_client
import datetime
from datetime import timedelta

# --- SEITE KONFIGURIEREN ---
st.set_page_config(page_title="Event-Tracker", layout="centered")

# CSS für kleinere Überschriften
st.markdown("""
    <style>
    h1 { font-size: 1.8rem !important; }
    h2 { font-size: 1.5rem !important; }
    h3 { font-size: 1.2rem !important; }
    </style>
    """, unsafe_allow_html=True)

# --- KONFIGURATION (SECRETS) ---
try:
    SUPABASE_URL = st.secrets["supabase_url"]
    SUPABASE_KEY = st.secrets["supabase_key"]
except Exception:
    st.error("Bitte Secrets in Streamlit Cloud eintragen!")
    st.stop()

@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def run_query():
    client = init_connection()
    response = client.table("events").select("*").execute()
    return pd.DataFrame(response.data)

def save_entry(name, date_obj, notes):
    client = init_connection()
    data = {"event_name": name, "event_date": date_obj.strftime("%Y-%m-%d"), "notes": notes}
    client.table("events").insert(data).execute()

# --- APP LAYOUT ---
st.title("scraPPPers Tracker")

# 1. EINGABE
with st.expander("Neues Ereignis eintragen"):
    name = st.text_input("Was ist passiert?", "Ereignis")
    date = st.date_input("Datum", datetime.date.today())
    notes = st.text_area("Details")
    if st.button("Speichern", use_container_width=True, type="primary"):
        save_entry(name, date, notes)
        st.success("Gespeichert!")
        st.cache_data.clear()
        st.rerun()

st.divider()

# 2. DATEN ABFRAGEN & VORBEREITEN
df_raw = run_query()

if not df_raw.empty:
    df_raw['event_date'] = pd.to_datetime(df_raw['event_date'])
    df_raw['Jahr'] = df_raw['event_date'].dt.year
    
    # --- DER GLOBALE SCHIEBEREGLER (Mittelgrau) ---
    min_year = int(df_raw['Jahr'].min())
    max_year = int(df_raw['Jahr'].max())
    
    st.subheader("Zeitraum filtern")
    if min_year == max_year:
        selected_years = (min_year, max_year)
    else:
        # Streamlit nutzt für Slider primär die Theme-Farben, aber wir halten es schlicht
        selected_years = st.slider("Jahre wählen:", min_year, max_year, (min_year, max_year))

    # DATEN FILTERN
    df = df_raw[(df_raw['Jahr'] >= selected_years[0]) & (df_raw['Jahr'] <= selected_years[1])].copy()
    
    days_de = {'Monday': 'Mo', 'Tuesday': 'Di', 'Wednesday': 'Mi', 'Thursday': 'Do', 'Friday': 'Fr', 'Saturday': 'Sa', 'Sunday': 'So'}
    months_de = {1: 'Jan', 2: 'Feb', 3: 'Mär', 4: 'Apr', 5: 'Mai', 6: 'Jun', 7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Okt', 11: 'Nov', 12: 'Dez'}
    
    df['Wochentag'] = df['event_date'].dt.day_name().map(days_de)
    df['Monat_Name'] = df['event_date'].dt.month.map(months_de)
    df = df.sort_values(by='event_date')

    # --- A. ANALYSE & PROGNOSE (2x2 Layout) ---
    st.subheader("Analyse & Prognose")
    
    total_count = len(df)
    
    # Erste Zeile
    col1, col2 = st.columns(2)
    col1.metric("Gesamtanzahl", total_count)
    
    if total_count >= 2:
        df['diff'] = df['event_date'].diff().dt.days
        avg_days = df['diff'].mean()
        last_date = df['event_date'].iloc[-1]
        next_date = last_date + timedelta(days=avg_days)
        
        col2.metric("Ø Tage Abstand", f"{avg_days:.1f}")
        
        # Zweite Zeile
        col3, col4 = st.columns(2)
        col3.metric("Zuletzt am", last_date.strftime("%d.%m."))
        col4.metric("Nächste ca.", next_date.strftime("%d.%m."))
    else:
        col2.info("Mehr Daten nötig")

    # --- B. DIAGRAMME (Grau & Beschriftet) ---
    st.divider()
    
    # Diagramm-Farbe (Warmes Mittelgrau)
    warm_gray = "#8C837E"

    st.markdown("### Häufigkeit nach Jahr")
    year_counts = df['Jahr'].value_counts().sort_index().reset_index()
    year_counts.columns = ['Jahr', 'Anzahl']
    st.bar_chart(year_counts.set_index('Jahr'), color=warm_gray)
    # Hinweis: Native st.bar_chart Labels sind in der aktuellen Streamlit Version eingeschränkt, 
    # daher nutzen wir die Standard-Interaktivität (Hover zeigt Wert).

    st.markdown("### Häufigkeit nach Wochentag")
    w_order = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']
    weekday_counts = df['Wochentag'].value_counts().reindex(w_order).fillna(0).reset_index()
    weekday_counts.columns = ['Wochentag', 'Anzahl']
    st.bar_chart(weekday_counts.set_index('Wochentag'), color=warm_gray)

    # --- C. HEATMAP ---
    st.markdown("### Heatmap (Muster)")
    if not df.empty:
        heatmap_data = pd.crosstab(df['Wochentag'], df['Monat_Name'])
        m_order = ['Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez']
        existing_w = [t for t in w_order if t in heatmap_data.index]
        existing_m = [m for m in m_order if m in heatmap_data.columns]
        
        if existing_w and existing_m:
            heatmap_display = heatmap_data.reindex(index=existing_w, columns=existing_m).fillna(0)
            st.dataframe(
                heatmap_display.style.background_gradient(cmap="Reds", axis=None).format("{:.0f}"),
                use_container_width=True
            )

    # --- D. TABELLE ---
    with st.expander("Alle Einträge"):
        st.dataframe(df[['event_date', 'event_name', 'notes']].sort_values(by='event_date', ascending=False), use_container_width=True)

else:
    st.info("Noch keine Daten vorhanden.")
