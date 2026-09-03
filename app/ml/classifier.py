from typing import Dict, Any

class FailureClassifier:
    """
    Classifies raw gateway failure codes, bank decline strings,
    and HTTP transaction anomalies into standardized failure categories.
    """

    CATEGORIES = [
        "TEMPORARY_NETWORK",
        "INVALID_PAYMENT_METHOD",
        "AUTHENTICATION_FAILURE",
        "INSUFFICIENT_FUNDS",
        "RISK_RELATED",
        "DUPLICATE_ALREADY_PAID",
        "UNKNOWN"
    ]

    KEYWORD_MAPPINGS = {
        "TEMPORARY_NETWORK": [
            "timeout", "network", "bank_unreachable", "gateway_timeout", "e_conn_reset",
            "rail_busy", "server_error", "504", "502", "503", "switch_down", "down"
        ],
        "INVALID_PAYMENT_METHOD": [
            "expired", "invalid_vpa", "card_blocked", "invalid_cvv", "no_such_account",
            "invalid_pin", "format_error", "unsupported_card", "dormant_account", "invalid"
        ],
        "AUTHENTICATION_FAILURE": [
            "otp", "3ds", "auth", "wrong_otp", "mismatch",
            "user_cancelled_auth", "token_expired", "biometric"
        ],
        "INSUFFICIENT_FUNDS": [
            "low_balance", "insufficient", "exceeds_limit", "credit_limit_reached",
            "daily_limit_exceeded", "balance_check_failed", "balance"
        ],
        "RISK_RELATED": [
            "fraud", "risk", "velocity_exceeded", "blacklisted", "sanctioned",
            "anomaly", "device_fingerprint_mismatch", "suspect"
        ],
        "DUPLICATE_ALREADY_PAID": [
            "duplicate", "already_processed", "idempotency_conflict", "order_already_paid", "already_paid"
        ]
    }

    @classmethod
    def classify(cls, failure_code: str, raw_message: str = "") -> str:
        if not failure_code and not raw_message:
            return "UNKNOWN"

        norm_code = (failure_code or "").upper().strip()
        if norm_code in cls.CATEGORIES:
            return norm_code

        search_text = f"{failure_code} {raw_message}".lower()

        for category, keywords in cls.KEYWORD_MAPPINGS.items():
            for kw in keywords:
                if kw in search_text:
                    return category

        return "UNKNOWN"

classifier = FailureClassifier()
