from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from backend.app.core.config import settings
from backend.app.core.database import Base, engine, SessionLocal
from backend.app.api import (
    auth, transactions, predictions, recovery, analytics,
    audit, agent, customers, policies, notifications, demo, health
)
from backend.app.services.demo_service import demo_engine
from backend.app.models.models import User, Merchant
from backend.app.core.security import hash_password

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Automatically create database tables if they do not exist
    Base.metadata.create_all(bind=engine)
    
    # Auto-seed demo dataset if table is empty
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "admin@recoverai.local").first()
        if not user:
            merchant = Merchant(
                merchant_id="merchant_demo_electronics_01",
                business_name="Apex Electronics & SaaS Store",
                category="Consumer Electronics & Subscriptions",
                average_order_value=6500.0
            )
            db.add(merchant)
            db.flush()

            demo_user = User(
                email="admin@recoverai.local",
                hashed_password=hash_password("RecoverAI@2026"),
                full_name="Alex Mercer (VP Finance)",
                role="OWNER",
                merchant_id=merchant.merchant_id
            )
            db.add(demo_user)
            db.commit()

            demo_engine.generate_seed_dataset(db, total_count=150)
    finally:
        db.close()

    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="RecoverAI — AI Revenue Recovery Engine with Simulated Payment Rails and Expected Value Decision Intelligence",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all API Routers
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(transactions.router)
app.include_router(predictions.router)
app.include_router(recovery.router)
app.include_router(analytics.router)
app.include_router(audit.router)
app.include_router(agent.router)
app.include_router(customers.router)
app.include_router(policies.router)
app.include_router(notifications.router)
app.include_router(demo.router)

@app.get("/")
def root():
    return {
        "app": "RecoverAI",
        "tagline": "Turn at-risk revenue into measurable recovered revenue.",
        "status": "online",
        "mode": "SIMULATION_MODE",
        "docs": "/docs"
    }
