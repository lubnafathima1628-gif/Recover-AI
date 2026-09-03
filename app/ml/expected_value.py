from typing import Dict, Any

class ExpectedValueEngine:
    """
    Computes Expected Recovery Value (EV) to prioritize interventions
    by direct net financial return:
    
    EV = (Transaction Amount * Recovery Probability) - Intervention Cost
    """

    # Estimated costs per intervention channel/action in INR
    ACTION_COSTS = {
        "RETRY_LATER": 15.0,                  # Serverless background retry compute
        "ALTERNATE_PAYMENT_METHOD": 45.0,    # In-app interactive modal / push notification
        "PAYMENT_LINK": 65.0,                # SMS & Email branded payment gateway link
        "RETRY_OR_UPDATE_METHOD": 50.0,      # Subscription mandate update
        "RECONCILE_FIRST": 25.0,             # Banking rail API query
        "MERCHANT_APPROVAL": 120.0,          # Human operator review overhead
        "ESCALATE": 100.0,                   # Fraud analyst review
        "NO_ACTION": 0.0                     # Zero cost
    }

    @classmethod
    def calculate_expected_value(
        cls,
        amount: float,
        probability: float,
        action: str = "RETRY_LATER",
        custom_cost: float = None
    ) -> float:
        cost = custom_cost if custom_cost is not None else cls.ACTION_COSTS.get(action, 50.0)
        ev = (amount * probability) - cost
        return round(max(0.0, ev), 2)

    @classmethod
    def get_intervention_cost(cls, action: str) -> float:
        return cls.ACTION_COSTS.get(action, 50.0)

expected_value_engine = ExpectedValueEngine()
