import imaplib
import email
from email.header import decode_header
import sqlite3
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

IMAP_SERVER = "imap.gmail.com"
EMAIL_USER = "vilouraai1@gmail.com"
EMAIL_PASS = os.getenv("GMAIL_APP_PASSWORD", "")
DB_PATH = "/home/ubuntu/email-agent/leads.db"

def check_for_replies():
    if not EMAIL_PASS:
        logging.error("GMAIL_APP_PASSWORD not set. Cannot check for replies.")
        return
    
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")
        
        # Search for unread messages or recent messages from leads
        status, messages = mail.search(None, '(UNSEEN)')
        if status != 'OK':
            logging.info("No new messages found.")
            return

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        for num in messages[0].split():
            res, msg_data = mail.fetch(num, '(DATA)')
            if res != 'OK':
                continue
            
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    from_header = email.utils.parseaddr(msg.get("From"))[1].lower()
                    
                    if from_header:
                        # Check if sender is in our leads database with 'sent' status
                        cursor.execute("SELECT id FROM leads WHERE email = ? AND status = 'sent'", (from_header,))
                        lead = cursor.fetchone()
                        if lead:
                            cursor.execute("UPDATE leads SET status = 'replied' WHERE email = ?", (from_header,))
                            conn.commit()
                            logging.info(f"🎉 Lead replied! Updated status for {from_header} to 'replied'.")

        conn.close()
        mail.logout()
    except Exception as e:
        logging.error(f"Error checking IMAP replies: {e}")

if __name__ == "__main__":
    check_for_replies()
