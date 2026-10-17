# Backend Guidelines

## Dev environment
- Backend development runs on `backend/docker-compose.yml` (project "backend": postgres, rabbitmq `broker`, mosquitto `mqtt`, backend, celery, flower): `cd backend && docker compose up -d backend`, then the `make` targets in `backend/makefile` exec into that stack. The root `docker-compose.dev.yml` exists only to simulate the production deployment config — never use it for day-to-day backend development.
- LoRaWAN readings arrive from The Things Network's MQTT broker, never from the gateway directly (ADR 0002): the `mqtt` service (Mosquitto, `backend/mosquitto/mosquitto.conf`, anonymous on `127.0.0.1:1883`) is a dev/simulation broker only, fed by `make simulate-lora`; `MQTT_SOURCE=local|ttn` picks the source for `mqtt_ingest` and `make mqtt-restart` applies a change; `broker` is RabbitMQ for Celery, not MQTT.
- The assistant's LLM runs in the `ollama` service; `make assistant-model` pulls `OLLAMA_MODEL` into its volume once (the endpoint answers 503 until then). In the container it runs on CPU (~30 s per model call on a Mac); on macOS set `OLLAMA_URL=http://host.docker.internal:11434` to use a native Ollama on the GPU (~1–3 s) — host port 11434 may already belong to that native Ollama, so reach the container's from inside the network (`http://ollama:11434`).
- Every seeded user in `accounts/fixtures/initial_users.json` has the password `Test@1234!` (the fixture ships its hash), so `make loaddata` leaves login and the e2e suite working; if that hash ever changes, regenerate it in-container (`make_password` via `make shell`) and keep `e2e/frontend/helpers.ts` + `e2e/README.md` in sync.

## Time zones
- Keep `TIME_ZONE = 'UTC'`: DRF serializes datetimes in it, so changing it rewrites every API timestamp (`Z` → `-05:00`) and the dates in export filenames; local time in the Django admin comes from `ADMIN_TIME_ZONE` via `core.middleware.AdminTimeZoneMiddleware`, and Wagtail's admin uses each user's profile zone (Account › Preferences), falling back to `TIME_ZONE` (UTC) when it is blank.
- A model `__str__` that shows a datetime formats `timezone.localtime(...)`, never the raw field: the stored value is UTC, so formatting it directly ignores the admin's active zone (Wagtail list titles come from `__str__`).

## Django Apps

Do not set `default_auto_field` in individual `AppConfig` classes. The project already sets `DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'` globally in `settings/common.py`, so per-app overrides are redundant.

## Readability
- Prefer guard clauses (early returns) over nested `if`/`else` branching — handle the special case and `return`/`raise` early, keeping the main path unindented; avoid multi-line conditional expressions where a plain `if` block reads clearer.
- Name things explicitly — no cryptic abbreviations (`re`, `cfg`, `tmp`, `val`, `usr`, `qs`). Write the full word: `username_regex`/`username_pattern`, `config`, `user`, `queryset`. A name should read unambiguously without the reader guessing what it stands for.


## DRF API layer

