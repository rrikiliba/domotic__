import streamlit as st
from utils import get_user_cache
import streamlit_analytics as sta

cache = get_user_cache()

if 'homepage_visited' not in cache:
    cache['homepage_visited'] = False

def navigate_to(page_path):
    cache['homepage_visited'] = True
    
    sta.stop_tracking(save_to_json='streamlit_analytics/data.json')
    try:
        st.switch_page(page_path)
    except Exception:
        st.rerun()

row1_col1, row1_col2 = st.columns(2, gap="medium")
row2_col1, row2_col2 = st.columns(2, gap="medium")

with row1_col1:
    with st.container(border=True):
        st.subheader("📑 :green[La tua bolletta]", anchor=False)
        with st.container(border=False, height=120, vertical_alignment="center"):
            st.write("Carica la tua :green[bolletta elettrica] per estrarre i dati e ottenere un'analisi dettagliata dei :green[tuoi costi].")
        if st.button("Vai all'Analisi", type="primary", key="btn_analyze", width="stretch"):
            navigate_to("pages/analyze.py")

with row1_col2:
    with st.container(border=True):
        st.subheader("💬 :green[Chatta con Domitico]", anchor=False)
        with st.container(border=False, height=120, vertical_alignment="center"):
            st.write("Hai :green[domande] sulle tariffe energetiche o sui tuoi consumi? Parla con :blue[Domitico] 🧙‍♂️, il nostro assistente AI.")
        if st.button("Inizia una Chat", type="primary", key="btn_chat", width="stretch"):
            navigate_to("pages/chat.py")

with row2_col1:
    with st.container(border=True):
        st.subheader("📊 :green[Le offerte per te]", anchor=False)
        with st.container(border=False, height=120, vertical_alignment="center"):
            st.write(""":green[Visualizza] le offerte a tua disposizione e :green[confrontale] direttamente.""")
        if st.button("Vedi le offerte", type="primary", key="btn_overview", width="stretch"):
            navigate_to("pages/overview.py")

with row2_col2:
    with st.container(border=True):
        st.subheader("🏠 :green[Smart Home]", anchor=False)
        with st.container(border=False, height=120, vertical_alignment="center"):
            st.write("Controlla il :green[consumo energetico] dei tuoi :green[dispositivi smart] e ottimizzane l'utilizzo.")
        if st.button("Smart Dashboard", type="primary", key="btn_smart", width="stretch"):
            navigate_to("pages/smart_home.py")