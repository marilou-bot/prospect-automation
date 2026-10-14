"""Recherche de restaurants via Google Places API (New)."""
import os
import requests

from quota import consume

consume(1)
response = requests.post(url, ...)

URL = "https://places.googleapis.com/v1/places:searchText"
FIELDS = ",".join([
    "places.id", "places.displayName", "places.formattedAddress", "places.rating",
    "places.userRatingCount", "places.websiteUri", "places.nationalPhoneNumber", "nextPageToken",
])


def search_restaurants(city: str, max_results: int = 60, query_suffix: str = "restaurant") -> list[dict]:
    key = os.getenv("GOOGLE_PLACES_API_KEY")
    if not key:
        raise RuntimeError("GOOGLE_PLACES_API_KEY manquante")
    headers = {"X-Goog-Api-Key": key, "X-Goog-FieldMask": FIELDS, "Content-Type": "application/json"}
    body = {"textQuery": f"{query_suffix} {city}, France", "includedType": "restaurant",
            "languageCode": "fr", "regionCode": "FR", "pageSize": 20}
    results = []
    while len(results) < max_results:
        r = requests.post(URL, headers=headers, json=body, timeout=20)
        r.raise_for_status()
        data = r.json()
        for p in data.get("places", []):
            results.append({
                "dedupe_key": p["id"],
                "name": p.get("displayName", {}).get("text", ""),
                "address": p.get("formattedAddress"),
                "city": city,
                "website": p.get("websiteUri"),
                "phone": p.get("nationalPhoneNumber"),
                "rating": p.get("rating"),
                "reviews_count": p.get("userRatingCount", 0),
            })
        token = data.get("nextPageToken")
        if not token:
            break
        body["pageToken"] = token
    return results[:max_results]
