"""Génération des brouillons + envoi SMTP depuis ta messagerie."""
import os
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid
from pathlib import Path

TEMPLATE_PATH = Path(__file__).parent / "email_template.txt"
ENGINE_LABELS = {
    "Zenchef": "Zenchef", "TheFork": "TheFork", "SevenRooms": "SevenRooms",
    "CoverManager": "Cover Manager", "OpenTable": "OpenTable",
}


def render(restaurant: dict, contact_name: str | None = None) -> tuple[str, str]:
    """Retourne (objet, corps) à partir du template et du moteur détecté."""
    raw = TEMPLATE_PATH.read_text(encoding="utf-8")
    first, _, body = raw.partition("\n")
    subject = first.removeprefix("Objet:").strip()
    body = body.lstrip("\n")
    engine = ENGINE_LABELS.get(restaurant.get("booking_engine"), restaurant.get("booking_engine") or "")
    salutation = f"Bonjour {contact_name}," if contact_name else "Bonjour Madame, Monsieur,"
    for k, v in {"{moteur}": engine, "{salutation}": salutation}.items():
        subject, body = subject.replace(k, v), body.replace(k, v)
    return subject, body


def sender_address() -> str:
    return os.getenv("SENDER_EMAIL") or os.getenv("SMTP_USER") or ""


def send_email(to: str, subject: str, body: str) -> None:
    host, user, pwd = os.getenv("SMTP_HOST"), os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD")
    if not (host and user and pwd):
        raise RuntimeError("SMTP_HOST / SMTP_USER / SMTP_PASSWORD manquants dans .env")
    port = int(os.getenv("SMTP_PORT", "587"))

    msg = EmailMessage()
    msg["From"] = formataddr((os.getenv("SENDER_NAME", ""), sender_address()))
    msg["To"] = to
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid()
    msg.set_content(body)

    ctx = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(host, port, context=ctx, timeout=30) as s:
            s.login(user, pwd)
            s.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=30) as s:
            s.starttls(context=ctx)
            s.login(user, pwd)
            s.send_message(msg)
