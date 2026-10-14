import os
from datetime import datetime, timezone

import db

DAILY_LIMIT = int(os.getenv("PLACES_DAILY_LIMIT", 25))


class QuotaExceeded(Exception):
    pass


def consume(n: int = 1) -> None:
    """À appeler AVANT chaque requête Google Places."""
    sb = db.client()
    if sb is None:
        raise RuntimeError("SUPABASE_URL / SUPABASE_KEY manquants : impossible de vérifier le quota")
    today = datetime.now(timezone.utc).date().isoformat()
    rows = sb.table("api_usage").select("count").eq("day", today).execute().data
    used = rows[0]["count"] if rows else 0
    if used + n > DAILY_LIMIT:
        raise QuotaExceeded(
            f"Limite quotidienne atteinte ({used}/{DAILY_LIMIT} requêtes Google Places). "
            "Réessaie demain."
        )
    sb.table("api_usage").upsert({"day": today, "count": used + n}).execute()
