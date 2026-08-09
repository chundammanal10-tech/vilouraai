import stripe
import os
import sqlite3

# Initialize Stripe API Key (mock or env)
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_mock_key")
DB_PATH = "/home/ubuntu/email-outreach/viloura.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def record_usage(developer_id: int, agent_id: int, user_email: str, tokens_used: int, price_per_token: float = 0.0001):
    cost = tokens_used * price_per_token
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO usage_logs (developer_id, agent_id, user_email, tokens_used, cost)
           VALUES (?, ?, ?, ?, ?)""",
        (developer_id, agent_id, user_email, tokens_used, cost)
    )
    conn.commit()
    conn.close()
    return {"tokens_used": tokens_used, "calculated_cost": cost}

def calculate_payout(developer_id: int, platform_commission_rate: float = 0.15):
    """
    Calculates total earnings for a developer and splits the platform cut.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(cost) as total_revenue FROM usage_logs WHERE developer_id = ?", (developer_id,))
    row = cursor.fetchone()
    conn.close()
    
    gross_revenue = row["total_revenue"] if row and row["total_revenue"] else 0.0
    platform_cut = gross_revenue * platform_commission_rate
    developer_payout = gross_revenue - platform_cut
    
    return {
        "gross_revenue": round(gross_revenue, 4),
        "platform_commission": round(platform_cut, 4),
        "developer_payout": round(developer_payout, 4)
    }

def create_stripe_checkout(developer_email: str, plan_name: str, success_url: str, cancel_url: str):
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            customer_email=developer_email,
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {'name': f'VilouraAI - {plan_name} Tier'},
                    'unit_amount': 2900,  # e.g., $29.00/month
                    'recurring': {'interval': 'month'},
                },
                'quantity': 1,
            }],
            mode='subscription',
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return {"checkout_url": session.url, "session_id": session.id}
    except Exception as e:
        # Fallback for test/mock environments if Stripe key is not live
        return {
            "checkout_url": "https://billing.stripe.com/test/mock-checkout",
            "session_id": "cs_test_mock123",
            "note": f"Stripe running in mock mode due to API error: {str(e)}"
        }
