from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional, List
import sqlite3
import hashlib
import jwt
from datetime import datetime, timedelta

SECRET_KEY = "vilouraai-super-secret-key-change-in-production"
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

app = FastAPI(title="VilouraAI Core Registry & Marketplace API", version="1.0.0")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

DB_PATH = "/home/ubuntu/email-outreach/viloura.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hash_password(plain_password) == hashed_password

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_developer(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM developers WHERE email = ?", (email,))
    developer = cursor.fetchone()
    conn.close()
    if developer is None:
        raise credentials_exception
    return developer

# --- Pydantic Models ---
class DeveloperRegister(BaseModel):
    email: str
    password: str
    company_name: Optional[str] = None

class AgentCreate(BaseModel):
    name: str
    description: str
    capabilities: str
    api_endpoint: str
    pricing_model: str  # e.g., 'Free', 'Pay-per-call', 'Subscription'
    category: str       # e.g., 'Customer Support', 'Data Analysis', 'Automation'

class AgentResponse(AgentCreate):
    id: int
    developer_id: int
    status: str
    created_at: str

# --- Authentication Endpoints ---
@app.post("/register", status_code=status.HTTP_201_CREATED)
def register_developer(dev: DeveloperRegister):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM developers WHERE email = ?", (dev.email,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_pw = hash_password(dev.password)
    cursor.execute(
        "INSERT INTO developers (email, hashed_password, company_name) VALUES (?, ?, ?)",
        (dev.email, hashed_pw, dev.company_name)
    )
    conn.commit()
    conn.close()
    return {"message": "Developer registered successfully. You can now log in."}

@app.post("/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM developers WHERE email = ?", (form_data.username,))
    dev = cursor.fetchone()
    conn.close()
    
    if not dev or not verify_password(form_data.password, dev["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": dev["email"]})
    return {"access_token": access_token, "token_type": "bearer"}

# --- Marketplace & Agent Registry Endpoints ---
@app.get("/agents", response_model=List[AgentResponse])
def list_public_agents(category: Optional[str] = None):
    conn = get_db()
    cursor = conn.cursor()
    if category:
        cursor.execute("SELECT * FROM agents WHERE status = 'active' AND category = ?", (category,))
    else:
        cursor.execute("SELECT * FROM agents WHERE status = 'active'")
    agents = cursor.fetchall()
    conn.close()
    return [dict(row) for row in agents]

@app.post("/agents", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
def register_agent(agent: AgentCreate, current_dev = Depends(get_current_developer)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO agents (developer_id, name, description, capabilities, api_endpoint, pricing_model, category, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'active')""",
        (current_dev["id"], agent.name, agent.description, agent.capabilities, agent.api_endpoint, agent.pricing_model, agent.category)
    )
    conn.commit()
    agent_id = cursor.lastrowid
    cursor.execute("SELECT * FROM agents WHERE id = ?", (agent_id,))
    new_agent = cursor.fetchone()
    conn.close()
    return dict(new_agent)

@app.get("/developer/agents", response_model=List[AgentResponse])
def get_my_agents(current_dev = Depends(get_current_developer)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM agents WHERE developer_id = ?", (current_dev["id"],))
    agents = cursor.fetchall()
    conn.close()
    return [dict(row) for row in agents]
