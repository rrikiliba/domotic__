import streamlit as st

def load():
    with st.container(border=True):
        cols = st.columns([0.3, 0.7], vertical_alignment="center")
        with cols[0]:    
            st.image("assets/images/logo.png", clamp=True, width="stretch")
        with cols[1]:
            st.subheader("Benvenuto in :green[Domotic]", anchor=False, help=None)
            st.write("Il tuo portale per il :green[**monitoraggio energetico**], l'analisi delle :green[bollette] e molto altro!")
        st.space()
    st.markdown("---")