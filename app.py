import streamlit as st
import pandas as pd
from supabase import create_client
import datetime
from datetime import timedelta

# --- SEITE KONFIGURIEREN ---
st.set_page_config(page_title="Event-Tracker", layout="centered")

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
st.title("☁️ scraPPPers Tracker")

# 1. EINGABE
with st.expander("➕ Neues Ereignis eintragen", expanded=False):
    name = st.text_input("Was ist passiert?", "Ereignis")
    date = st.date_input("Datum", datetime.date.today())
    notes = st.text_area("Details")
    if st.button("Speichern", use_container_width=True, type="primary"):
        save_entry(name, date, notes)
        st.success("Gespeichert!")
        st.cache_data.clear()
        st.rerun()

st.divider()

# 2. DATEN ABFRAGEN
df = run_query()

if not df.empty:
    # Datenaufbereitung
    df['event_date'] = pd.to_datetime(df['event_date'])
    df = df.sort_values(by='event_date')
    
    # Mapping für Deutsch
    days_de = {'Monday': 'Mo', 'Tuesday': 'Di', 'Wednesday': 'Mi', 'Thursday': 'Do', 'Friday': 'Fr', 'Saturday': 'Sa', 'Sunday': 'So'}
    months_de = {1: 'Jan', 2: 'Feb', 3: 'Mär', 4: 'Apr', 5: 'Mai', 6: 'Jun', 7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Okt', 11: 'Nov', 12: 'Dez'}
    
    df['Wochentag'] = df['event_date'].dt.day_name().map(days_de)
    df['Monat_Nr'] = df['event_date'].dt.month
    df['Monat'] = df['Monat_Nr'].map(months_de)
    df['Jahr'] = df['event_date'].dt.year

    # --- A. PROGNOSE ---
    st.subheader("🔮 Analyse & Prognose")
    if len(df) >= 2:
        df['diff'] = df['event_date'].diff().dt.days
        avg_days = df['diff'].mean()
        last_date = df['event_date'].iloc[-1]
        next_date = last_date + timedelta(days=avg_days)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Ø Abstand", f"{avg_days:.1f} d")
        c2.metric("Zuletzt", last_date.strftime("%d.%m."))
        c3.metric("Nächste ca.", next_date.strftime("%d.%m."))
    
    # --- B. VERLAUF (LINIE STATT BÄLKCHEN) ---
    st.markdown("### 📈 Zeitlicher Verlauf")
    # Wir gruppieren nach Monat, um eine schöne Linie zu bekommen
    timeline = df.set_index('event_date').resample('ME').size().reset_index()
    timeline.columns = ['Datum', 'Anzahl']
    
    # Wir nutzen st.line_chart für eine saubere Linie
    st.line_chart(timeline.set_index('Datum'), color="#FF4B4B")

    # --- C. HEATMAP (MUSTER) ---
    st.markdown("### 🗓️ Muster-Erkennung")
    # Heatmap erstellen
    heatmap_data = pd.crosstab(df['Wochentag'], df['Monat'])
    
    # Sortierung der Wochentage
    wochentage_order = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']
    vorhandene_tage = [t for t in wochentage_order if t in heatmap_data.index]
    heatmap_data = heatmap_data.reindex(vorhandene_tage)
    
    # Darstellung mit Style (Heatmap-Effekt)
    st.dataframe(
        heatmap_data.style.background_gradient(cmap="Reds", axis=None).format("{:.0f}"),
        use_container_width=True
    )

    # --- D. TABELLE ---
    with st.expander("📄 Alle Einträge"):
        st.dataframe(df[['event_date', 'event_name', 'notes']].sort_values(by='event_date', ascending=False), use_container_width=True)

else:
    st.info("Noch keine Daten vorhanden. Trag oben dein erstes Ereignis ein!")
