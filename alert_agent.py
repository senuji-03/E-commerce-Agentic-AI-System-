import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict

# -------------------------------
# CONFIGURATION
# -------------------------------
EMAIL_ADDRESS = "amashiimayav@gmail.com"        # Sender email
EMAIL_PASSWORD = "oyfe jgjh dbxf xwux"          # Gmail app password (not your normal password)
RECIPIENT_EMAIL = "staygoldheaven@gmail.com" # Who will receive alerts

ALERT_FILE = "price_alerts.json"

# -------------------------------
# SEND EMAIL FUNCTION
# -------------------------------
def send_email(subject: str, body: str) -> bool:
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
        return True
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False


def build_alert_email_body(alerts: List[Dict]) -> str:
    if not alerts:
        return "No price alerts found."
    body = "🛒 Price Drop Alerts!\n\n"
    total_savings = 0
    for alert in alerts:
        body += (
            f"- {alert['name']}\n"
            f"  Current Price: {alert['current_price']}\n"
            f"  Threshold: {alert['threshold']}\n"
            f"  Savings: Rs. {alert['savings']:,}\n"
            f"  Link: {alert['url']}\n\n"
        )
        total_savings += alert.get("savings", 0)
    body += f"Total potential savings: Rs. {total_savings:,}"
    return body


def send_alerts_from_file(alert_file_path: str = ALERT_FILE) -> bool:
    try:
        with open(alert_file_path, "r", encoding="utf-8") as f:
            alerts = json.load(f)
    except FileNotFoundError:
        print(f"No alert file found at {alert_file_path}.")
        return False
    if not alerts:
        print("No price alerts found. No email sent.")
        return False
    body = build_alert_email_body(alerts)
    return send_email("Daraz Price Drop Alerts!", body)


if __name__ == "__main__":
    # Keep CLI behavior for manual testing
    send_alerts_from_file(ALERT_FILE)
