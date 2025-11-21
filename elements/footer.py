import streamlit as st
from streamlit_theme import st_theme

def load():
    theme = st_theme(adjust=True)
    st.markdown(f"""<style>
.footer a:link , a:visited{{
color: blue;
background-color: transparent;
text-decoration: underline;
}}

.footer a:hover,  a:active {{
color: red;
background-color: transparent;
text-decoration: underline;
}}

.footer {{
position: fixed;
left: 0;
bottom: 0;
width: 100%;
background-color: {theme['lightenedBg05']};
color: {theme['textColor']};
text-align: center;
padding-top: 25px;
height: 5em;
z-index: 9999;
}}
</style>
<div class="footer">
<p>Questo tool è sviluppato a scopo educativo nell'ambito del corso 
    Innovation and Business ICT presso UniTN.
    I calcoli di risparmio sono stime indicative 
    basate sui dati del Portale Offerte ARERA. Per informazioni ufficiali e vincolanti, 
    consultare direttamente il sito del fornitore o il Portale Offerte ARERA.</p>
</div>
""",unsafe_allow_html=True)