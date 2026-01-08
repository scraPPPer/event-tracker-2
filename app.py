import streamlit as st
import pandas as pd
from supabase import create_client
import datetime
from datetime import timedelta

# --- SEITE KONFIGURIEREN ---
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
st.title("☁️ scraPPPers Tracker")

# 1. EINGABE
with st.expander("➕ Neues Ereignis eintragen"):
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
    
    # --- DER GLOBALE SCHIEBEREGLER ---
    min_year = int(df_raw['Jahr'].min())
    max_year = int(df_raw['Jahr'].max())
    
    st.subheader("🗓️ Zeitraum filtern")
    if min_year == max_year:
        selected_years = (min_year, max_year)
        st.info(f"Daten für {min_year} vorhanden.")
    else:
        selected_years = st.slider("Jahre wählen:", min_year, max_year, (min_year, max_year))

    # DATEN FILTERN
    df = df_raw[(df_raw['Jahr'] >= selected_years[0]) & (df_raw['Jahr'] <= selected_years[1])].copy()
    
    # Mapping für Deutsch
    days_de = {'Monday': 'Mo', 'Tuesday': 'Di', 'Wednesday': 'Mi', 'Thursday': 'Do', 'Friday': 'Fr', 'Saturday': 'Sa', 'Sunday': 'So'}
    months_de = {1: 'Jan', 2: 'Feb', 3: 'Mär', 4: 'Apr', 5: 'Mai', 6: 'Jun', 7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Okt', 11: 'Nov', 12: 'Dez'}
    
    df['Wochentag'] = df['event_date'].dt.day_name().map(days_de)
    df['Monat_Name'] = df['event_date'].dt.month.map(months_de)
    df = df.sort_values(by='event_date')

    # --- A. PROGNOSE ---
    st.subheader("🔮 Analyse & Prognose")
    if len(df) >= 2:
        df['diff'] = df['event_date'].diff().dt.days
        avg_days = df['diff'].mean()
        last_date = df['event_date'].iloc[-1]
        next_date = last_date + timedelta(days=avg_days)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Ø Tage", f"{avg_days:.1f}")
        c2.metric("Zuletzt", last_date.strftime("%d.%m."))
        c3.metric("Nächste", next_date.strftime("%d.%m."))
    else:
        st.warning("Mehr Daten für Prognose nötig.")

    # --- B. DIAGRAMME (Jahre & Wochentage) ---
    st.divider()
    
    st.markdown("### 📊 Häufigkeit nach Jahr")
    year_counts = df['Jahr'].value_counts().sort_index()
    st.bar_chart(year_counts, color="#FF4B4B")

    st.markdown("### 🗓️ Häufigkeit nach Wochentag")
    w_order = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']
    weekday_counts = df['Wochentag'].value_counts().reindex(w_order).fillna(0)
    st.bar_chart(weekday_counts, color="#2E66FF")

    # --- C. HEATMAP (REPARIERT) ---
    st.markdown("### 🌡️ Heatmap (Muster)")
    # Wichtig: Hier stand vorher der Fehler!
    heatmap_data = pd.crosstab(df['Wochentag'], df['Monat_Name'])
    
    # Sortierung sicherstellen
    m_order = ['Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez']
    heatmap_data = heatmap_data.reindex(index=[t for t in w_order if t in heatmap_data.index], 
                                       columns=[m for m in m_order if m in heatmap_data.columns])
    
    st.dataframe(
        heatmap_data.style.background_gradient(cmap="Reds", axis=None).format("{:.0f}"),
        use_container_width=True
    )

    # --- D. TABELLE ---
    with st.expander("📄 Alle Einträge"):
        st.dataframe(df[['event_date', 'event_name', 'notes']].sort_values(by='event_date', ascending=False), use_container_width=True)

else:
    st.info("Noch keine Daten vorhanden.")
