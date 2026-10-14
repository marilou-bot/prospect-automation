import os

import streamlit as st
from dotenv import load_dotenv

load_dotenv()
try:
    for k, v in st.secrets.items():
        if isinstance(v, (str, int, float, bool)):
            os.environ[k] = str(v)   # les Secrets écrasent le .env
except Exception:
    pass
