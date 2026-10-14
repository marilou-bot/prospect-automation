"""Comprend une demande en langage naturel -> paramètres de recherche."""
import json
import os
import re

ENGINE_NAMES = ["Zenchef", "TheFork", "SevenRooms", "CoverManager", "OpenTable"]


def _fallback(text: str) -> dict:
    m = re.search(r"\b(?:à|a|sur|dans|in)\s+([A-Za-zÀ-ÿ' \-]+)", text)
    city = (m.group(1) if m else text).strip(" .?!")
    return {"city": city, "min_reviews": None, "engines": None, "max_results": None}


def parse_request(text: str) -> dict:
    if not os.getenv("ANTHROPIC_API_KEY"):
        return _fallback(text)
    try:
        import anthropic
        resp = anthropic.Anthropic().messages.create(
            model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5"),
            max_tokens=300,
            system=(
                "Tu extrais des paramètres de recherche de restaurants en France. Réponds UNIQUEMENT "
                'avec un JSON : {"city": str, "min_reviews": int|null, "engines": [str]|null, '
                '"max_results": int|null}. engines ⊂ ' + str(ENGINE_NAMES) + ". "
                "Mets null si l'utilisateur ne précise pas."
            ),
            messages=[{"role": "user", "content": text}],
        )
        raw = "".join(b.text for b in resp.content if b.type == "text")
        return json.loads(re.sub(r"```json|```", "", raw).strip())
    except Exception:
        return _fallback(text)
