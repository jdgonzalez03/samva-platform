from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import timezone


class AdminTimeZoneMiddleware:
    """Shows dates in the Django admin in `ADMIN_TIME_ZONE`.

    Only the admin pages switch zone: the API keeps serializing in `TIME_ZONE` (UTC), which
    is the contract the frontend and the exports rely on. Wagtail's admin picks its zone
    from each user's profile (Account > Preferences) and overrides this one anyway.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.admin_time_zone = ZoneInfo(settings.ADMIN_TIME_ZONE)

    def __call__(self, request):
        if not request.path.startswith(settings.ADMIN_TIME_ZONE_PATH):
            return self.get_response(request)

        with timezone.override(self.admin_time_zone):
            return self.get_response(request)
