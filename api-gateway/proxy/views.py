"""
API Gateway Proxy View
======================
Forwards every  GET / POST / PUT / PATCH / DELETE  request from
  /api/<service>/<path>
to the registered downstream service:
  <SERVICE_URL>/api/<service>/<path>

Headers listed in settings.PROXY_HEADERS_PASSTHROUGH are forwarded as-is.
Query parameters are also forwarded unchanged.
"""
import logging
import requests
from requests.exceptions import RequestException

from django.conf import settings
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)

TIMEOUT = 30  # seconds


def _forward_headers(request) -> dict:
    """Build a headers dict from the incoming request, keeping only safe headers."""
    allowed = settings.PROXY_HEADERS_PASSTHROUGH
    headers = {}
    for key, value in request.headers.items():
        if key.lower() in allowed:
            headers[key] = value
    return headers


class GatewayProxyView(APIView):
    """
    Single catch-all view that proxies requests to downstream services.

    URL pattern:  /api/<service>/<path>
    Forwarded to: <SERVICE_URL>/api/<service>/<path>
    """

    def dispatch(self, request, service: str, path: str = "", *args, **kwargs):
        registry = settings.SERVICE_REGISTRY
        if service not in registry:
            return JsonResponse(
                {"error": f"Unknown service: '{service}'"},
                status=status.HTTP_404_NOT_FOUND,
            )
        self._service = service
        self._upstream_base = registry[service]
        return super().dispatch(request, service=service, path=path, *args, **kwargs)

    def _proxy(self, request, path: str):
        upstream_url = f"{self._upstream_base}/api/{self._service}/{path}"
        method = request.method.lower()
        headers = _forward_headers(request)
        params = request.query_params.dict()

        try:
            if method in ("post", "put", "patch"):
                upstream_resp = getattr(requests, method)(
                    upstream_url,
                    json=request.data,
                    headers=headers,
                    params=params,
                    timeout=TIMEOUT,
                )
            else:
                upstream_resp = getattr(requests, method)(
                    upstream_url,
                    headers=headers,
                    params=params,
                    timeout=TIMEOUT,
                )
        except RequestException as exc:
            logger.error("Gateway proxy error [%s → %s]: %s", self._service, upstream_url, exc)
            return Response(
                {"error": f"Service '{self._service}' is temporarily unavailable."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            data = upstream_resp.json()
        except ValueError:
            data = {"detail": upstream_resp.text}

        return Response(data, status=upstream_resp.status_code)

    def get(self, request, service, path=""):
        return self._proxy(request, path)

    def post(self, request, service, path=""):
        return self._proxy(request, path)

    def put(self, request, service, path=""):
        return self._proxy(request, path)

    def patch(self, request, service, path=""):
        return self._proxy(request, path)

    def delete(self, request, service, path=""):
        return self._proxy(request, path)


class HealthCheckView(APIView):
    """GET /health/ — returns health status of all downstream services."""

    def get(self, request):
        results = {}
        for name, url in settings.SERVICE_REGISTRY.items():
            try:
                resp = requests.get(f"{url}/admin/", timeout=3)
                results[name] = "healthy" if resp.status_code < 500 else "degraded"
            except RequestException:
                results[name] = "unreachable"
        overall = "healthy" if all(v == "healthy" for v in results.values()) else "degraded"
        return Response({"status": overall, "services": results})
