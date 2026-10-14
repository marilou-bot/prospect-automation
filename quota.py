import os
from datetime import date

import db  # adapte selon comment db.py expose le client Supabase

DAILY_LIMIT = int(os.getenv("PLACES_DAILY_LIMIT", 25))


class QuotaExceeded(Exception):
    pass


def consume(n: int = 1) -> None:
    """À appeler AVANT chaque requête Google Places."""
    sb = db.get_client()  # remplace par ton accès au client
    today = date.today().isoformat()
    rows = sb.table("api_usage").select("count").eq("day", today).execute().data
    used = rows[0]["count"] if rows else 0
    if used + n > DAILY_LIMIT:
        raise QuotaExceeded(
            f"Limite quotidienne atteinte ({used}/{DAILY_LIMIT} requêtes Google Places). "
            "Réessaie demain."
        )
    sb.table("api_usage").upsert({"day": today, "count": used + n}).execute()
