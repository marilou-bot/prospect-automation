import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import bootstrap  # noqa: F401  (charge .env + secrets, doit rester avant db/places)
import pandas as pd
import streamlit as st

import db
import quota
from nlu import ENGINE_NAMES, parse_request
from places import search_restaurants
from scanner import scan_site

st.set_page_config(page_title="Resto Prospector", page_icon="🍽️", layout="wide")
st.title("🍽️ Resto Prospector")
st.caption("Trouve des restaurants à fort volume d'avis, détecte leur moteur de réservation et leurs contacts.")

ASSETS = Path(__file__).parent / "assets"


def avatar(role: str):
    """Photo si le fichier existe, sinon avatar par défaut de Streamlit."""
    f = ASSETS / ("user.png" if role == "user" else "assistant.png")
    return str(f) if f.exists() else None


# ---------- Compteur de quota ----------
def render_quota(slot):
    with slot.container():
        try:
            u = quota.get_usage()
        except Exception as e:
            st.warning(f"Compteur de quota indisponible : {e}")
            return
        if u is None:
            st.warning("Supabase non configuré : le compteur de quota est indisponible.")
            return
        c1, c2 = st.columns(2)
        c1.metric("Requêtes Google ce mois-ci", f"{u['month']} / {quota.MONTHLY_LIMIT}")
        c2.metric("Requêtes aujourd'hui", f"{u['day']} / {quota.DAILY_LIMIT}")
        st.progress(min(u["month"] / quota.MONTHLY_LIMIT, 1.0))
        if u["month"] >= quota.MONTHLY_LIMIT:
            st.error("Limite mensuelle atteinte : les recherches Google sont bloquées jusqu'au mois prochain.")
        elif u["day"] >= quota.DAILY_LIMIT:
            st.warning("Limite quotidienne atteinte : réessaie demain.")


quota_slot = st.empty()
render_quota(quota_slot)

# ---------- Barre latérale : critères ----------
with st.sidebar:
    st.header("Critères")
    min_reviews = st.number_input("Avis Google minimum", 0, 50000, 1000, step=100)
    engines = st.multiselect("Moteurs de réservation ciblés", ENGINE_NAMES, default=ENGINE_NAMES)
    max_results = st.slider("Restaurants analysés par recherche", 20, 120, 40, step=20)
    st.divider()
    st.subheader("Ou importer ta liste (CSV)")
    st.caption("Colonnes : name, website, reviews_count (+ optionnel address, city, rating)")
    csv = st.file_uploader("CSV", type="csv", label_visibility="collapsed")
    run_csv = st.button("Analyser le CSV", disabled=csv is None)

if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant",
        "content": "Bonjour ! Dis-moi où chercher, par ex. **« restaurants à Lyon »** ou "
                   "**« Bordeaux, plus de 1500 avis, uniquement Zenchef et TheFork »**.",
    }]
if "results" not in st.session_state:
    st.session_state.results = None

for m in st.session_state.messages:
    with st.chat_message(m["role"], avatar=avatar(m["role"])):
        st.markdown(m["content"])


# ---------- Pipeline ----------
def run_pipeline(rows, min_rev, eng_filter, status):
    status.write(f"{len(rows)} restaurants récupérés")
    kept = [r for r in rows if (r.get("reviews_count") or 0) >= min_rev]
    status.write(f"{len(kept)} avec ≥ {min_rev} avis Google")

    status.write("Analyse des sites web (moteur de réservation + emails)…")
    with ThreadPoolExecutor(max_workers=8) as ex:
        scans = list(ex.map(lambda r: scan_site(r.get("website")), kept))
    for r, s in zip(kept, scans):
        r.update(s)

    final = [r for r in kept if r.get("booking_engine") in eng_filter]
    status.write(f"{len(final)} utilisent un des moteurs ciblés")
    return final


def show_and_store(final):
    st.session_state.results = final
    if not final:
        return "Aucun restaurant ne correspond à ces critères. Essaie d'élargir (moins d'avis, autre ville, plus de moteurs)."
    with_mail = sum(1 for r in final if r.get("emails"))
    return f"**{len(final)} restaurants** correspondent, dont **{with_mail}** avec au moins un email trouvé."


def autosave(final):
    """Enregistre automatiquement les résultats dans Supabase."""
    if not final:
        return ""
    try:
        n = db.save_restaurants(final)
        return f" {n} enregistrés dans la base (page *Restaurants*)."
    except Exception as e:
        return f" ⚠️ Sauvegarde Supabase impossible : {e}"


def prospects_df(final):
    df = pd.DataFrame(final)
    cols = ["name", "city", "reviews_count", "rating", "booking_engine", "emails", "website", "phone", "engine_evidence"]
    df = df[[c for c in cols if c in df.columns]].copy()
    if "emails" in df:
        df["emails"] = df["emails"].apply(lambda x: ", ".join(x) if isinstance(x, list) else x)
    return df.sort_values("reviews_count", ascending=False)


# ---------- Chat ----------
prompt = st.chat_input("Où veux-tu chercher ?")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar=avatar("user")):
        st.markdown(prompt)
    with st.chat_message("assistant", avatar=avatar("assistant")):
        p = parse_request(prompt)
        mr = p.get("min_reviews") or min_reviews
        eng = p.get("engines") or engines
        mx = p.get("max_results") or max_results
        city = p.get("city") or prompt
        with st.status(f"Recherche : {city} · ≥{mr} avis · {', '.join(eng)}", expanded=True) as status:
            try:
                rows = search_restaurants(city, max_results=mx)
                final = run_pipeline(rows, mr, eng, status)
                reply = show_and_store(final) + autosave(final)
                status.update(label="Terminé", state="complete")
            except Exception as e:
                reply, final = f"❌ Erreur : {e}", None
                status.update(label="Erreur", state="error")
        st.markdown(reply)
    st.session_state.messages.append({"role": "assistant", "content": reply})
    render_quota(quota_slot)  # met à jour le compteur après la recherche

if run_csv and csv is not None:
    df_in = pd.read_csv(csv)
    rows = []
    for _, r in df_in.iterrows():
        site = str(r.get("website") or "")
        rows.append({
            "dedupe_key": site or str(r["name"]), "name": str(r["name"]),
            "website": site or None, "reviews_count": int(r.get("reviews_count") or 0),
            "address": r.get("address"), "city": r.get("city"), "rating": r.get("rating"),
        })
    with st.status("Analyse du CSV…", expanded=True) as status:
        final = run_pipeline(rows, min_reviews, engines, status)
        status.update(label="Terminé", state="complete")
    st.session_state.messages.append({"role": "assistant", "content": show_and_store(final) + autosave(final)})
    st.rerun()

# ---------- Résultats ----------
if st.session_state.results:
    st.subheader("Prospects trouvés")
    df = prospects_df(st.session_state.results)
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.download_button("⬇️ Export CSV", df.to_csv(index=False).encode("utf-8"), "prospects.csv", "text/csv")
