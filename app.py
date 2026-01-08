import streamlit as st
import pandas as pd
from supabase import create_client
import datetime
from datetime import timedelta

# --- SEITE KONFIGURIEREN ---
st.set_page_config(page_title="Event-Tracker", layout="centered")

# CSS für kleinere Überschriften & kompakte Metrics
st.markdown("""
    <style>
    h1 { font-size: 1.5rem !important; margin-bottom: 0.5rem; }
    h2 { font-size: 1.2rem !important; margin-top: 1rem; }
    h3 { font-size: 1.0rem !important; color: #666; }
    [data-testid="stMetricValue"] { font-size: 1.3rem !important; }
    [data-testid="stMetricLabel"] { font-size: 0.8rem !important; }
    </style>
    """, unsafe_allow_html=True)

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
st.title("scraPPPers Tracker")

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

# 2. DATEN ABFRAGEN
df_raw = run_query()

if not df_raw.empty:
    df_raw['event_date'] = pd.to_datetime(df_raw['event_date'])
    df_raw['Jahr'] = df_raw['event_date'].dt.year
    
    # --- NEUES DESIGN: JAHRES-FILTER (Multi-Select statt Slider) ---
    all_years = sorted(df_raw['Jahr'].unique().tolist(), reverse=True)
    
    st.subheader("Zeitraum wählen")
    selected_years = st.multiselect(
        "Zeige Daten für folgende Jahre:",
        options=all_years,
        default=all_years,
        placeholder="Wähle Jahre aus..."
    )

    # Filtern basierend auf der Auswahl
    df = df_raw[df_raw['Jahr'].isin(selected_years)].copy()
    
    days_de = {'Monday': 'Mo', 'Tuesday': 'Di', 'Wednesday': 'Mi', 'Thursday': 'Do', 'Friday': 'Fr', 'Saturday': 'Sa', 'Sunday': 'So'}
    months_de = {1: 'Jan', 2: 'Feb', 3: 'Mär', 4: 'Apr', 5: 'Mai', 6: 'Jun', 7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Okt', 11: 'Nov', 12: 'Dez'}
    
    df['Wochentag'] = df['event_date'].dt.day_name().map(days_de)
    df['Monat_Name'] = df['event_date'].dt.month.map(months_de)
    df = df.sort_values(by='event_date')

    # --- A. ANALYSE (KOMPAKT 2x2) ---
    st.subheader("Analyse & Prognose")
    
    m1, m2 = st.columns(2)
    m1.metric("Gesamt", len(df))
    
    if len(df) >= 2:
        df['diff'] = df['event_date'].diff().dt.days
        avg_days = df['diff'].mean()
        last_date = df['event_date'].iloc[-1]
        next_date = last_date + timedelta(days=avg_days)
        
        m2.metric("Ø Abstand", f"{avg_days:.1f} d")
        
        m3, m4 = st.columns(2)
        m3.metric("Zuletzt", last_date.strftime("%d.%m."))
        m4.metric("Nächste ca.", next_date.strftime("%d.%m."))
    else:
        m2.info("Ab 2 Einträgen")

    # --- B. DIAGRAMME (Grau) ---
    st.divider()
    warm_gray = "#8C837E"

    st.markdown("### Häufigkeit nach Jahr")
    y_counts = df['Jahr'].value_counts().sort_index().reset_index()
    y_counts.columns = ['Jahr', 'Anzahl']
    st.bar_chart(y_counts.set_index('Jahr'), color=warm_gray)

    st.markdown("### Häufigkeit nach Wochentag")
    w_order = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']
    wd_counts = df['Wochentag'].value_counts().reindex(w_order).fillna(0).reset_index()
    wd_counts.columns = ['Wochentag', 'Anzahl']
    st.bar_chart(wd_counts.set_index('Wochentag'), color=warm_gray)

    # --- C. HEATMAP ---
    st.markdown("### Heatmap (Muster)")
    if not df.empty:
        heatmap_data = pd.crosstab(df['Wochentag'], df['Monat_Name'])
        m_order = ['Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez']
        e_w = [t for t in w_order if t in heatmap_data.index]
        e_m = [m for m in m_order if m in heatmap_data.columns]
        
        if e_w and e_m:
            h_disp = heatmap_data.reindex(index=e_w, columns=e_m).fillna(0)
            st.dataframe(h_disp.style.background_gradient(cmap="Reds", axis=None).format("{:.0f}"), use_container_width=True)

    with st.expander("Alle Einträge"):
        st.dataframe(df[['event_date', 'event_name', 'notes']].sort_values(by='event_date', ascending=False), use_container_width=True)

else:
    st.info("Bitte wähle mindestens ein Jahr aus oder trage Daten ein.")
