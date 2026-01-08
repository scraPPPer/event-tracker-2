import streamlit as st
import pandas as pd
from supabase import create_client
import datetime
from datetime import timedelta

# --- SEITE KONFIGURIEREN (Mobile Optimierung) ---
st.set_page_config(page_title="Event-Tracker", layout="centered")

# --- KONFIGURATION ---
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
st.title("☁️ Event-Tracker")

# Eingabe-Bereich
with st.container():
    st.subheader("Neues Ereignis")
    name = st.text_input("Was ist passiert?", "Kopfschmerzen")
    date = st.date_input("Wann?", datetime.date.today())
    notes = st.text_area("Notizen")
    
    if st.button("Speichern", use_container_width=True, type="primary"):
        save_entry(name, date, notes)
        st.success("Erfolgreich gespeichert!")
        st.cache_data.clear()
        st.rerun()

st.divider()

# Analyse-Bereich
df = run_query()

if not df.empty:
    df['event_date'] = pd.to_datetime(df['event_date'])
    df = df.sort_values(by='event_date')
    
    # Statistiken (Metrics) - Am Handy werden diese schön untereinander gestapelt
    if len(df) >= 2:
        df['diff'] = df['event_date'].diff().dt.days
        avg_days = df['diff'].mean()
        next_date = df['event_date'].iloc[-1] + timedelta(days=avg_days)
        
        c1, c2 = st.columns(2)
        c1.metric("Abstand", f"{avg_days:.1f} Tage")
        c2.metric("Nächste Prognose", next_date.strftime("%d.%m."))

    st.subheader("Verlauf")
    # Area Chart nutzt die volle Breite am Handy
    timeline = df.set_index('event_date').resample('M').size()
    st.area_chart(timeline)

    with st.expander("Rohdaten einsehen"):
        st.dataframe(df, use_container_width=True)
else:
    st.info("Noch keine Daten vorhanden.")
