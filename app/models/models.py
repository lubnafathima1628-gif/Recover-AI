import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON
)
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(String, default="ADMIN")  # OWNER, ADMIN, ANALYST, VIEWER
    merchant_id = Column(String, ForeignKey("merchants.merchant_id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    merchant = relationship("Merchant", back_populates="users")


class Merchant(Base):
    __tablename__ = "merchants"

    merchant_id = Column(String, primary_key=True, default=generate_uuid)
    business_name = Column(String, nullable=False)
    category = Column(String, default="E-Commerce")
    average_order_value = Column(Float, default=1500.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    users = relationship("User", back_populates="merchant")
    customers = relationship("Customer", back_populates="merchant", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="merchant", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="merchant", cascade="all, delete-orphan")
    policy = relationship("Policy", back_populates="merchant", uselist=False, cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="merchant", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="merchant", cascade="all, delete-orphan")
    analytics_snapshots = relationship("AnalyticsSnapshot", back_populates="merchant", cascade="all, delete-orphan")


class Policy(Base):
    __tablename__ = "policies"

    policy_id = Column(String, primary_key=True, default=generate_uuid)
    merchant_id = Column(String, ForeignKey("merchants.merchant_id"), unique=True, nullable=False)
    auto_recovery_enabled = Column(Boolean, default=True)
    auto_retry_limit = Column(Integer, default=3)
    approval_threshold = Column(Float, default=10000.0)
    contact_limit = Column(Integer, default=3)
    allowed_channels = Column(JSON, default=lambda: ["EMAIL", "SMS", "WHATSAPP", "IN_APP"])
    quiet_hours_enabled = Column(Boolean, default=False)
    quiet_hours_start = Column(String, default="22:00")
    quiet_hours_end = Column(String, default="08:00")
    blocked_failure_categories = Column(JSON, default=lambda: ["RISK_RELATED"])
    risk_escalation_threshold = Column(Float, default=50000.0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    merchant = relationship("Merchant", back_populates="policy")


class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(String, primary_key=True, default=generate_uuid)
    merchant_id = Column(String, ForeignKey("merchants.merchant_id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, index=True)
    phone = Column(String, nullable=True)
    segment = Column(String, default="Standard")  # VIP, Enterprise, SMB, Standard
    preferred_channel = Column(String, default="EMAIL")  # EMAIL, SMS, WHATSAPP, IN_APP
    tenure = Column(Integer, default=1)  # Months
    total_payments = Column(Integer, default=0)
    successful_payments = Column(Integer, default=0)
    failed_payments = Column(Integer, default=0)
    lifetime_value = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    merchant = relationship("Merchant", back_populates="customers")
    orders = relationship("Order", back_populates="customer", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="customer", cascade="all, delete-orphan")


class Order(Base):
    __tablename__ = "orders"

    order_id = Column(String, primary_key=True, default=generate_uuid)
    merchant_id = Column(String, ForeignKey("merchants.merchant_id"), nullable=False, index=True)
    customer_id = Column(String, ForeignKey("customers.customer_id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    product = Column(String, nullable=False)
    category = Column(String, default="Electronics")
    status = Column(String, default="PENDING")  # PENDING, PAID, FAILED, CANCELLED
    created_at = Column(DateTime, default=datetime.utcnow)

    merchant = relationship("Merchant", back_populates="orders")
    customer = relationship("Customer", back_populates="orders")
    payments = relationship("Payment", back_populates="order", cascade="all, delete-orphan")


class Payment(Base):
    __tablename__ = "payments"

    payment_id = Column(String, primary_key=True, default=generate_uuid)
    order_id = Column(String, ForeignKey("orders.order_id"), nullable=False, index=True)
    merchant_id = Column(String, ForeignKey("merchants.merchant_id"), nullable=False, index=True)
    customer_id = Column(String, ForeignKey("customers.customer_id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    method = Column(String, nullable=False)  # UPI, CARD, NET_BANKING, WALLET, BANK_TRANSFER
    status = Column(String, default="FAILED")  # SUCCESS, FAILED, PENDING, AUTHORIZED, CAPTURED, CANCELLED, REFUNDED, UNKNOWN
    failure_code = Column(String, nullable=True)
    failure_reason = Column(String, nullable=True)  # TEMPORARY_NETWORK, INVALID_PAYMENT_METHOD, etc.
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    external_payment_id = Column(String, nullable=True)
    requires_approval = Column(Boolean, default=False)
    approval_status = Column(String, default="PENDING")  # PENDING, APPROVED, REJECTED, NOT_REQUIRED
    is_reconciled = Column(Boolean, default=True)

    merchant = relationship("Merchant", back_populates="payments")
    customer = relationship("Customer", back_populates="payments")
    order = relationship("Order", back_populates="payments")
    prediction = relationship("Prediction", back_populates="payment", uselist=False, cascade="all, delete-orphan")
    recovery_attempts = relationship("RecoveryAttempt", back_populates="payment", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="payment", cascade="all, delete-orphan")


class Prediction(Base):
    __tablename__ = "predictions"

    prediction_id = Column(String, primary_key=True, default=generate_uuid)
    payment_id = Column(String, ForeignKey("payments.payment_id"), unique=True, nullable=False)
    failure_class = Column(String, nullable=False)
    recovery_probability = Column(Float, nullable=False)
    expected_value = Column(Float, nullable=False)
    intervention_cost = Column(Float, default=50.0)
    recommended_action = Column(String, nullable=False)
    model_version = Column(String, default="v1.2.0-xgb")
    explanation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    payment = relationship("Payment", back_populates="prediction")
    feedbacks = relationship("Feedback", back_populates="prediction", cascade="all, delete-orphan")


class RecoveryAttempt(Base):
    __tablename__ = "recovery_attempts"

    attempt_id = Column(String, primary_key=True, default=generate_uuid)
    payment_id = Column(String, ForeignKey("payments.payment_id"), nullable=False, index=True)
    action = Column(String, nullable=False)  # RETRY_LATER, ALTERNATE_PAYMENT_METHOD, PAYMENT_LINK, RETRY_OR_UPDATE_METHOD, RECONCILE_FIRST, MERCHANT_APPROVAL, ESCALATE, NO_ACTION
    channel = Column(String, default="SYSTEM")  # EMAIL, SMS, WHATSAPP, IN_APP, SYSTEM
    scheduled_at = Column(DateTime, default=datetime.utcnow)
    executed_at = Column(DateTime, nullable=True)
    result = Column(String, default="PENDING")  # SUCCESS, FAILED, PENDING, RECONCILED
    recovered_amount = Column(Float, default=0.0)
    failure_reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    payment = relationship("Payment", back_populates="recovery_attempts")
    feedbacks = relationship("Feedback", back_populates="attempt", cascade="all, delete-orphan")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    audit_id = Column(String, primary_key=True, default=generate_uuid)
    merchant_id = Column(String, ForeignKey("merchants.merchant_id"), nullable=False, index=True)
    payment_id = Column(String, ForeignKey("payments.payment_id"), nullable=True, index=True)
    event_type = Column(String, nullable=False)
    actor = Column(String, default="AI_ENGINE")  # AI_ENGINE, SYSTEM, USER:<id>
    action = Column(String, nullable=False)
    reason = Column(String, nullable=True)
    metadata_json = Column(JSON, default=dict)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    merchant = relationship("Merchant", back_populates="audit_logs")
    payment = relationship("Payment", back_populates="audit_logs")


class Notification(Base):
    __tablename__ = "notifications"

    notification_id = Column(String, primary_key=True, default=generate_uuid)
    merchant_id = Column(String, ForeignKey("merchants.merchant_id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    type = Column(String, default="INFO")  # INFO, WARNING, SUCCESS, ALERT
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    merchant = relationship("Merchant", back_populates="notifications")


class ModelVersion(Base):
    __tablename__ = "model_versions"

    version_id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    algorithm = Column(String, default="XGBoost Classifier + Expected Value Ranking")
    precision = Column(Float, default=0.884)
    recall = Column(Float, default=0.842)
    roc_auc = Column(Float, default=0.912)
    is_active = Column(Boolean, default=True)
    trained_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class Feedback(Base):
    __tablename__ = "feedback"

    feedback_id = Column(String, primary_key=True, default=generate_uuid)
    prediction_id = Column(String, ForeignKey("predictions.prediction_id"), nullable=False)
    attempt_id = Column(String, ForeignKey("recovery_attempts.attempt_id"), nullable=False)
    actual_outcome = Column(String, nullable=False)  # SUCCESS, FAILED
    recovered_amount = Column(Float, default=0.0)
    time_to_recovery = Column(Float, default=0.0)  # Seconds
    contact_count = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    prediction = relationship("Prediction", back_populates="feedbacks")
    attempt = relationship("RecoveryAttempt", back_populates="feedbacks")


class AnalyticsSnapshot(Base):
    __tablename__ = "analytics_snapshots"

    snapshot_id = Column(String, primary_key=True, default=generate_uuid)
    merchant_id = Column(String, ForeignKey("merchants.merchant_id"), nullable=False, index=True)
    date = Column(DateTime, default=datetime.utcnow, index=True)
    total_at_risk = Column(Float, default=0.0)
    expected_recoverable = Column(Float, default=0.0)
    actually_recovered = Column(Float, default=0.0)
    recovery_rate = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    merchant = relationship("Merchant", back_populates="analytics_snapshots")