- API views live in `<app>/api.py` (not `views.py`), serializers in `<app>/serializers.py`, routes in `<app>/urls.py` with `app_name`; mount in `backend/urls.py` as `path('api/<app>/', include((<app>_urlpatterns, '<app>')))` — the namespace tuple is what makes `reverse('<app>:<name>')` work in tests, since the plain list import drops `app_name`.
- `<app>/api.py` holds the HTTP surface and nothing else: module constants go to `<app>/constants.py`, helper functions and streaming generators to `<app>/utils.py`, and a helper used by more than one app to `core/utils.py`. Pagination classes stay next to the views that declare them.
- Every view sets `permission_classes` explicitly: there is no `DEFAULT_PERMISSION_CLASSES`, so the DRF default is `AllowAny`.
- Scope user-owned querysets through a lookup (`Farm.objects.filter(owner__user=self.request.user)`), never `request.user.farmer` — a user without the related row raises `RelatedObjectDoesNotExist` (500) instead of returning an empty list.
- Nested resources resolve the parent with `get_owned_or_404` (`core/utils.py`) so someone else's id 404s instead of returning `[]`, which would leak its existence; Django's `get_object_or_404` names the model in the body, which distinguishes a row that exists from one that never did.
- Any model exposed through a list endpoint needs `Meta.ordering` — without it the page order is unstable and DRF warns.
- Any paginated endpoint orders on a column set that ends in a unique tie-break (`.order_by('-recorded_at', '-id')`). Rows sharing the sort value are otherwise free to swap between the page-1 and page-2 queries, so a row silently repeats or vanishes; `Meta.ordering` alone does not fix it.
- Never use `?format=` as your own discriminator: DRF reserves it (`URL_FORMAT_OVERRIDE`), so it triggers content negotiation for a renderer of that name and 404s with `Invalid format`. Give each output its own route (`export/csv/`, `export/json/`).
- Geometry fields (`PointField`/`PolygonField`) do not serialize through a plain `ModelSerializer`; exposing them needs `djangorestframework-gis`, which is not installed yet.
- Rich `@extend_schema` docs (long descriptions, `OpenApiExample`s, per-status `OpenApiResponse`s) live in `<app>/openapi.py`, not in `api.py`; build limits quoted in prose from the real constants/settings so the published docs cannot drift.
- A custom `BaseAuthentication` must implement `authenticate_header`, or DRF answers a request with missing credentials with 403 instead of 401.
- There is no `CACHES` setting, so throttle counters live in the per-process `LocMemCache`: limits are per gunicorn worker, and the counts outlive each test's transaction — call `cache.clear()` in `setUp` of any throttled test case.

## Tests
- Run a subset with `make test ARGS="<app>.tests.<Class>"` instead of calling `manage.py test` directly.
- `make test` failing with "test database already exists" means another session is running the suite on the same Postgres — wait and retry; never answer `yes` to clobber it.
- `patch()` targets the module where a name is *used*, not where it is defined: `from x import CONST` binds the value into the consumer's namespace at import time, so patching `x.CONST` leaves the consumer untouched. Moving a constant to `constants.py` therefore breaks every `patch('<old_module>.CONST')` — repoint them at the module that imports it.
- A test that consumes `random` without an explicit seed is not deterministic — it is a coin flip that will fail in someone else's run. Seed it, and make the assertion robust as well: a seed fixes the noise but not a timestamp grid anchored on `now()`, so assert over a window or an aggregate rather than a single-sample `argmax`.
- Tests that reach `close_old_connections()` (e.g. the `mqtt_ingest` message loop) must patch it: inside a `TestCase` it closes the test's own connection.
- Check dev data through the REST API (curl + JWT) rather than piping a script into `make shell`, which hangs.

## Assistant (LLM tools)
- Tests never call Ollama: patch `assistant.utils.ollama.chat` (the loop) or `assistant.ollama.requests.post` (the client) and script the model's turns as `tool_calls` / text messages.
- A tool takes `user` first and scopes every query to it; it raises `ToolError` for anything the model should read and explain, and returns plain JSON numbers (not `Decimal`), which a small model reads more reliably than strings.
- Adding a tool means adding the function to `TOOLS` and its schema to `TOOL_SCHEMAS` (a test checks both match) plus its label in `frontend/layers/assistant/i18n/locales/*.json`.

## Fuzzy models (scikit-fuzzy)
- Build the `ControlSystem` per prediction, never cache it: skfuzzy stores every simulation's state on the system's own term objects keyed by input values, so a shared system grows without bound and is not thread-safe (building costs ~80 ms).
- The model's membership functions and rules come from an agronomic study: any change must keep the golden grid in `predictions/tests.py` green or be agreed with its authors.

## Signals

Always import signals in `AppConfig.ready()` using the relative import syntax:

```python
def ready(self):
    from . import signals
```

Never use absolute imports (`import accounts.signals`) or `# noqa` comments. The IDE hint about `signals` being unused is a false positive — the import is intentional for its side effects (registering signal handlers).

## Celery Tasks

Always dispatch Celery tasks using `.delay_on_commit()` instead of `.delay()`. This ensures the task is only sent to the broker after the database transaction commits, preventing race conditions where the task runs before the data it needs is persisted. The only exception is when you explicitly need the task ID returned, in which case `.delay()` is still available.

## Python Package Installation

Never install packages directly in a running container (e.g. `pip install` via `docker compose exec`). Always add the package to `requirements.txt` and rebuild the Docker image. 