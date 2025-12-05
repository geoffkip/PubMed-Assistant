# Utility functions can go here
import streamlit as st

def init_session_state():
    if 'articles' not in st.session_state:
        st.session_state.articles = []
    if 'rag_engine' not in st.session_state:
        st.session_state.rag_engine = None
