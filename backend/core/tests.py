from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.utils import timezone

from core.middleware import AdminTimeZoneMiddleware


@override_settings(TIME_ZONE='UTC', ADMIN_TIME_ZONE='America/Bogota', ADMIN_TIME_ZONE_PATH='/django-admin/')
class AdminTimeZoneMiddlewareTests(SimpleTestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.seen_time_zones = []

        def get_response(request):
            self.seen_time_zones.append(timezone.get_current_timezone_name())
            return HttpResponse()

        self.middleware = AdminTimeZoneMiddleware(get_response)

    def test_the_django_admin_renders_in_the_admin_time_zone(self):
        self.middleware(self.factory.get('/django-admin/sensors/weathersnapshot/'))

        self.assertEqual(self.seen_time_zones, ['America/Bogota'])

    def test_the_api_keeps_the_default_time_zone(self):
        self.middleware(self.factory.get('/api/sensors/farms/1/stations/'))

        self.assertEqual(self.seen_time_zones, ['UTC'])

    def test_the_admin_time_zone_does_not_leak_into_the_next_request(self):
        self.middleware(self.factory.get('/django-admin/'))
        self.middleware(self.factory.get('/api/farm/plots/'))

        self.assertEqual(self.seen_time_zones, ['America/Bogota', 'UTC'])
