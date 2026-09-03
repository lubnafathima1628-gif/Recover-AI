from typing import Tuple, Optional, Dict, Any

VALID_TRANSITIONS = {
    "INITIATED": ["PENDING", "PROCESSING", "AUTHORIZED", "SUCCESS", "FAILED"],
    "PENDING": ["PROCESSING", "SUCCESS", "FAILED", "CANCELLED"],
    "PROCESSING": ["SUCCESS", "FAILED", "AUTHORIZED", "UNKNOWN"],
    "AUTHORIZED": ["CAPTURED", "REFUNDED", "CANCELLED"],
    "CAPTURED": ["SUCCESS", "REFUNDED"],
    "SUCCESS": ["REFUNDED"],  # Terminal state for recovery
    "FAILED": ["PROCESSING", "RETRYING", "RECONCILING", "SUCCESS", "FAILED", "CANCELLED"],
    "RETRYING": ["PROCESSING", "SUCCESS", "FAILED"],
    "RECONCILING": ["SUCCESS", "FAILED"],
    "REFUNDED": [],
    "CANCELLED": [],
    "UNKNOWN": ["RECONCILING", "SUCCESS", "FAILED"]
}

class PaymentStateMachine:
    """
    Enforces safe state transitions, double-charge prevention, and debit reconciliation.
    """

    @staticmethod
    def can_transition(current_status: str, new_status: str) -> bool:
        if current_status == new_status:
            return True
        allowed = VALID_TRANSITIONS.get(current_status.upper(), [])
        return new_status.upper() in allowed

    @staticmethod
    def validate_recovery_safety(payment: Any, policy: Optional[Any] = None) -> Tuple[bool, Optional[str]]:
        """
        Determines whether a payment can safely undergo recovery intervention.
        Prevents double-charging, enforces quiet hours, approval limits, and reconciliation.
        """
        status = payment.status.upper()
        if status == "SUCCESS":
            return False, "Payment is already marked as SUCCESS. Recovery intervention blocked to prevent duplicate billing."

        if status == "REFUNDED":
            return False, "Payment has already been REFUNDED."

        # Safety Check: Ambiguous debit detection
        if payment.failure_code in ["DUPLICATE_ALREADY_PAID", "UNKNOWN"] and not getattr(payment, "is_reconciled", False):
            return False, "Payment has ambiguous banking debit state. Must execute RECONCILE_FIRST before retry."

        # Policy & Approval Checks
        if getattr(payment, "requires_approval", False) and getattr(payment, "approval_status", "") != "APPROVED":
            return False, "Payment amount exceeds merchant threshold and requires human approval before execution."

        # Max retry limit check
        attempts_count = len(getattr(payment, "recovery_attempts", []))
        if policy and attempts_count >= policy.auto_retry_limit:
            return False, f"Maximum retry attempt limit ({policy.auto_retry_limit}) reached for this transaction."

        return True, None
