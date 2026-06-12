import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class CartServiceClient:
    """HTTP client for inter-service communication with cart-service."""

    BASE_URL = settings.CART_SERVICE_URL

    @classmethod
    def create_cart_for_customer(cls, customer_id: int) -> dict:
        try:
            response = requests.post(
                f"{cls.BASE_URL}/internal/carts/create/",
                json={"customer_id": customer_id},
                timeout=5,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error("Failed to create cart for customer %s: %s", customer_id, e)
            return {}
