from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework import authentication, exceptions, permissions, throttling

from farmer.models import Farmer
from sensors.constants import API_KEY_HEADER


class ApiKeyAuthentication(authentication.BaseAuthentication):
    """Resolves the farmer behind a field sensor from the secret shown on their profile.

    `request.auth` carries the `Farmer`, so the ingest view scopes sensors by owner without
    going back through `request.user`.
    """

    def authenticate(self, request):
        api_key = request.headers.get(API_KEY_HEADER)
        if not api_key:
            return None

        farmer = Farmer.objects.select_related('user').filter(api_secret=api_key).first()
        if farmer is None:
            raise exceptions.AuthenticationFailed('Invalid API key.')
        return (farmer.user, farmer)

    def authenticate_header(self, request):
        # Without a challenge DRF downgrades a missing key from 401 to 403.
        return API_KEY_HEADER


class IsActiveApiKeyOwner(permissions.BasePermission):
    message = 'This API key belongs to an inactive account.'

    def has_permission(self, request, view):
        farmer = request.auth
        if not isinstance(farmer, Farmer):
            return False
        return farmer.is_active and request.user.is_active


class ApiKeyRateThrottle(throttling.SimpleRateThrottle):
    """Counts per API key rather than per IP: every sensor of a farm can sit behind one NAT."""

    scope = 'sensor_ingest'

    def get_cache_key(self, request, view):
        return self.cache_format % {'scope': self.scope, 'ident': request.auth.pk}


class ApiKeyAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = 'sensors.authentication.ApiKeyAuthentication'
    name = 'ApiKeyAuth'

    def get_security_definition(self, auto_schema):
        return {'type': 'apiKey', 'in': 'header', 'name': API_KEY_HEADER}
