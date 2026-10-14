import bootstrap  # noqa: F401
import pandas as pd
import streamlit as st

import db

st.set_page_config(page_title="Restaurants trouvés", page_icon="📋", layout="wide")
st.title("📋 Restaurants déjà trouvés")

try:
    rows = db.fetch_all()
except Exception as e:
    st.error(f"Supabase : {e}")
    st.stop()

if not rows:
    st.info("Aucun restaurant enregistré pour l'instant. Lance une recherche depuis la page principale.")
    st.stop()

df = pd.DataFrame(rows)
if "emails" in df:
    df["emails"] = df["emails"].apply(lambda x: ", ".join(x) if isinstance(x, list) else (x or ""))

# ---------- Filtres ----------
with st.sidebar:
    st.header("Filtres")
    q = st.text_input("Nom contient")
    cities = sorted(df["city"].dropna().unique()) if "city" in df else []
    sel_cities = st.multiselect("Ville", cities)
    engines = sorted(df["booking_engine"].dropna().unique()) if "booking_engine" in df else []
    sel_engines = st.multiselect("Moteur de réservation", engines)
    min_rev = st.number_input("Avis minimum", 0, 50000, 0, step=100)
    only_mail = st.checkbox("Avec email uniquement")

f = df
if q:
    f = f[f["name"].str.contains(q, case=False, na=False)]
if sel_cities:
    f = f[f["city"].isin(sel_cities)]
if sel_engines:
    f = f[f["booking_engine"].isin(sel_engines)]
if min_rev:
    f = f[f["reviews_count"].fillna(0) >= min_rev]
if only_mail and "emails" in f:
    f = f[f["emails"] != ""]

c1, c2, c3 = st.columns(3)
c1.metric("Restaurants en base", len(df))
c2.metric("Après filtres", len(f))
c3.metric("Avec email", int((f["emails"] != "").sum()) if "emails" in f else 0)

cols = ["name", "city", "reviews_count", "rating", "booking_engine", "emails",
        "website", "phone", "status", "scanned_at"]
view = f[[c for c in cols if c in f.columns]]
st.dataframe(
    view,
    use_container_width=True,
    hide_index=True,
    column_config={"website": st.column_config.LinkColumn("website")},
)
st.download_button("⬇️ Export CSV", view.to_csv(index=False).encode("utf-8"), "restaurants.csv", "text/csv")
