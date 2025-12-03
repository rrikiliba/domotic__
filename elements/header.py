import streamlit as st

def load():
    with st.container(border=True):
        st.title("Benvenuto in :green[Domotic] 💡", anchor=None, help=None)
        st.subheader("Il tuo portale per il :green[**monitoraggio energetico**], l'analisi delle :green[bollette] e molto altro!")
        st.space()
    st.markdown("---")