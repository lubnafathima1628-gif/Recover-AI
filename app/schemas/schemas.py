from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

# --- Auth Schemas ---
class UserBase(BaseModel):
    email: str
    full_name: Optional[str] = None
    role: Optional[str] = "ADMIN"

class UserCreate(UserBase):
    password: str
    business_name: Optional[str] = "Demo Electronics Store"
    category: Optional[str] = "E-Commerce"

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]

class UserResponse(UserBase):
    id: str
    merchant_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# --- Policy Schemas ---
class PolicyBase(BaseModel):
    auto_recovery_enabled: bool = True
    auto_retry_limit: int = 3
    approval_threshold: float = 10000.0
    contact_limit: int = 3
    allowed_channels: List[str] = ["EMAIL", "SMS", "WHATSAPP", "IN_APP"]
    quiet_hours_enabled: bool = False
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "08:00"
    blocked_failure_categories: List[str] = ["RISK_RELATED"]
    risk_escalation_threshold: float = 50000.0

class PolicyUpdate(PolicyBase):
    pass

class PolicyResponse(PolicyBase):
    policy_id: str
    merchant_id: str
    updated_at: datetime

    class Config:
        from_attributes = True


# --- Customer Schemas ---
class CustomerBase(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    segment: str = "Standard"
    preferred_channel: str = "EMAIL"
    tenure: int = 1
    total_payments: int = 0
    successful_payments: int = 0
    failed_payments: int = 0
    lifetime_value: float = 0.0

class CustomerCreate(CustomerBase):
    pass

class CustomerResponse(CustomerBase):
    customer_id: str
    merchant_id: str
    created_at: datetime

    class Config:
        from_attributes = True


# --- Order Schemas ---
class OrderBase(BaseModel):
    amount: float
    product: str
    category: str = "Electronics"
    status: str = "PENDING"

class OrderCreate(OrderBase):
    customer_id: str

class OrderResponse(OrderBase):
    order_id: str
    merchant_id: str
    customer_id: str
    created_at: datetime

    class Config:
        from_attributes = True


# --- Payment & Prediction Schemas ---
class PaymentCreate(BaseModel):
    order_id: Optional[str] = None
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    amount: float
    method: str = "UPI"  # UPI, CARD, NET_BANKING, WALLET, BANK_TRANSFER
    failure_code: Optional[str] = "TEMPORARY_NETWORK"
    failure_reason: Optional[str] = "TEMPORARY_NETWORK"

class PredictionResponse(BaseModel):
    prediction_id: str
    payment_id: str
    failure_class: str
    recovery_probability: float
    expected_value: float
    intervention_cost: float
    recommended_action: str
    model_version: str
    explanation: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class RecoveryAttemptResponse(BaseModel):
    attempt_id: str
    payment_id: str
    action: str
    channel: str
    scheduled_at: datetime
    executed_at: Optional[datetime] = None
    result: str
    recovered_amount: float
    failure_reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class PaymentResponse(BaseModel):
    payment_id: str
    order_id: str
    merchant_id: str
    customer_id: str
    amount: float
    method: str
    status: str
    failure_code: Optional[str] = None
    failure_reason: Optional[str] = None
    timestamp: datetime
    external_payment_id: Optional[str] = None
    requires_approval: bool
    approval_status: str
    is_reconciled: bool
    customer: Optional[CustomerResponse] = None
    prediction: Optional[PredictionResponse] = None
    recovery_attempts: List[RecoveryAttemptResponse] = []

    class Config:
        from_attributes = True


# --- Recovery Execution Schemas ---
class RecoveryExecuteRequest(BaseModel):
    action: Optional[str] = None  # If not provided, uses recommended_action
    channel: Optional[str] = None
    force_override: bool = False

class RecoveryExecutionResult(BaseModel):
    status: str  # SUCCESS, FAILED, ESCALATED, PENDING_APPROVAL, RECONCILED
    payment_id: str
    recovered_amount: float
    action_executed: str
    channel_used: str
    reason: Optional[str] = None
    verified: bool
    execution_steps: List[str]
    audit_id: Optional[str] = None


# --- Predict Request Schema ---
class PredictRequest(BaseModel):
    amount: float
    method: str
    failure_code: Optional[str] = "TEMPORARY_NETWORK"
    customer_id: Optional[str] = None
    customer_tenure: Optional[int] = 6
    customer_segment: Optional[str] = "Standard"
    previous_successful: Optional[int] = 3
    previous_failed: Optional[int] = 1


# --- Analytics Schemas ---
class AnalyticsSummary(BaseModel):
    revenue_at_risk: float
    expected_recoverable: float
    actually_recovered: float
    recovery_rate: float
    recovery_precision: float
    avg_recovery_time_seconds: float
    intervention_success_rate: float
    incremental_recovery: float
    total_failed_count: int
    total_recovered_count: int
    total_analyzed_count: int

class LeakageItem(BaseModel):
    category: str
    lost_amount: float
    recoverable_amount: float
    recovery_rate: float
    count: int

class LeakageAnalytics(BaseModel):
    by_payment_method: List[LeakageItem]
    by_failure_reason: List[LeakageItem]
    by_customer_segment: List[LeakageItem]
    by_checkout_intent: List[LeakageItem]

class ActionPerformance(BaseModel):
    action: str
    attempts: int
    successes: int
    success_rate: float
    total_recovered: float
    avg_expected_value: float


# --- AI Analyst Schema ---
class AgentQueryRequest(BaseModel):
    query: str
    context_filters: Optional[Dict[str, Any]] = None

class AgentQueryResponse(BaseModel):
    answer: str
    citations: List[Dict[str, Any]] = []
    suggested_actions: List[str] = []
    generated_chart: Optional[Dict[str, Any]] = None


# --- Audit Log Schema ---
class AuditLogResponse(BaseModel):
    audit_id: str
    merchant_id: str
    payment_id: Optional[str] = None
    event_type: str
    actor: str
    action: str
    reason: Optional[str] = None
    metadata_json: Dict[str, Any]
    timestamp: datetime

    class Config:
        from_attributes = True


# --- Notification Schema ---
class NotificationResponse(BaseModel):
    notification_id: str
    merchant_id: str
    title: str
    message: str
    type: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True
