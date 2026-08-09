import sqlite3
import smtplib
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "vilouraai1@gmail.com"
SENDER_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
DB_PATH = "/home/ubuntu/email-agent/leads.db"

def validate_environment():
    print("==================================================")
    print("       VILOURAAI OUTREACH PRE-FLIGHT CHECK        ")
    print("==================================================")
    
    success = True

    # 1. Check SMTP Password Environment Variable
    if not SENDER_PASSWORD:
        logging.error("❌ GMAIL_APP_PASSWORD environment variable is NOT set!")
        success = False
    else:
        logging.info("✅ GMAIL_APP_PASSWORD environment variable is set.")

    # 2. Check Database Existence & Schema
    if not os.path.exists(DB_PATH):
        logging.error(f"❌ Database not found at {DB_PATH}")
        success = False
    else:
        logging.info(f"✅ Database found at {DB_PATH}")
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Check table structure
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='leads';")
            if not cursor.fetchone():
                logging.error("❌ 'leads' table does not exist in the database.")
                success = False
            else:
                logging.info("✅ 'leads' table verified.")
                
                # Check pending leads count
                cursor.execute("SELECT COUNT(*) as cnt FROM leads WHERE email IS NOT NULL AND email != '' AND status = 'new'")
                row = cursor.fetchone()
                pending_count = row["cnt"] if row else 0
                logging.info(f"📊 Pending leads ready for outreach: {pending_count}")
                
            conn.close()
        except Exception as e:
            logging.error(f"❌ Database validation error: {e}")
            success = False

    # 3. Test SMTP Connection & Authentication
    if SENDER_PASSWORD:
        logging.info("🔌 Testing SMTP connection to Gmail...")
        try:
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.quit()
            logging.info("✅ SMTP Connection and Authentication successful!")
        except Exception as e:
            logging.error(f"❌ SMTP Authentication failed: {e}")
            success = False

    print("==================================================")
    if success:
        print("🚀 ALL PRE-FLIGHT CHECKS PASSED! Ready to run outreach.")
        print("==================================================")
        return True
    else:
        print("⚠️  PRE-FLIGHT CHECKS FAILED. Please fix issues above.")
        print("==================================================")
        return False

if __name__ == "__main__":
    validate_environment()
