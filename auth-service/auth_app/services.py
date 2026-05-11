import requests
from django.conf import settings


class CartServiceClient:
    @staticmethod
    def create_cart_for_customer(customer_id):
        cart_url = getattr(settings, "CART_SERVICE_URL", "http://cart-service:8000")
        try:
            response = requests.post(
                f"{cart_url}/internal/carts/create/",
                json={"customer_id": customer_id},
                timeout=5,
            )
            return response.status_code in (200, 201)
        except requests.RequestException:
            return False
