# alert_agent.py

import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# -------------------------------
# CONFIGURATION
# -------------------------------
EMAIL_ADDRESS = "amashiimayav@gmail.com"        # Sender email
EMAIL_PASSWORD = "oyfe jgjh dbxf xwux"          # Gmail app password (not your normal password)
RECIPIENT_EMAIL = "staygoldheaven@gmail.com" # Who will receive alerts

ALERT_FILE = "price_alerts.json"

# -------------------------------
# LOAD ALERTS
# -------------------------------
try:
    with open(ALERT_FILE, "r", encoding="utf-8") as f:
        alerts = json.load(f)
except FileNotFoundError:
    print(f"No alert file found at {ALERT_FILE}.")
    alerts = []

# -------------------------------
# SEND EMAIL FUNCTION
# -------------------------------
def send_email(subject, body):
    msg = MIMEMultipart()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = RECIPIENT_EMAIL
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        print("✅ Email sent successfully!")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

# -------------------------------
# CREATE ALERT MESSAGE
# -------------------------------
if alerts:
    body = "🛒 Price Drop Alerts!\n\n"
    total_savings = 0
    for alert in alerts:
        body += f"- {alert['name']}\n  Current Price: {alert['current_price']}\n  Threshold: {alert['threshold']}\n  Savings: Rs. {alert['savings']:,}\n  Link: {alert['url']}\n\n"
        total_savings += alert["savings"]

    body += f"Total potential savings: Rs. {total_savings:,}"

    send_email("Daraz Price Drop Alerts!", body)
else:
    print("No price alerts found. No email sent.")
