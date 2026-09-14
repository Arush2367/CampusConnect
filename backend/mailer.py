"""Transactional email delivery for Campus Connect OTP verification."""
import os, smtplib, ssl, json
from datetime import datetime, timezone
from email.message import EmailMessage
from backend.config import ROOT  # loads project .env before reading SMTP settings

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = ""
SMTP_APP_PASSWORD = ""
SMTP_FROM_NAME = "Campus Connect"

def _smtp_settings():
    """Read SMTP settings at call time so deployment/local env changes take effect."""
    username = os.environ.get("CAMPUSCONNECT_SMTP_USERNAME", os.environ.get("SMTP_EMAIL", "")).strip()
    app_password = os.environ.get("CAMPUSCONNECT_SMTP_APP_PASSWORD", os.environ.get("SMTP_APP_PASSWORD", "")).replace(" ", "").strip()
    host = os.environ.get("CAMPUSCONNECT_SMTP_HOST", os.environ.get("SMTP_HOST", SMTP_HOST)).strip()
    port = int(os.environ.get("CAMPUSCONNECT_SMTP_PORT", os.environ.get("SMTP_PORT", str(SMTP_PORT))))
    from_name = os.environ.get("CAMPUSCONNECT_SMTP_FROM_NAME", os.environ.get("SMTP_FROM_NAME", SMTP_FROM_NAME)).strip() or SMTP_FROM_NAME
    return host, port, username, app_password, from_name

def send_otp_email(recipient, otp):
    if os.environ.get("CAMPUSCONNECT_EMAIL_MODE","smtp").strip().lower()=="test":
        outbox=os.path.join(os.path.dirname(os.path.dirname(__file__)),"data","test_email_outbox.jsonl")
        os.makedirs(os.path.dirname(outbox),exist_ok=True)
        with open(outbox,"a",encoding="utf-8") as fh:
            fh.write(json.dumps({"to":recipient,"otp":otp,
                                 "created_at":datetime.now(timezone.utc).isoformat(timespec="seconds")})+"\n")
        return

    host, port, username, app_password, from_name = _smtp_settings()
    if not username or not app_password:
        raise RuntimeError("Email verification is not configured. Add CAMPUSCONNECT_SMTP_USERNAME and CAMPUSCONNECT_SMTP_APP_PASSWORD (or SMTP_EMAIL and SMTP_APP_PASSWORD) to .env.")

    msg=EmailMessage()
    msg["Subject"]="Campus Connect — Your verification code"
    msg["From"]=f"{from_name} <{username}>"; msg["To"]=recipient
    msg.set_content(f"Your Campus Connect verification code is {otp}.\n\nThis code expires in 5 minutes and can be used once.\nIf you did not request this code, you can ignore this email.\n\nCampus Connect")
    msg.add_alternative(f"""<!doctype html><html><body style="font-family:Arial,sans-serif;background:#f7f1e8;padding:32px">
      <div style="max-width:560px;margin:auto;background:#fffdf8;border:1px solid #e7ded1;border-radius:20px;padding:28px;box-shadow:0 12px 30px rgba(67,47,35,.08)">
        <h2 style="margin:0 0 10px;color:#5b4637">Verify your Campus Connect email</h2>
        <p style="color:#786b60;margin:0 0 22px">Use the verification code below to finish creating your account.</p>
        <div style="font-size:34px;letter-spacing:10px;font-weight:800;color:#b96550;background:#fbf2ee;border-radius:16px;padding:18px;text-align:center">{otp}</div>
        <p style="color:#786b60;font-size:13px;margin:20px 0 0">This code expires in 5 minutes and can be used once.</p>
      </div></body></html>""",subtype="html")
    with smtplib.SMTP(host,port,timeout=20) as smtp:
        smtp.ehlo(); smtp.starttls(context=ssl.create_default_context()); smtp.ehlo()
        smtp.login(username,app_password); smtp.send_message(msg)
