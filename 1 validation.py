import random
import re
import time

import pandas as pd
import streamlit as st

from config import load_env
load_env()

import db
import emailer

st.set_page_config(page_title="Validation des emails", page_icon="✉️", layout="wide")
st.title("✉️ Validation des emails")

if db.client() is None:
    st.error("Supabase n'est pas configuré (SUPABASE_URL / SUPABASE_KEY).")
    st.stop()

EMAIL_OK = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
label = lambda r: f"{r['name']} · {r.get('city') or ''} · {r.get('booking_engine')} · {r.get('reviews_count')} avis"

c = st.columns(4)
c[0].metric("À relire", db.count_status("draft"))
c[1].metric("Validés (prêts)", db.count_status("approved"))
c[2].metric("Envoyés", db.count_status("sent"))
c[3].metric("Envoyés aujourd'hui", db.count_sent_today())

tab_draft, tab_send, tab_done = st.tabs(["1 · Relire", "2 · Envoyer", "3 · Historique"])

# ---------------- 1. Relecture ----------------
with tab_draft:
    if st.button("Générer les brouillons des nouveaux prospects"):
        new = [r for r in db.fetch("new", 500) if r.get("booking_engine") and r.get("emails")]
        for r in new:
            subject, body = emailer.render(r)
            db.update(r["id"], {"email_to": r["emails"][0], "email_subject": subject,
                                "email_body": body, "status": "draft"})
        st.success(f"{len(new)} brouillons créés.")
        st.rerun()

    drafts = db.fetch("draft")
    if not drafts:
        st.info("Aucun brouillon à relire.")
    for r in drafts:
        with st.expander(label(r)):
            st.caption(f"Site : {r.get('website')} · Preuve moteur : {r.get('engine_evidence')}")
            with st.form(f"f_{r['id']}"):
                to = st.text_input("Destinataire", r.get("email_to") or "")
                if len(r.get("emails") or []) > 1:
                    st.caption("Autres adresses trouvées : " + ", ".join(r["emails"][1:]))
                subj = st.text_input("Objet", r.get("email_subject") or "")
                body = st.text_area("Message", r.get("email_body") or "", height=380)
                b1, b2, b3, _ = st.columns([1, 1, 1, 4])
                save = b1.form_submit_button("💾 Enregistrer")
                ok = b2.form_submit_button("✅ Valider")
                no = b3.form_submit_button("❌ Rejeter")
            fields = {"email_to": to.strip(), "email_subject": subj, "email_body": body}
            if save:
                db.update(r["id"], fields)
                st.toast("Enregistré")
            elif ok:
                if not EMAIL_OK.match(to.strip()):
                    st.error("Adresse du destinataire invalide.")
                else:
                    db.update(r["id"], {**fields, "status": "approved"})
                    st.rerun()
            elif no:
                db.update(r["id"], {"status": "rejected"})
                st.rerun()

# ---------------- 2. Envoi ----------------
with tab_send:
    approved = db.fetch("approved")
    st.write(f"**{len(approved)}** emails validés en attente d'envoi.")
    if approved:
        st.dataframe(pd.DataFrame([{"Restaurant": r["name"], "À": r["email_to"], "Objet": r["email_subject"]}
                                   for r in approved]), use_container_width=True, hide_index=True)

    st.divider()
    me = emailer.sender_address()
    if st.button(f"📨 M'envoyer un email de test ({me or 'SMTP non configuré'})", disabled=not (approved and me)):
        try:
            r = approved[0]
            emailer.send_email(me, "[TEST] " + r["email_subject"], r["email_body"])
            st.success("Test envoyé : vérifie ta boîte de réception.")
        except Exception as e:
            st.error(f"Échec : {e}")

    limit = st.number_input("Limite d'envois par jour", 1, 100, 20)
    remaining = max(0, limit - db.count_sent_today())
    st.caption(f"Il reste **{remaining}** envois possibles aujourd'hui. Un délai aléatoire de 8 à 20 s sépare chaque mail.")
    confirm = st.checkbox(f"Je confirme l'envoi de {min(remaining, len(approved))} emails validés")
    if st.button("🚀 Envoyer", type="primary", disabled=not (confirm and approved and remaining)):
        batch = approved[:remaining]
        bar = st.progress(0.0)
        for i, r in enumerate(batch, 1):
            try:
                emailer.send_email(r["email_to"], r["email_subject"], r["email_body"])
                db.update(r["id"], {"status": "sent", "sent_at": pd.Timestamp.utcnow().isoformat(), "send_error": None})
            except Exception as e:
                db.update(r["id"], {"status": "error", "send_error": str(e)[:300]})
            bar.progress(i / len(batch), text=f"{i}/{len(batch)} · {r['name']}")
            if i < len(batch):
                time.sleep(random.uniform(8, 20))
        st.success("Terminé.")
        st.rerun()

# ---------------- 3. Historique ----------------
with tab_done:
    done = db.fetch(["sent", "error"])
    if done:
        st.dataframe(pd.DataFrame([{"Restaurant": r["name"], "À": r["email_to"], "Statut": r["status"],
                                    "Envoyé le": r.get("sent_at"), "Erreur": r.get("send_error")} for r in done]),
                     use_container_width=True, hide_index=True)
    else:
        st.info("Rien d'envoyé pour l'instant.")
