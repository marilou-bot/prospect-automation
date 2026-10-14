"""Stockage Supabase."""
import os
from datetime import datetime, timezone
from supabase import create_client

_client = None

def fetch_all(limit: int = 1000) -> list[dict]:
    sb = client()
    if sb is None:
        raise RuntimeError("SUPABASE_URL / SUPABASE_KEY manquants")
    return sb.table("restaurants").select("*").order("reviews_count", desc=True).limit(limit).execute().data
    
def client():
    global _client
    if _client is None:
        url, key = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY")
        if not url or not key:
            return None
        _client = create_client(url, key)
    return _client


def save_restaurants(rows: list[dict]) -> int:
    sb = client()
    if sb is None:
        raise RuntimeError("SUPABASE_URL / SUPABASE_KEY manquants")
    now = datetime.now(timezone.utc).isoformat()
    payload = []
    for r in rows:
        payload.append({
            "dedupe_key": r["dedupe_key"], "name": r["name"], "city": r.get("city"),
            "address": r.get("address"), "website": r.get("website"), "phone": r.get("phone"),
            "rating": r.get("rating"), "reviews_count": r.get("reviews_count"),
            "booking_engine": r.get("booking_engine"), "engine_evidence": r.get("engine_evidence"),
            "emails": r.get("emails") or [], "contact_page": r.get("contact_page"), "scanned_at": now,
        })
    if payload:
        # le statut n'est pas dans le payload : un restaurant déjà traité garde son statut
        sb.table("restaurants").upsert(payload, on_conflict="dedupe_key").execute()
    return len(payload)


def fetch(status: str | list[str], limit: int = 300) -> list[dict]:
    q = client().table("restaurants").select("*")
    q = q.in_("status", status) if isinstance(status, list) else q.eq("status", status)
    return q.order("reviews_count", desc=True).limit(limit).execute().data


def update(row_id: str, fields: dict) -> None:
    client().table("restaurants").update(fields).eq("id", row_id).execute()


def count_status(status: str) -> int:
    return client().table("restaurants").select("id", count="exact").eq("status", status).limit(1).execute().count or 0


def count_sent_today() -> int:
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    res = client().table("restaurants").select("id", count="exact").eq("status", "sent").gte("sent_at", start).limit(1).execute()
    return res.count or 0
