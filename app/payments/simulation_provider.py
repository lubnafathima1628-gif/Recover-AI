import uuid
import time
import random
from typing import Dict, Any, Optional
from datetime import datetime
from backend.app.payments.payment_provider import PaymentProvider

class SimulationPaymentProvider(PaymentProvider):
    """
    Realistic in-memory deterministic Payment Provider Simulation.
    Clearly operates in SIMULATION MODE for local zero-dependency testing.
    """

    def __init__(self, seed: Optional[int] = 42):
        self.mode = "SIMULATION_MODE"
        self._rng = random.Random(seed)
        self._transactions: Dict[str, Dict[str, Any]] = {}

    def create_payment(
        self,
        amount: float,
        currency: str = "INR",
        customer_info: Optional[Dict[str, Any]] = None,
        payment_method: str = "UPI",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Simulates initiating a payment with realistic success/failure distribution."""
        payment_id = f"pay_sim_{uuid.uuid4().hex[:12]}"
        
        # Determine failure reason or success based on realistic rates or metadata override
        forced_failure = metadata.get("force_failure_reason") if metadata else None
        
        if forced_failure:
            status = "FAILED"
            failure_code = forced_failure
            failure_message = self._get_failure_message(forced_failure)
        else:
            # 70% success, 30% initial failure for incoming live synthetic feed
            is_success = self._rng.random() < 0.70
            if is_success:
                status = "SUCCESS"
                failure_code = None
                failure_message = None
            else:
                status = "FAILED"
                failure_code = self._rng.choice([
                    "TEMPORARY_NETWORK",
                    "INVALID_PAYMENT_METHOD",
                    "AUTHENTICATION_FAILURE",
                    "INSUFFICIENT_FUNDS",
                    "RISK_RELATED",
                    "DUPLICATE_ALREADY_PAID"
                ])
                failure_message = self._get_failure_message(failure_code)

        payload = {
            "payment_id": payment_id,
            "external_payment_id": f"sim_ext_{uuid.uuid4().hex[:10]}",
            "amount": amount,
            "currency": currency,
            "payment_method": payment_method,
            "status": status,
            "failure_code": failure_code,
            "failure_reason": failure_message,
            "customer": customer_info or {},
            "created_at": datetime.utcnow().isoformat(),
            "simulation_mode": True,
            "history": [
                {
                    "step": "INITIATED",
                    "status": "PROCESSING",
                    "timestamp": datetime.utcnow().isoformat()
                },
                {
                    "step": "GATEWAY_RESPONSE",
                    "status": status,
                    "failure_code": failure_code,
                    "timestamp": datetime.utcnow().isoformat()
                }
            ]
        }
        
        self._transactions[payment_id] = payload
        return payload

    def get_payment(self, payment_id: str) -> Dict[str, Any]:
        if payment_id in self._transactions:
            return self._transactions[payment_id]
        return {
            "payment_id": payment_id,
            "status": "UNKNOWN",
            "simulation_mode": True,
            "message": "Simulated payment not found in active session cache"
        }

    def retry_payment(
        self,
        payment_id: str,
        action: str,
        channel: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Simulates executing a recovery intervention with calibrated success dynamics.
        """
        current_data = self._transactions.get(payment_id, {})
        failure_code = current_data.get("failure_code", "TEMPORARY_NETWORK")
        amount = current_data.get("amount", 25000.0)

        # Baseline recovery rates per intervention action & failure code
        success_probability = 0.65
        
        if action == "RETRY_LATER":
            if failure_code == "TEMPORARY_NETWORK":
                success_probability = 0.88
            elif failure_code == "AUTHENTICATION_FAILURE":
                success_probability = 0.45
            else:
                success_probability = 0.30
        elif action == "ALTERNATE_PAYMENT_METHOD":
            if failure_code in ["INVALID_PAYMENT_METHOD", "INSUFFICIENT_FUNDS"]:
                success_probability = 0.82
            else:
                success_probability = 0.70
        elif action == "PAYMENT_LINK":
            success_probability = 0.76
        elif action == "RETRY_OR_UPDATE_METHOD":
            success_probability = 0.74
        elif action == "RECONCILE_FIRST":
            # Reconcile reveals the payment was captured on banking rails
            success_probability = 0.92
        elif action == "ESCALATE":
            success_probability = 0.50
        elif action == "NO_ACTION":
            return {
                "success": False,
                "status": "FAILED",
                "recovered_amount": 0.0,
                "action": "NO_ACTION",
                "reason": "Intervention cost exceeds expected recovery value",
                "simulation_mode": True
            }

        # Deterministic check if seed is present in context, else RNG
        rnd_val = context.get("fixed_random") if context and "fixed_random" in context else self._rng.random()
        is_recovered = rnd_val < success_probability

        new_status = "SUCCESS" if is_recovered else "FAILED"
        recovered_amount = amount if is_recovered else 0.0

        result = {
            "success": is_recovered,
            "status": new_status,
            "recovered_amount": recovered_amount,
            "action_executed": action,
            "channel_used": channel or "SYSTEM",
            "executed_at": datetime.utcnow().isoformat(),
            "simulation_mode": True,
            "failure_reason": None if is_recovered else f"Simulated retry attempt failed after {action}",
            "external_reference": f"sim_recov_{uuid.uuid4().hex[:8]}"
        }

        if payment_id in self._transactions:
            self._transactions[payment_id]["status"] = new_status
            self._transactions[payment_id]["history"].append({
                "step": f"RECOVERY_ACTION_{action}",
                "status": new_status,
                "recovered_amount": recovered_amount,
                "timestamp": datetime.utcnow().isoformat()
            })

        return result

    def verify_payment(self, payment_id: str) -> Dict[str, Any]:
        """
        Verifies actual status on simulated banking network.
        Ensures safe reconciliation before retrying ambiguous transactions.
        """
        tx = self._transactions.get(payment_id)
        current_status = tx.get("status", "SUCCESS") if tx else "SUCCESS"
        
        return {
            "payment_id": payment_id,
            "verified": True,
            "verified_status": current_status,
            "gateway_reconciled": True,
            "banking_rail_sync_time": datetime.utcnow().isoformat(),
            "simulation_mode": True
        }

    def refund_payment(self, payment_id: str, amount: Optional[float] = None) -> Dict[str, Any]:
        return {
            "payment_id": payment_id,
            "status": "REFUNDED",
            "refund_id": f"rfnd_sim_{uuid.uuid4().hex[:10]}",
            "amount": amount,
            "simulation_mode": True
        }

    def get_payment_status(self, payment_id: str) -> str:
        tx = self._transactions.get(payment_id)
        return tx.get("status", "UNKNOWN") if tx else "UNKNOWN"

    def _get_failure_message(self, code: str) -> str:
        messages = {
            "TEMPORARY_NETWORK": "Bank server timeout during authorization handshake",
            "INVALID_PAYMENT_METHOD": "Card expired or invalid VPA address",
            "AUTHENTICATION_FAILURE": "3D Secure OTP verification failed / expired",
            "INSUFFICIENT_FUNDS": "Insufficient account balance on customer banking account",
            "RISK_RELATED": "Transaction flagged by fraud heuristic engine",
            "DUPLICATE_ALREADY_PAID": "Simultaneous duplicate debit detected on banking rail",
            "UNKNOWN": "Uncategorized gateway decline response"
        }
        return messages.get(code, "Generic payment gateway error")

# Default global simulation provider instance
simulation_provider = SimulationPaymentProvider()
