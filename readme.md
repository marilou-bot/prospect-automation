# Resto Prospector (prototype)

## Installation
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # puis remplir les clés
streamlit run app.py
```
1. Supabase : coller `schema.sql` puis `schema_v2.sql` dans SQL Editor.
2. Google Cloud : activer « Places API (New) » et créer une clé.
3. Messagerie : créer un mot de passe d'application (Gmail : compte Google > Sécurité > Validation en 2 étapes > Mots de passe des applications).
4. Déploiement : push sur GitHub, puis Streamlit Community Cloud (clés dans *Secrets*).

## Pipeline
Page principale : Google Places (avis ≥ seuil) → scan du site (moteur + emails) → Supabase.
Page « Validation » : brouillons depuis `email_template.txt` → relecture/validation → test → envoi (limite quotidienne).

Le template se modifie dans `email_template.txt` ({moteur} et {salutation} sont remplacés automatiquement).
