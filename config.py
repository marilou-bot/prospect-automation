import os


def load_env():
    """Charge .env en local, ou les Secrets Streamlit en ligne."""
    from dotenv import load_dotenv
    load_dotenv()
    try:
        import streamlit as st
        for k, v in st.secrets.items():
            os.environ.setdefault(k, str(v))
    except Exception:
        pass
