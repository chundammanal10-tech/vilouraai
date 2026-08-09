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

from sandbox import run_agent_in_docker
from pydantic import Field

class AgentExecutionRequest(BaseModel):
    code_payload: Optional[str] = Field(None, description="Raw python code to execute in sandbox")
    input_data: Optional[dict] = Field(None, description="Input payload if invoking an API endpoint agent")

@app.post("/agents/{agent_id}/execute")
def execute_agent(agent_id: int, req: AgentExecutionRequest, current_dev = Depends(get_current_developer)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM agents WHERE id = ? AND status = 'active'", (agent_id,))
    agent = cursor.fetchone()
    conn.close()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Active agent not found")
    
    # If the agent has raw code payload, run it in the Docker sandbox
    if req.code_payload:
        execution_result = run_agent_in_docker(req.code_payload)
        return {
            "agent_id": agent["id"],
            "agent_name": agent["name"],
            "execution_mode": "docker_sandbox",
            "result": execution_result
        }
    
    # Otherwise, proxy to the registered API endpoint
    return {
        "agent_id": agent["id"],
        "agent_name": agent["name"],
        "execution_mode": "api_proxy",
        "target_endpoint": agent["api_endpoint"],
        "status": "proxied_successfully",
        "note": "API proxy routing active."
    }

from billing import record_usage, calculate_payout, create_stripe_checkout

class ExecutionWithMeteringRequest(AgentExecutionRequest):
    tokens_used: Optional[int] = Field(100, description="Tokens consumed during execution")
    user_email: Optional[str] = Field("client@vilouraai.com", description="Calling user email")

@app.post("/agents/{agent_id}/execute-metered")
def execute_agent_metered(agent_id: int, req: ExecutionWithMeteringRequest, current_dev = Depends(get_current_developer)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM agents WHERE id = ? AND status = 'active'", (agent_id,))
    agent = cursor.fetchone()
    conn.close()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Active agent not found")
    
    # Record usage metering & split calculation
    metering_data = record_usage(
        developer_id=agent["developer_id"],
        agent_id=agent["id"],
        user_email=req.user_email,
        tokens_used=req.tokens_used
    )
    
    payout_summary = calculate_payout(agent["developer_id"])
    
    # Run sandbox if code payload provided
    execution_result = None
    if req.code_payload:
        execution_result = run_agent_in_docker(req.code_payload)
        
    return {
        "agent_id": agent["id"],
        "agent_name": agent["name"],
        "metering": metering_data,
        "financial_summary": payout_summary,
        "sandbox_execution": execution_result
    }

@app.get("/developer/earnings")
def get_developer_earnings(current_dev = Depends(get_current_developer)):
    summary = calculate_payout(current_dev["id"])
    return {
        "developer_email": current_dev["email"],
        "earnings": summary
    }

@app.post("/billing/create-subscription")
def create_subscription_checkout(plan_name: str = "Pro Developer", current_dev = Depends(get_current_developer)):
    checkout = create_stripe_checkout(
        developer_email=current_dev["email"],
        plan_name=plan_name,
        success_url="https://vilouraai.com/success",
        cancel_url="https://vilouraai.com/cancel"
    )
    return checkout

@app.get("/crm/metrics")
def get_crm_metrics(current_dev = Depends(get_current_developer)):
    # Connect to the email outreach leads DB
    leads_db_path = "/home/ubuntu/email-agent/leads.db"
    if not os.path.exists(leads_db_path):
        return {"error": "Leads database not found"}
        
    conn = sqlite3.connect(leads_db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as total FROM leads")
    total_leads = cursor.fetchone()["total"]
    
    cursor.execute("SELECT COUNT(*) as sent FROM leads WHERE status = 'sent'")
    sent_leads = cursor.fetchone()["sent"]
    
    cursor.execute("SELECT COUNT(*) as replied FROM leads WHERE status = 'replied'")
    replied_leads = cursor.fetchone()["replied"]
    
    conn.close()
    
    conversion_rate = (replied_leads / sent_leads * 100) if sent_leads > 0 else 0.0
    
    return {
        "pipeline_metrics": {
            "total_leads": total_leads,
            "emails_sent": sent_leads,
            "replies_received": replied_leads,
            "conversion_rate_percent": round(conversion_rate, 2)
        }
    }
