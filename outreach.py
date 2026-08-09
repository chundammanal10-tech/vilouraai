import sqlite3
import smtplib
from email.message import EmailMessage
import time
import os
import logging

logging.basicConfig(
    filename="outreach.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
console.setFormatter(formatter)
logging.getLogger("").addHandler(console)

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "vilouraai1@gmail.com"
SENDER_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "") 
DB_PATH = "/home/ubuntu/email-agent/leads.db"
DELAY_SECONDS = 15

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def send_outreach():
    if not os.path.exists(DB_PATH):
        logging.error(f"Database not found at {DB_PATH}")
        return

    logging.info("Connecting to SMTP server...")
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        logging.info("SMTP Connected successfully.")
    except Exception as e:
        logging.error(f"SMTP Authentication failed: {e}")
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, business_name, email, contact_name 
        FROM leads 
        WHERE email IS NOT NULL AND email != '' AND status = 'new'
    """)
    leads = cursor.fetchall()
    
    total_leads = len(leads)
    logging.info(f"Found {total_leads} pending leads to process.")

    count = 0
    for row in leads:
        lead_id = row["id"]
        name = row["contact_name"] or "Creator"
        email = row["email"]
        company = row["business_name"] or "your team"

        msg = EmailMessage()
        msg["Subject"] = f"Listing AI agents from {company} on VilouraAI"
        msg["From"] = SENDER_EMAIL
        msg["To"] = email
        
        msg.set_content(f"""Hi {name},

I've been following what you're building at {company} and love your work in the AI space. 

I'm reaching out from VilouraAI—we are launching a dedicated marketplace specifically built for developers and creators to showcase, distribute, and monetize autonomous AI agents. 

We are currently onboarding a select group of founding creators ahead of our public push. I'd love to get your agents listed early with zero platform commission for our beta cohort. 

Are you open to checking out a quick preview of how it works?

Best regards,
Jilsha Jose
Founder, VilouraAI
https://vilouraai-landing.pages.dev
""")

        try:
            server.send_message(msg)
            count += 1
            
            cursor.execute("""
                UPDATE leads 
                SET status = 'sent', 
                    last_contacted_at = CURRENT_TIMESTAMP, 
                    contacted_count = contacted_count + 1 
                WHERE id = ?
            """, (lead_id,))
            conn.commit()
            
            logging.info(f"[{count}/{total_leads}] Sent pitch to {email} ({name} at {company}) -> Status updated to 'sent'")
        except Exception as e:
            cursor.execute("""
                UPDATE leads 
                SET status = 'failed', 
                    notes = ? 
                WHERE id = ?
            """, (str(e), lead_id))
            conn.commit()
            logging.error(f"Failed to send to {email}: {e} -> Status updated to 'failed'")

        time.sleep(DELAY_SECONDS)

    server.quit()
    conn.close()
    logging.info(f"Outreach batch complete! Total emails successfully sent: {count}")

if __name__ == "__main__":
    send_outreach()
