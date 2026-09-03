import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from backend.app.core.database import Base, get_db
from backend.app.main import app
from backend.app.models.models import Merchant, User, Customer, Payment, Policy, Prediction
from backend.app.payments.simulation_provider import SimulationPaymentProvider
from backend.app.payments.payment_state_machine import PaymentStateMachine
from backend.app.ml.classifier import FailureClassifier
from backend.app.ml.recovery_model import RecoveryProbabilityModel
from backend.app.ml.expected_value import ExpectedValueEngine
from backend.app.ml.decision_engine import DecisionEngine
from backend.app.core.security import hash_password, verify_password, create_access_token

# Test Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_recoverai.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

# 1. Security & Auth Tests
def test_password_hashing():
    pwd = "SecureFintechPassword123!"
    hashed = hash_password(pwd)
    assert verify_password(pwd, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

def test_auth_token_generation():
    token = create_access_token(subject="tester@recoverai.local")
    assert token is not None
    assert len(token) > 20

# 2. Failure Classifier Tests
def test_failure_classifier():
    assert FailureClassifier.classify("BANK_TIMEOUT_504") == "TEMPORARY_NETWORK"
    assert FailureClassifier.classify("CARD_EXPIRED_DECLINE") == "INVALID_PAYMENT_METHOD"
    assert FailureClassifier.classify("OTP_VERIFY_MISMATCH") == "AUTHENTICATION_FAILURE"
    assert FailureClassifier.classify("INSUFFICIENT_FUNDS") == "INSUFFICIENT_FUNDS"
    assert FailureClassifier.classify("FRAUD_SUSPECT") == "RISK_RELATED"
    assert FailureClassifier.classify("DUPLICATE_ALREADY_PAID") == "DUPLICATE_ALREADY_PAID"

# 3. Recovery Probability ML Model Tests
def test_recovery_probability_model():
    model = RecoveryProbabilityModel()
    prob, explanation = model.predict_probability(
        amount=25000.0,
        payment_method="UPI",
        failure_category="TEMPORARY_NETWORK",
        customer_tenure_months=12,
        successful_payments=10,
        failed_payments=1,
        customer_segment="VIP"
    )
    assert 0.05 <= prob <= 0.98
    assert prob > 0.65  # VIP with temporary network timeout should have high recovery probability
    assert len(explanation) > 0

# 4. Expected Value Engine Tests
def test_expected_value_calculation():
    amount = 25000.0
    prob = 0.72
    action = "RETRY_LATER"
    ev = ExpectedValueEngine.calculate_expected_value(amount, prob, action)
    cost = ExpectedValueEngine.get_intervention_cost(action)
    expected_calc = round((amount * prob) - cost, 2)
    assert ev == expected_calc
    assert ev > 0

# 5. Decision Engine Tests
def test_decision_engine_rules():
    # Ambiguous debit
    act, reason, appr = DecisionEngine.select_action(
        amount=10000.0,
        failure_category="DUPLICATE_ALREADY_PAID",
        probability=0.85,
        expected_value=8450.0,
        is_ambiguous_debit=True
    )
    assert act == "RECONCILE_FIRST"

    # High value exceeds threshold
    mock_policy = type("Policy", (), {"approval_threshold": 15000.0, "blocked_failure_categories": []})
    act_high, reason_high, appr_high = DecisionEngine.select_action(
        amount=45000.0,
        failure_category="TEMPORARY_NETWORK",
        probability=0.80,
        expected_value=35000.0,
        policy=mock_policy
    )
    assert act_high == "MERCHANT_APPROVAL"
    assert appr_high is True

    # Temporary network failure under threshold
    act_temp, _, appr_temp = DecisionEngine.select_action(
        amount=5000.0,
        failure_category="TEMPORARY_NETWORK",
        probability=0.85,
        expected_value=4200.0,
        policy=mock_policy
    )
    assert act_temp == "RETRY_LATER"
    assert appr_temp is False

# 6. Simulated Payment Provider Tests
def test_simulation_payment_provider():
    sim = SimulationPaymentProvider(seed=123)
    created = sim.create_payment(
        amount=15000.0,
        currency="INR",
        payment_method="UPI",
        metadata={"force_failure_reason": "TEMPORARY_NETWORK"}
    )
    assert created["status"] == "FAILED"
    assert created["failure_code"] == "TEMPORARY_NETWORK"
    assert created["simulation_mode"] is True

    # Test retry intervention
    retry_res = sim.retry_payment(
        payment_id=created["payment_id"],
        action="RETRY_LATER",
        channel="SYSTEM"
    )
    assert retry_res["status"] in ["SUCCESS", "FAILED"]
    assert "simulation_mode" in retry_res

# 7. Payment State Machine Tests
def test_payment_state_machine():
    assert PaymentStateMachine.can_transition("INITIATED", "PROCESSING") is True
    assert PaymentStateMachine.can_transition("FAILED", "PROCESSING") is True
    assert PaymentStateMachine.can_transition("SUCCESS", "PROCESSING") is False  # Cannot retry settled payment

# 8. API Endpoint Integration Tests
def test_health_endpoint():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["simulation_mode"] == "SIMULATION_MODE"

def test_auth_and_recovery_flow():
    # Register test user
    reg_payload = {
        "email": "test_owner@fintech.local",
        "password": "Password@12345",
        "full_name": "Test Fintech Admin",
        "business_name": "Test Merchant Inc"
    }
    reg_res = client.post("/auth/register", json=reg_payload)
    assert reg_res.status_code == 200
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify /auth/me
    me_res = client.get("/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "test_owner@fintech.local"

    # Create a transaction
    tx_payload = {
        "amount": 25000.0,
        "method": "UPI",
        "failure_reason": "TEMPORARY_NETWORK",
        "customer_name": "Test Customer",
        "customer_email": "test.cust@example.com"
    }
    tx_res = client.post("/transactions", json=tx_payload)
    assert tx_res.status_code == 200
    tx_data = tx_res.json()
    payment_id = tx_data["payment_id"]

    # Verify prediction was generated
    assert tx_data["prediction"] is not None
    assert tx_data["prediction"]["recovery_probability"] > 0
    assert tx_data["prediction"]["expected_value"] > 0

    # Execute recovery
    recov_res = client.post(f"/recover/{payment_id}", json={"force_override": True})
    assert recov_res.status_code == 200
    recov_data = recov_res.json()
    assert recov_data["payment_id"] == payment_id
    assert recov_data["status"] in ["SUCCESS", "FAILED"]

    # Check Analytics
    analytics_res = client.get("/analytics/summary")
    assert analytics_res.status_code == 200
    summary = analytics_res.json()
    assert "revenue_at_risk" in summary
    assert "actually_recovered" in summary

    # Check AI Analyst Query
    agent_res = client.post("/agent/query", json={"query": "Why did revenue fall?"})
    assert agent_res.status_code == 200
    assert len(agent_res.json()["answer"]) > 0
