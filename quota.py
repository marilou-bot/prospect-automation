import os
from datetime import datetime, timezone

import db

DAILY_LIMIT = int(os.getenv("PLACES_DAILY_LIMIT", 25))
MONTHLY_LIMIT = int(os.getenv("PLACES_MONTHLY_LIMIT", 900))


class QuotaExceeded(Exception):
    pass


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def get_usage() -> dict | None:
    """Retourne {'day': n, 'month': n}, ou None si Supabase n'est pas configuré."""
    sb = db.client()
    if sb is None:
        return None
    today = _today()
    month_start = today[:8] + "01"
    rows = sb.table("api_usage").select("day,count").gte("day", month_start).execute().data
    return {
        "day": sum(r["count"] for r in rows if r["day"] == today),
        "month": sum(r["count"] for r in rows),
    }


def consume(n: int = 1) -> None:
    """À appeler AVANT chaque requête Google Places."""
    u = get_usage()
    if u is None:
        raise RuntimeError("SUPABASE_URL / SUPABASE_KEY manquants : impossible de vérifier le quota")
    if u["month"] + n > MONTHLY_LIMIT:
        raise QuotaExceeded(f"Limite mensuelle atteinte ({u['month']}/{MONTHLY_LIMIT} requêtes Google Places).")
    if u["day"] + n > DAILY_LIMIT:
        raise QuotaExceeded(f"Limite quotidienne atteinte ({u['day']}/{DAILY_LIMIT} requêtes). Réessaie demain.")
    db.client().table("api_usage").upsert({"day": _today(), "count": u["day"] + n}).execute()
