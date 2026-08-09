from fastapi import FastAPI, HTTPException
import sqlite3
import os

app = FastAPI(title="VilouraAI Core API", version="1.0")

DB_PATH = "/home/ubuntu/email-agent/leads.db"

def get_db_connection():
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=500, detail="Database not found.")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/")
def read_root():
    return {"status": "VilouraAI API is online", "project": "Autonomous AI Agent Marketplace"}

@app.get("/api/leads")
def get_leads(limit: int = 50):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, business_name, category, email, contact_name, status, priority FROM leads LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.get("/api/stats")
def get_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*), SUM(CASE WHEN email IS NOT NULL AND email != '' THEN 1 ELSE 0 END) FROM leads")
    total, with_email = cursor.fetchone()
    conn.close()
    return {
        "total_leads": total,
        "leads_with_email": with_email
    }
