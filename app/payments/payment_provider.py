from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class PaymentProvider(ABC):
    """
    Abstract Payment Provider interface.
    Allows swappable implementations (e.g. Simulation, Gateway Adapters).
    """

    @abstractmethod
    def create_payment(
        self,
        amount: float,
        currency: str,
        customer_info: Dict[str, Any],
        payment_method: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Initiates a payment and returns gateway response."""
        pass

    @abstractmethod
    def get_payment(self, payment_id: str) -> Dict[str, Any]:
        """Retrieves payment state and details from provider."""
        pass

    @abstractmethod
    def retry_payment(
        self,
        payment_id: str,
        action: str,
        channel: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Executes a recovery retry or alternate payment method dispatch."""
        pass

    @abstractmethod
    def verify_payment(self, payment_id: str) -> Dict[str, Any]:
        """Performs state verification with simulated banking network."""
        pass

    @abstractmethod
    def refund_payment(self, payment_id: str, amount: Optional[float] = None) -> Dict[str, Any]:
        """Processes a simulated refund."""
        pass

    @abstractmethod
    def get_payment_status(self, payment_id: str) -> str:
        """Returns standard status: SUCCESS, FAILED, PENDING, AUTHORIZED, CAPTURED, CANCELLED, REFUNDED, UNKNOWN."""
        pass
