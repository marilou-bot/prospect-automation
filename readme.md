# Resto Prospector (prototype)

## Installation
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # puis remplir les clés
streamlit run app.py
```
1. Supabase : coller `schema.sql` dans SQL Editor.
2. Google Cloud : activer « Places API (New) » et créer une clé.
3. Déploiement : push sur GitHub, puis Streamlit Community Cloud (clés dans *Secrets*).

## Pipeline
Google Places (avis ≥ seuil) → scan du site (moteur de résa + emails) → filtre → Supabase.
Étape 2 (à venir) : emails de démarchage via Resend.
