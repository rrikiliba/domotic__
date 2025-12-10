import streamlit_analytics as sta
import streamlit as st

sta.start_tracking(load_from_json='streamlit_analytics/data.json')
sta.stop_tracking(show=True, unsafe_password=st.secrets.get('ANALYTICS_PASSWORD', 'admin'), json_location='streamlit_analytics/data.json')