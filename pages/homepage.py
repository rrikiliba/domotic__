import streamlit as st
from utils import Cache
import streamlit_analytics as sta

cache = Cache()

cache['homepage_visited'] = False

# Helper function to handle navigation from the landing page
def navigate_to(page_path):
    # 1. Update state so main.py knows we are inside the app
    cache['homepage_visited'] = True
    
    # 2. Try to switch to the specific page. 
    # Note: If the page is not currently in the active st.navigation list, 
    # this might raise an error. In that case, we fallback to st.rerun() 
    # which will reload main.py and take the user to the default app page.
    sta.stop_tracking(save_to_json='streamlit_analytics/data.json')
    try:
        st.switch_page(page_path)
    except Exception:
        st.rerun()

# Define the grid layout
row1_col1, row1_col2 = st.columns(2, gap="medium")
row2_col1, row2_col2 = st.columns(2, gap="medium")

# --- Row 1 ---

with row1_col1:
    with st.container(border=True):
        st.subheader("📑 :green[Analizza la tua bolletta]", anchor=False)
        with st.container(border=False, height=120, vertical_alignment="center"):
            st.write("Carica la tua :green[bolletta elettrica] per estrarre i dati e ottenere un'analisi dettagliata dei :green[tuoi costi].")
        if st.button("Vai all'Analisi", type="primary", key="btn_analyze", use_container_width=True):
            navigate_to("pages/analyze.py")

with row1_col2:
    with st.container(border=True):
        st.subheader("💬 :green[Chatta con Domitico]", anchor=False)
        with st.container(border=False, height=120, vertical_alignment="center"):
            st.write("Hai :green[domande] sulle tariffe energetiche o sui tuoi consumi? :green[Parla con il nostro assistente AI].")
        if st.button("Inizia una Chat", type="primary", key="btn_chat", use_container_width=True):
            navigate_to("pages/chat.py")

# --- Row 2 ---
with row2_col1:
    with st.container(border=True):
        st.subheader("📊 :green[Le offerte per te]", anchor=False)
        with st.container(border=False, height=120, vertical_alignment="center"):
            st.write(""":green[Visualizza] le offerte a tua disposizione e :green[confrontale] direttamente.""")
        if st.button("Vedi le offerte", type="primary", key="btn_overview", use_container_width=True):
            navigate_to("pages/overview.py")

with row2_col2:
    with st.container(border=True):
        st.subheader("🏠 :green[Smart Home]", anchor=False)
        with st.container(border=False, height=120, vertical_alignment="center"):
            st.write("Controlla il :green[consumo energetico] dei tuoi :green[dispositivi smart] e ottimizzane l'utilizzo.")
        if st.button("Smart Dashboard", type="primary", key="btn_smart", use_container_width=True):
            navigate_to("pages/smart_home.py")