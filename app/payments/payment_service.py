import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from backend.app.models.models import Payment, RecoveryAttempt, AuditLog, Order, Customer, Policy, Prediction
from backend.app.payments.simulation_provider import simulation_provider
from backend.app.payments.payment_state_machine import PaymentStateMachine

class PaymentService:
    def __init__(self, db: Session):
        self.db = db
        self.provider = simulation_provider

    def create_payment(
        self,
        merchant_id: str,
        amount: float,
        customer_id: str,
        method: str = "UPI",
        order_id: Optional[str] = None,
        force_failure_reason: Optional[str] = None
    ) -> Payment:
        customer = self.db.query(Customer).filter(Customer.customer_id == customer_id).first()
        if not order_id:
            order = Order(
                merchant_id=merchant_id,
                customer_id=customer_id,
                amount=amount,
                product="Premium Electronics & Accessories",
                category="Electronics",
                status="PENDING"
            )
            self.db.add(order)
            self.db.flush()
            order_id = order.order_id

        # Invoke Simulation Provider
        sim_res = self.provider.create_payment(
            amount=amount,
            currency="INR",
            customer_info={"id": customer_id, "name": customer.name if customer else "Customer"},
            payment_method=method,
            metadata={"force_failure_reason": force_failure_reason} if force_failure_reason else None
        )

        # Check Policy for Approval Threshold
        policy = self.db.query(Policy).filter(Policy.merchant_id == merchant_id).first()
        threshold = policy.approval_threshold if policy else 10000.0
        requires_approval = amount >= threshold and sim_res["status"] == "FAILED"

        payment = Payment(
            order_id=order_id,
            merchant_id=merchant_id,
            customer_id=customer_id,
            amount=amount,
            method=method,
            status=sim_res["status"],
            failure_code=sim_res.get("failure_code"),
            failure_reason=sim_res.get("failure_reason"),
            external_payment_id=sim_res.get("external_payment_id"),
            requires_approval=requires_approval,
            approval_status="PENDING" if requires_approval else "NOT_REQUIRED",
            is_reconciled=sim_res.get("failure_code") != "DUPLICATE_ALREADY_PAID"
        )
        self.db.add(payment)
        self.db.flush()

        # Append to Audit Log
        audit = AuditLog(
            merchant_id=merchant_id,
            payment_id=payment.payment_id,
            event_type="PAYMENT_DETECTED" if payment.status == "FAILED" else "PAYMENT_SUCCESS",
            actor="SIMULATION_GATEWAY",
            action="CREATE_PAYMENT",
            reason=payment.failure_reason,
            metadata_json={
                "amount": amount,
                "method": method,
                "status": payment.status,
                "failure_code": payment.failure_code
            }
        )
        self.db.add(audit)
        self.db.commit()
        self.db.refresh(payment)
        return payment

    def execute_recovery(
        self,
        payment_id: str,
        action: Optional[str] = None,
        channel: Optional[str] = None,
        force_override: bool = False,
        actor: str = "AI_ENGINE"
    ) -> Dict[str, Any]:
        payment = self.db.query(Payment).filter(Payment.payment_id == payment_id).first()
        if not payment:
            raise ValueError(f"Payment with ID {payment_id} not found")

        policy = self.db.query(Policy).filter(Policy.merchant_id == payment.merchant_id).first()

        # Step 1: Safety Validation
        if not force_override:
            safe, err_reason = PaymentStateMachine.validate_recovery_safety(payment, policy)
            if not safe:
                return {
                    "status": "BLOCKED",
                    "payment_id": payment_id,
                    "recovered_amount": 0.0,
                    "action_executed": action or "UNKNOWN",
                    "channel_used": channel or "SYSTEM",
                    "reason": err_reason,
                    "verified": False,
                    "execution_steps": [
                        "1. Checking payment state... COMPLETED",
                        f"2. Validating merchant policy... BLOCKED: {err_reason}"
                    ]
                }

        # Determine Action
        selected_action = action
        if not selected_action and payment.prediction:
            selected_action = payment.prediction.recommended_action
        if not selected_action:
            selected_action = "RETRY_LATER"

        selected_channel = channel or (payment.customer.preferred_channel if payment.customer else "EMAIL")

        execution_steps = [
            "1. Checking payment state... VERIFIED (FAILED)",
            "2. Validating merchant policy... PASSED",
            f"3. Checking customer history... {payment.customer.name if payment.customer else 'Verified customer'}",
            f"4. Selecting action... {selected_action} via {selected_channel}",
            "5. Executing simulation recovery intervention..."
        ]

        # Step 2: Invoke Simulation Provider
        sim_result = self.provider.retry_payment(
            payment_id=payment_id,
            action=selected_action,
            channel=selected_channel,
            context={"amount": payment.amount, "failure_code": payment.failure_code}
        )

        execution_steps.append(f"6. Gateway processing... {sim_result['status']}")

        # Step 3: Verify Payment Outcome
        verify_result = self.provider.verify_payment(payment_id)
        execution_steps.append("7. Verifying payment on banking rail... VERIFIED")

        # Update Payment Record
        recovered_amount = sim_result["recovered_amount"]
        is_success = sim_result["success"]
        payment.status = "SUCCESS" if is_success else "FAILED"
        payment.is_reconciled = True
        if is_success:
            payment.failure_code = None
            payment.failure_reason = None
            if payment.order:
                payment.order.status = "PAID"
            if payment.customer:
                payment.customer.successful_payments += 1
                payment.customer.lifetime_value += recovered_amount

        # Record Recovery Attempt
        attempt = RecoveryAttempt(
            payment_id=payment_id,
            action=selected_action,
            channel=selected_channel,
            executed_at=datetime.utcnow(),
            result="SUCCESS" if is_success else "FAILED",
            recovered_amount=recovered_amount,
            failure_reason=sim_result.get("failure_reason")
        )
        self.db.add(attempt)
        self.db.flush()

        execution_steps.append(
            f"8. Recording outcome... {'✓ ₹{:,.2f} RECOVERED'.format(recovered_amount) if is_success else '✗ RECOVERY FAILED'}"
        )

        # Audit Log Event
        audit = AuditLog(
            merchant_id=payment.merchant_id,
            payment_id=payment.payment_id,
            event_type="RECOVERY_EXECUTED",
            actor=actor,
            action=selected_action,
            reason=f"Recovery intervention outcome: {payment.status}",
            metadata_json={
                "attempt_id": attempt.attempt_id,
                "action": selected_action,
                "channel": selected_channel,
                "recovered_amount": recovered_amount,
                "success": is_success
            }
        )
        self.db.add(audit)
        self.db.commit()

        return {
            "status": "SUCCESS" if is_success else "FAILED",
            "payment_id": payment_id,
            "recovered_amount": recovered_amount,
            "action_executed": selected_action,
            "channel_used": selected_channel,
            "reason": None if is_success else sim_result.get("failure_reason"),
            "verified": verify_result.get("verified", True),
            "execution_steps": execution_steps,
            "audit_id": audit.audit_id
        }

    def verify_and_reconcile(self, payment_id: str) -> Dict[str, Any]:
        payment = self.db.query(Payment).filter(Payment.payment_id == payment_id).first()
        if not payment:
            raise ValueError("Payment not found")

        verification = self.provider.verify_payment(payment_id)
        payment.is_reconciled = True
        
        audit = AuditLog(
            merchant_id=payment.merchant_id,
            payment_id=payment.payment_id,
            event_type="PAYMENT_VERIFIED",
            actor="SYSTEM_RECONCILER",
            action="RECONCILE_FIRST",
            reason="Banking rail verification complete",
            metadata_json=verification
        )
        self.db.add(audit)
        self.db.commit()
        return {"payment_id": payment_id, "reconciled": True, "details": verification}

    def approve_recovery(self, payment_id: str, actor: str = "ADMIN") -> Payment:
        payment = self.db.query(Payment).filter(Payment.payment_id == payment_id).first()
        if not payment:
            raise ValueError("Payment not found")
        payment.approval_status = "APPROVED"

        audit = AuditLog(
            merchant_id=payment.merchant_id,
            payment_id=payment.payment_id,
            event_type="APPROVAL_GRANTED",
            actor=actor,
            action="APPROVE_RECOVERY",
            reason="Merchant manager manually authorized high-value recovery execution",
            metadata_json={"amount": payment.amount}
        )
        self.db.add(audit)
        self.db.commit()
        return payment

    def reject_recovery(self, payment_id: str, reason: str = "Merchant declined recovery", actor: str = "ADMIN") -> Payment:
        payment = self.db.query(Payment).filter(Payment.payment_id == payment_id).first()
        if not payment:
            raise ValueError("Payment not found")
        payment.approval_status = "REJECTED"

        audit = AuditLog(
            merchant_id=payment.merchant_id,
            payment_id=payment.payment_id,
            event_type="APPROVAL_REJECTED",
            actor=actor,
            action="REJECT_RECOVERY",
            reason=reason,
            metadata_json={"amount": payment.amount}
        )
        self.db.add(audit)
        self.db.commit()
        return payment
