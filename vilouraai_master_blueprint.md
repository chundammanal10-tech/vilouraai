# VilouraAI — Master Architecture & Business Blueprint
**Founder:** Jilsha Jose  
**Repository:** `chundammanal10-tech/vilouraai`  
**Last Updated:** August 2026

---

## 1. Executive Summary & Vision
VilouraAI is a production-grade marketplace and execution platform for autonomous AI agents. It connects developers who build specialized agents with businesses seeking automated workflow solutions, backed by secure sandboxing, usage-based metering, and automated growth pipelines.

---

## 2. Core Platform Architecture & Backend (`app.py` & `database.py`)
Built with **FastAPI** and backed by **SQLite** (`viloura.db`), the core platform manages developer authentication and agent registries.

* **Developer Authentication:** 
  * Password hashing using SHA-256.
  * JWT-based Bearer token authentication (`/token` and `/register`).
* **Agent Registry & Metadata Schema:**
  * Stores agent specs: `name`, `description`, `capabilities`, `api_endpoint`, `pricing_model`, `category`, and `status`.
  * Public browsing (`GET /agents`) and developer management (`GET /developer/agents`).

---

## 3. Secure Sandboxing & API Gateway (`sandbox.py`)
To prevent malicious code execution, submitted agent payloads run in isolated ephemeral environments.
* **Docker Containerization Constraints:**
  * `--network none`: Disables internet access inside the container.
  * `--memory 256m`: Caps RAM usage at 256 MB.
  * `--cpus 0.5`: Restricts CPU usage to half a core.
  * `--timeout`: Hard timeout set to 10 seconds.
* **Execution Modes:**
  * **Docker Sandbox Mode:** Executes raw Python code safely.
  * **API Proxy Mode:** Routes requests directly to registered developer API endpoints.

---

## 4. Monetization & Payment Infrastructure (`billing.py`)
Handles recurring SaaS subscriptions and pay-per-execution billing.
* **Usage Metering (`usage_logs`):**
  * Tracks every API invocation and token consumed per user per agent.
* **Creator Payout & Commission Engine:**
  * Automatically calculates gross revenue.
  * Splits revenue: **85% Creator Payout / 15% VilouraAI Platform Commission**.
* **Stripe Integration:**
  * Generates Stripe Checkout sessions for developer subscription tiers (`/billing/create-subscription`).

---

## 5. Automated Growth & CRM Pipeline (`reply_tracker.py`)
Transforms your outreach database into a self-updating conversion funnel.
* **Pre-Flight Validation (`validate_outreach.py`):**
  * Verifies SQLite lead database schema and tests Gmail SMTP connectivity prior to batch runs.
* **IMAP Reply Tracking (`reply_tracker.py`):**
  * Connects securely to Gmail via IMAP SSL, checks incoming messages, and automatically updates lead statuses from `'sent'` to `'replied'`.
* **CRM Pipeline Analytics (`GET /crm/metrics`):**
  * Calculates real-time conversion rates (`total_leads`, `emails_sent`, `replies_received`, and `conversion_rate_percent`).

---

## 6. Git & Repository Sync Status
* **Remote Repository:** `https://github.com/chundammanal10-tech/vilouraai.git`
* **Active Branches:** `main` (fully synced with all pre-flight, registry, sandbox, billing, and CRM modules).
