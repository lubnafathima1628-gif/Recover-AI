import random
import uuid
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Generator, AsyncGenerator
from sqlalchemy.orm import Session

from backend.app.models.models import (
    Merchant, User, Customer, Order, Payment, Prediction, RecoveryAttempt,
    AuditLog, Notification, Policy, ModelVersion, AnalyticsSnapshot
)
from backend.app.ml.classifier import classifier
from backend.app.ml.recovery_model import recovery_model
from backend.app.ml.expected_value import expected_value_engine
from backend.app.ml.decision_engine import decision_engine
from backend.app.payments.simulation_provider import simulation_provider

class DemoEngine:
    """
    Synthetic Transaction Generator & Live Cinematic Recovery Simulator.
    Generates realistic datasets and streams live event processing.
    """

    def __init__(self):
        self._rng = random.Random(42)

    def generate_seed_dataset(self, db: Session, total_count: int = 1000) -> Dict[str, Any]:
        """
        Creates a complete seeded merchant, customers, and transactions in the DB.
        """
        # 1. Merchant & Policy
        merchant = db.query(Merchant).first()
        if not merchant:
            merchant = Merchant(
                merchant_id="merchant_demo_electronics_01",
                business_name="Apex Electronics & Gear",
                category="Consumer Electronics & SaaS",
                average_order_value=4500.0
            )
            db.add(merchant)
            db.flush()

        policy = db.query(Policy).filter(Policy.merchant_id == merchant.merchant_id).first()
        if not policy:
            policy = Policy(
                merchant_id=merchant.merchant_id,
                auto_recovery_enabled=True,
                auto_retry_limit=3,
                approval_threshold=15000.0,
                contact_limit=3,
                allowed_channels=["EMAIL", "SMS", "WHATSAPP", "IN_APP"],
                quiet_hours_enabled=False,
                blocked_failure_categories=["RISK_RELATED"],
                risk_escalation_threshold=50000.0
            )
            db.add(policy)
            db.flush()

        # 2. Customers
        customer_pool = db.query(Customer).filter(Customer.merchant_id == merchant.merchant_id).all()
        if not customer_pool:
            first_names = ["Arjun", "Priya", "Rohan", "Sneha", "Aditya", "Ananya", "Vikram", "Neha", "Rahul", "Kavita", "Siddharth", "Pooja"]
            last_names = ["Sharma", "Verma", "Patel", "Reddy", "Mehta", "Iyer", "Nair", "Gupta", "Deshmukh", "Chopra", "Kapoor", "Bose"]
            segments = ["VIP", "Enterprise", "SMB", "Standard"]
            channels = ["EMAIL", "SMS", "WHATSAPP", "IN_APP"]

            customer_pool = []
            for i in range(50):
                fn = first_names[i % len(first_names)]
                ln = last_names[(i // 2) % len(last_names)]
                cust = Customer(
                    merchant_id=merchant.merchant_id,
                    name=f"{fn} {ln}",
                    email=f"{fn.lower()}.{ln.lower()}{i}@example.com",
                    phone=f"+91 98{i:02d}0 {i:02d}110",
                    segment=self._rng.choice(segments),
                    preferred_channel=self._rng.choice(channels),
                    tenure=self._rng.randint(2, 36),
                    total_payments=self._rng.randint(5, 40),
                    successful_payments=self._rng.randint(4, 38),
                    failed_payments=self._rng.randint(0, 3),
                    lifetime_value=float(self._rng.randint(12000, 350000))
                )
                db.add(cust)
                customer_pool.append(cust)
            db.flush()

        # 3. Generate Transactions
        products = [
            ("Pro ANC Noise-Cancelling Headphones", 14999.0, "Audio"),
            ("Ultra-Wide 34' 4K OLED Monitor", 42500.0, "Displays"),
            ("Mechanical Ergonomic Keyboard RGB", 8499.0, "Accessories"),
            ("Smart Studio Audio Interface", 18900.0, "Audio"),
            ("USB-C GaN 140W Fast Charging Hub", 4999.0, "Power"),
            ("Flagship Mirrorless 4K Camera Lens", 68000.0, "Optics"),
            ("Enterprise Cloud Sync Annual Subscription", 24000.0, "Software"),
            ("MagSafe Wireless Power Deck", 3499.0, "Power")
        ]

        methods = ["UPI", "CARD", "NET_BANKING", "WALLET", "BANK_TRANSFER"]
        failure_codes = [
            "TEMPORARY_NETWORK",
            "INVALID_PAYMENT_METHOD",
            "AUTHENTICATION_FAILURE",
            "INSUFFICIENT_FUNDS",
            "RISK_RELATED",
            "DUPLICATE_ALREADY_PAID"
        ]

        # Populate batch
        for i in range(total_count):
            cust = self._rng.choice(customer_pool)
            prod_name, prod_price, prod_cat = self._rng.choice(products)
            method = self._rng.choice(methods)

            # 70% success, 30% failed
            is_init_fail = self._rng.random() < 0.32
            pay_status = "FAILED" if is_init_fail else "SUCCESS"
            fail_code = self._rng.choice(failure_codes) if is_init_fail else None
            fail_reason = simulation_provider._get_failure_message(fail_code) if fail_code else None

            created_time = datetime.utcnow() - timedelta(days=self._rng.randint(0, 30), minutes=self._rng.randint(0, 1440))

            order = Order(
                merchant_id=merchant.merchant_id,
                customer_id=cust.customer_id,
                amount=prod_price,
                product=prod_name,
                category=prod_cat,
                status="PAID" if pay_status == "SUCCESS" else "FAILED",
                created_at=created_time
            )
            db.add(order)
            db.flush()

            requires_approval = (prod_price >= policy.approval_threshold) and is_init_fail

            payment = Payment(
                order_id=order.order_id,
                merchant_id=merchant.merchant_id,
                customer_id=cust.customer_id,
                amount=prod_price,
                method=method,
                status=pay_status,
                failure_code=fail_code,
                failure_reason=fail_reason,
                timestamp=created_time,
                external_payment_id=f"sim_ext_{uuid.uuid4().hex[:10]}",
                requires_approval=requires_approval,
                approval_status="PENDING" if requires_approval else "NOT_REQUIRED",
                is_reconciled=fail_code != "DUPLICATE_ALREADY_PAID"
            )
            db.add(payment)
            db.flush()

            if is_init_fail:
                # Failure classification & ML prediction
                f_class = classifier.classify(fail_code, fail_reason)
                prob, explanation = recovery_model.predict_probability(
                    amount=prod_price,
                    payment_method=method,
                    failure_category=f_class,
                    customer_tenure_months=cust.tenure,
                    successful_payments=cust.successful_payments,
                    failed_payments=cust.failed_payments,
                    customer_segment=cust.segment
                )
                action, reason, need_appr = decision_engine.select_action(
                    amount=prod_price,
                    failure_category=f_class,
                    probability=prob,
                    expected_value=0.0,
                    policy=policy
                )
                cost = expected_value_engine.get_intervention_cost(action)
                ev = expected_value_engine.calculate_expected_value(prod_price, prob, action, cost)

                pred = Prediction(
                    payment_id=payment.payment_id,
                    failure_class=f_class,
                    recovery_probability=prob,
                    expected_value=ev,
                    intervention_cost=cost,
                    recommended_action=action,
                    model_version=recovery_model.version,
                    explanation=explanation,
                    created_at=created_time + timedelta(seconds=2)
                )
                db.add(pred)

                # For half of failed payments in history, simulate that recovery was executed
                if self._rng.random() < 0.65 and not requires_approval:
                    is_rec = self._rng.random() < prob
                    rec_amount = prod_price if is_rec else 0.0
                    attempt = RecoveryAttempt(
                        payment_id=payment.payment_id,
                        action=action,
                        channel=cust.preferred_channel,
                        scheduled_at=created_time + timedelta(seconds=15),
                        executed_at=created_time + timedelta(seconds=18),
                        result="SUCCESS" if is_rec else "FAILED",
                        recovered_amount=rec_amount,
                        failure_reason=None if is_rec else "Simulated retry attempt timed out",
                        created_at=created_time + timedelta(seconds=18)
                    )
                    db.add(attempt)
                    if is_rec:
                        payment.status = "SUCCESS"
                        order.status = "PAID"

            # Audit log for failed/recovered events
            if is_init_fail:
                audit = AuditLog(
                    merchant_id=merchant.merchant_id,
                    payment_id=payment.payment_id,
                    event_type="PAYMENT_DETECTED",
                    actor="SIMULATION_ENGINE",
                    action="DIAGNOSE_FAILURE",
                    reason=fail_reason,
                    metadata_json={"amount": prod_price, "method": method, "code": fail_code},
                    timestamp=created_time
                )
                db.add(audit)

        db.commit()
        return {"status": "SUCCESS", "message": f"Successfully generated {total_count} transactions dataset"}

    async def run_live_demo_stream(self, db: Session) -> AsyncGenerator[str, None]:
        """
        Streams realistic real-time events for the Demo Command Center via SSE.
        """
        events = [
            {"step": "START", "title": "10,000 TRANSACTIONS INGESTED & ANALYZED", "at_risk": 482500.0, "progress": 10},
            {"step": "DIAGNOSE", "title": "DIAGNOSING ROOT CAUSES ACROSS PAYMENT RAILS", "details": "Identified temporary bank timeouts & invalid method drops", "progress": 25},
            {"step": "PREDICT", "title": "CALCULATING ML RECOVERY PROBABILITIES", "details": "Ensemble gradient boosting evaluated 72.4% avg probability", "progress": 40},
            {"step": "PRIORITIZE", "title": "EXPECTED VALUE RANKING (EV = Amount × P - Cost)", "expected_recoverable": 348900.0, "progress": 55},
            {"step": "DECISION", "title": "MATCHING OPTIMAL RECOVERY ACTIONS & POLICIES", "details": "Scheduled automated retries, alternate rails, & smart links", "progress": 70},
            {"step": "EXECUTE", "title": "EXECUTING RECOVERY INTERVENTIONS", "details": "Dispatched smart payment links & background retries", "progress": 85},
            {"step": "VERIFY", "title": "VERIFYING BANKING RAIL SETTLEMENT & RECORDING", "actually_recovered": 352400.0, "progress": 100}
        ]

        for ev in events:
            yield f"data: {json.dumps(ev)}\n\n"
            await asyncio.sleep(0.8)

demo_engine = DemoEngine()
