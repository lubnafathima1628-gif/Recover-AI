from typing import Dict, Any, Tuple, Optional
from datetime import datetime

class DecisionEngine:
    """
    Intelligent Multi-Factor Recovery Decision Engine.
    Matches failure diagnostics and expected recovery with optimal merchant-compliant action.
    """

    @staticmethod
    def select_action(
        amount: float,
        failure_category: str,
        probability: float,
        expected_value: float,
        policy: Optional[Any] = None,
        is_subscription: bool = False,
        is_ambiguous_debit: bool = False
    ) -> Tuple[str, str, bool]:
        """
        Returns: (recommended_action, decision_reason, requires_approval)
        """
        # Rule 1: Safety check - Ambiguous debit / potential duplicate
        if is_ambiguous_debit or failure_category == "DUPLICATE_ALREADY_PAID":
            return (
                "RECONCILE_FIRST",
                "Banking state ambiguous; verification required before retrying to prevent double-debit.",
                False
            )

        # Rule 2: Risk-related issues
        if failure_category == "RISK_RELATED":
            return (
                "ESCALATE",
                "Transaction flagged by risk heuristic. Escalated to fraud & compliance team.",
                True
            )

        # Rule 3: Check Merchant Blocked Categories
        if policy and policy.blocked_failure_categories:
            if failure_category in policy.blocked_failure_categories:
                return (
                    "ESCALATE",
                    f"Failure category {failure_category} is blocked by merchant policy rules.",
                    True
                )

        # Rule 4: High Value Threshold -> Merchant Approval
        approval_threshold = getattr(policy, "approval_threshold", 10000.0) if policy else 10000.0
        if amount >= approval_threshold:
            return (
                "MERCHANT_APPROVAL",
                f"Transaction amount (₹{amount:,.2f}) exceeds merchant auto-recovery threshold (₹{approval_threshold:,.2f}). Human sign-off required.",
                True
            )

        # Rule 5: Low Expected Value -> No Action
        if expected_value < 100.0 or probability < 0.15:
            return (
                "NO_ACTION",
                f"Expected recovery value (₹{expected_value:,.2f}) is too low relative to customer contact friction.",
                False
            )

        # Rule 6: Technical / Network Failure with High Probability
        if failure_category == "TEMPORARY_NETWORK":
            return (
                "RETRY_LATER",
                "Temporary bank network timeout detected. Automated background retry scheduled for optimal success window.",
                False
            )

        # Rule 7: Invalid Payment Method (e.g. Expired card, invalid VPA)
        if failure_category == "INVALID_PAYMENT_METHOD":
            return (
                "ALTERNATE_PAYMENT_METHOD",
                "Payment method invalid or expired. Prompt customer with secondary payment rails (UPI / NetBanking).",
                False
            )

        # Rule 8: Authentication / OTP Drop-off
        if failure_category == "AUTHENTICATION_FAILURE":
            return (
                "PAYMENT_LINK",
                "OTP verification failed. Dispatch seamless one-click 1-click recovery payment link via preferred channel.",
                False
            )

        # Rule 9: Subscription renewal
        if is_subscription or failure_category == "INSUFFICIENT_FUNDS":
            return (
                "RETRY_OR_UPDATE_METHOD",
                "Mandate renewal failed or balance insufficient. Request payment method update with intelligent backup retry.",
                False
            )

        # Default fallback
        return (
            "PAYMENT_LINK",
            "Dispatched contextual smart recovery link to customer.",
            False
        )

decision_engine = DecisionEngine()
