import os

import streamlit as st
from dotenv import load_dotenv

load_dotenv()
# Streamlit Cloud : les secrets deviennent des variables d'environnement
try:
    for k, v in st.secrets.items():
        os.environ.setdefault(k, str(v))
except Exception:
    pass
