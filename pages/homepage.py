import streamlit as st
from utils import Cache

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
        st.subheader("📑 Analyze Bill", anchor=False)
        with st.container(border=False, height=120, vertical_alignment="center"):
            st.write("Upload your electricity bill to extract data and get a detailed breakdown of your costs.")
        if st.button("Go to Analysis", key="btn_analyze", use_container_width=True):
            navigate_to("pages/analyze.py")

with row1_col2:
    with st.container(border=True):
        st.subheader("💬 Chat with Domitico", anchor=False)
        with st.container(border=False, height=120, vertical_alignment="center"):
            st.write("Have questions about energy tariffs or your consumption? Chat with our AI assistant.")
        if st.button("Start Chat", key="btn_chat", use_container_width=True):
            navigate_to("pages/chat.py")

# --- Row 2 ---
with row2_col1:
    with st.container(border=True):
        st.subheader("📊 Offers Overview", anchor=False)
        with st.container(border=False, height=120, vertical_alignment="center"):
            st.write("""Visualize the offers available to you, and compare them directly.""")
        if st.button("View Data", key="btn_overview", use_container_width=True):
            navigate_to("pages/overview.py")

with row2_col2:
    with st.container(border=True):
        st.subheader("🏠 Smart Home", anchor=False)
        with st.container(border=False, height=120, vertical_alignment="center"):
            st.write("Check the energy consumption of your smart home devices, and optimize usage.")
        if st.button("Smart Dashboard", key="btn_smart", use_container_width=True):
            navigate_to("pages/smart_home.py")