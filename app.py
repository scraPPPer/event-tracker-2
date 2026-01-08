import streamlit as st
import pandas as pd
from supabase import create_client
import datetime
from datetime import timedelta
import plotly.express as px

# --- SEITE KONFIGURIEREN ---
st.set_page_config(page_title="Event-Tracker", layout="centered")

# CSS Fixes für Design und Mobile
st.markdown("""
    <style>
    h1 { font-size: 1.5rem !important; margin-bottom: 0.5rem; }
    h2 { font-size: 1.2rem !important; margin-top: 1rem; }
    h3 { font-size: 1.0rem !important; color: #666; }
    
    /* Eigener Style für die Metric-Boxen im HTML */
    .metric-container {
        display: flex;
        justify-content: space-between;
        margin-bottom: 10px;
        gap: 10px;
    }
    .metric-box {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 10px;
        width: 48%;
        text-align: center;
    }
    .metric-label { font-size: 0.8rem; color: #555; margin-bottom: 5px; }
    .metric-value { font-size: 1.2rem; font-weight: bold; color: #31333F; }
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

df_raw = run_query()

if not df_raw.empty:
    df_raw['event_date'] = pd.to_datetime(df_raw['event_date'])
    df_raw['Jahr'] = df_raw['event_date'].dt.year
    all_years = sorted(df_raw['Jahr'].unique().tolist())
    current_year = datetime.date.today().year

    st.subheader("Zeitraum wählen")
    
    if "selected_years" not in st.session_state:
        st.session_state.selected_years = [y for y in all_years if y >= (current_year - 2)] or all_years

    col_btn1, col_btn2 = st.columns(2)
    if col_btn1.button("Alle Jahre", use_container_width=True):
        st.session_state.selected_years = all_years
        st.rerun()
    if col_btn2.button("Letzte 3 J.", use_container_width=True):
        three_year_range = [current_year, current_year - 1, current_year - 2]
        st.session_state.selected_years = [y for y in all_years if y in three_year_range]
        st.rerun()

    selected_years = st.multiselect("Jahre anpassen:", options=all_years, key="selected_years")

    if not selected_years:
        st.warning("Bitte wähle Jahre aus.")
        df = pd.DataFrame()
    else:
        df = df_raw[df_raw['Jahr'].isin(selected_years)].copy()
    
    if not df.empty:
        days_de = {'Monday': 'Mo', 'Tuesday': 'Di', 'Wednesday': 'Mi', 'Thursday': 'Do', 'Friday': 'Fr', 'Saturday': 'Sa', 'Sunday': 'So'}
        months_de = {1:'Jan', 2:'Feb', 3:'Mär', 4:'Apr', 5:'Mai', 6: 'Jun', 7:'Jul', 8:'Aug', 9:'Sep', 10:'Okt', 11:'Nov', 12:'Dez'}
        df['Wochentag'] = df['event_date'].dt.day_name().map(days_de)
        df['Monat_Name'] = df['event_date'].dt.month.map(months_de)
        df = df.sort_values(by='event_date')

        # --- A. ANALYSE (ERZWUNGENES LAYOUT ÜBER HTML) ---
        st.subheader("Analyse & Prognose")
        
        total = len(df)
        df['Abstand'] = df['event_date'].diff().dt.days
        
        if total >= 2:
            avg_days = f"{df['Abstand'].mean():.1f} d"
            last_date = df['event_date'].iloc[-1].strftime("%d.%m.")
            next_date = (df['event_date'].iloc[-1] + timedelta(days=df['Abstand'].mean())).strftime("%d.%m.")
            
            # Hier erzwingen wir das 2x2 Gitter mit HTML
            st.markdown(f"""
                <div class="metric-container">
                    <div class="metric-box"><div class="metric-label">Gesamt</div><div class="metric-value">{total}</div></div>
                    <div class="metric-box"><div class="metric-label">Ø Abstand</div><div class="metric-value">{avg_days}</div></div>
                </div>
                <div class="metric-container">
                    <div class="metric-box"><div class="metric-label">Zuletzt</div><div class="metric-value">{last_date}</div></div>
                    <div class="metric-box"><div class="metric-label">Nächste ca.</div><div class="metric-value">{next_date}</div></div>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.info("Ab 2 Einträgen verfügbar.")

        # --- B. DIAGRAMME ---
        st.divider()
        warm_gray = "#8C837E"

        def create_bar_chart(data, x_col, y_col, is_year_axis=False):
            fig = px.bar(data, x=x_col, y=y_col, text=y_col)
            max_val = data[y_col].max() if not data.empty else 10
            y_range = max_val * 1.3
            fig.update_traces(marker_color=warm_gray, textposition='outside', textfont_size=11)
            fig.update_layout(
                xaxis_title="", yaxis_title="", 
                yaxis=dict(range=[0, y_range], showgrid=False, showticklabels=False),
                xaxis=dict(type='category' if is_year_axis else None, showgrid=False),
                margin=dict(l=10, r=10, t=30, b=10), height=250,
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
            )
            return fig

        st.markdown("### Häufigkeit nach Jahr")
        y_counts = df['Jahr'].value_counts().sort_index().reset_index()
        y_counts.columns = ['Jahr', 'Anzahl']
        st.plotly_chart(create_bar_chart(y_counts, 'Jahr', 'Anzahl', True), use_container_width=True, config={'displayModeBar': False})

        st.markdown("### Ø Abstand nach Jahr (Tage)")
        yearly_avg = df.groupby('Jahr')['Abstand'].mean().reset_index()
        yearly_avg.columns = ['Jahr', 'Abstand']
        yearly_avg['Abstand'] = yearly_avg['Abstand'].round(1)
        if not yearly_avg['Abstand'].dropna().empty:
            st.plotly_chart(create_bar_chart(yearly_avg, 'Jahr', 'Abstand', True), use_container_width=True, config={'displayModeBar': False})

        st.markdown("### Häufigkeit nach Wochentag")
        w_order = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']
        wd_counts = df['Wochentag'].value_counts().reindex(w_order).fillna(0).reset_index()
        wd_counts.columns = ['Wochentag', 'Anzahl']
        st.plotly_chart(create_bar_chart(wd_counts, 'Wochentag', 'Anzahl'), use_container_width=True, config={'displayModeBar': False})

        st.markdown("### Heatmap (Muster)")
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
    st.info("Noch keine Daten vorhanden.")
