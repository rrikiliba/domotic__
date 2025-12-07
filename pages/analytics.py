import streamlit_analytics as sta

sta.start_tracking(load_from_json='streamlit_analytics/data.json')
sta.stop_tracking(show=True, unsafe_password='apple-business-cream-dread', json_location='streamlit_analytics/data.json')