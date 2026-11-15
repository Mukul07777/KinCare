"""Email delivery for reminders and care-circle notices.

Provider order: Resend (RESEND_API_KEY, one HTTPS call, free tier 3,000/month) -> any SMTP server (SMTP_HOST,
e.g. Gmail with an app password, Brevo, SendGrid SMTP) -> "outbox": the email is only recorded, so a laptop demo
shows exactly what would have been sent. Every email is logged in `emails`; the body is encrypted at rest (vault).
"""
import html
import os
import smtplib
import ssl
from email.message import EmailMessage

import requests

import vault

SCHEMA = """
CREATE TABLE IF NOT EXISTS emails (
    id INTEGER PRIMARY KEY,
    to_addr TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT,
    kind TEXT,
    status TEXT NOT NULL,            -- sent | outbox | failed
    provider TEXT,
    provider_id TEXT,
    error TEXT,
    at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_emails_at ON emails(at);
"""

FROM = lambda: os.environ.get("EMAIL_FROM") or "KinCare <onboarding@resend.dev>"  # noqa: E731


def provider() -> str:
    if os.environ.get("RESEND_API_KEY"):
        return "resend"
    if os.environ.get("SMTP_HOST"):
        return "smtp"
    return "outbox"


def _html(subject: str, text: str) -> str:
    """Large type and high contrast: many readers are elders on a phone."""
    body = "<br>".join(html.escape(line) for line in text.splitlines())
    return (f"<div style=\"font-family:Arial,sans-serif;font-size:18px;line-height:1.5;color:#111;max-width:560px\">"
            f"<h2 style=\"font-size:22px;margin:0 0 12px\">{html.escape(subject)}</h2><p>{body}</p>"
            f"<p style=\"font-size:13px;color:#555;margin-top:24px\">Sent by KinCare. You get this because you are part of "
            f"this person's care circle. Ask them to remove you if you no longer help with their care.</p></div>")


def _resend(to: str, subject: str, text: str) -> str:
    r = requests.post("https://api.resend.com/emails", timeout=20,
                      headers={"Authorization": f"Bearer {os.environ['RESEND_API_KEY']}"},
                      json={"from": FROM(), "to": [to], "subject": subject, "text": text, "html": _html(subject, text)})
    r.raise_for_status()
    return r.json().get("id", "")


def _smtp(to: str, subject: str, text: str) -> str:
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = FROM(), to, subject
    msg.set_content(text)
    msg.add_alternative(_html(subject, text), subtype="html")
    host, port = os.environ["SMTP_HOST"], int(os.environ.get("SMTP_PORT") or 587)
    user, pw = os.environ.get("SMTP_USER"), os.environ.get("SMTP_PASSWORD")
    ctx = ssl.create_default_context()
    if port == 465:
        s = smtplib.SMTP_SSL(host, port, context=ctx, timeout=20)
    else:
        s = smtplib.SMTP(host, port, timeout=20)
        s.starttls(context=ctx)
    with s:
        if user:
            s.login(user, pw or "")
        s.send_message(msg)
    return msg.get("Message-ID") or ""


def valid(addr: str | None) -> bool:
    a = (addr or "").strip()
    return 3 < len(a) <= 254 and a.count("@") == 1 and "." in a.split("@")[1] and not any(c in a for c in " <>,;\r\n")


def send(conn, to: str, subject: str, text: str, kind: str = "notice") -> str:
    """Send one email (or record it in the outbox). Never raises: a reminder failing must not stop the others."""
    if not valid(to):
        return "invalid"
    p, status, pid, err = provider(), "outbox", None, None
    try:
        if p == "resend":
            pid, status = _resend(to, subject, text), "sent"
        elif p == "smtp":
            pid, status = _smtp(to, subject, text), "sent"
    except Exception as e:  # network, auth, provider rejected
        status, err = "failed", str(e)[:300]
        print(f"email to {to} failed:", err)
    conn.execute("INSERT INTO emails (to_addr, subject, body, kind, status, provider, provider_id, error) VALUES (?,?,?,?,?,?,?,?)",
                 (to.strip(), subject, vault.seal(text, "emails", "body"), kind, status, p, pid, err))
    return status
