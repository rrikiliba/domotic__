import streamlit as st

def load():
    with st.container(border=True):
        st.subheader("Benvenuto in :green[Domotic] 💡", anchor=False, help=None)
        st.write("Il tuo portale per il :green[**monitoraggio energetico**], l'analisi delle :green[bollette] e molto altro!")
        st.space()
    st.markdown("---")