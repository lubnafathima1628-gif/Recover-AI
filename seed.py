import sys
import os

# Add root directory to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.core.database import SessionLocal, Base, engine
from backend.app.models.models import User, Merchant, Policy
from backend.app.core.security import hash_password
from backend.app.services.demo_service import demo_engine

def seed():
    print("Initializing RecoverAI Database Schema...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("Checking Demo Merchant...")
        merchant = db.query(Merchant).filter(Merchant.merchant_id == "merchant_demo_electronics_01").first()
        if not merchant:
            merchant = Merchant(
                merchant_id="merchant_demo_electronics_01",
                business_name="Apex Electronics & SaaS Store",
                category="Consumer Electronics & Subscriptions",
                average_order_value=6500.0
            )
            db.add(merchant)
            db.flush()

        print("Checking Demo User Account...")
        user = db.query(User).filter(User.email == "admin@recoverai.local").first()
        if not user:
            user = User(
                email="admin@recoverai.local",
                hashed_password=hash_password("RecoverAI@2026"),
                full_name="Alex Mercer (VP Finance)",
                role="OWNER",
                merchant_id=merchant.merchant_id
            )
            db.add(user)
            db.commit()

        print("Generating Realistic Synthetic Transactions (500 records)...")
        res = demo_engine.generate_seed_dataset(db, total_count=500)
        print(f"[SUCCESS] Seed completed successfully: {res['message']}")
        print("\nDemo Login Credentials:")
        print("-----------------------")
        print("Email:    admin@recoverai.local")
        print("Password: RecoverAI@2026")
        print("Role:     OWNER / ADMIN")
        print("-----------------------\n")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
