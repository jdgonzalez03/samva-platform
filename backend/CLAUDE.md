# Backend Guidelines

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

## Tests

- `patch()` targets the module where a name is *used*, not where it is defined: `from x import CONST` binds the value into the consumer's namespace at import time, so patching `x.CONST` leaves the consumer untouched. Moving a constant to `constants.py` therefore breaks every `patch('<old_module>.CONST')` — repoint them at the module that imports it.
- A test that consumes `random` without an explicit seed is not deterministic — it is a coin flip that will fail in someone else's run. Seed it, and make the assertion robust as well: a seed fixes the noise but not a timestamp grid anchored on `now()`, so assert over a window or an aggregate rather than a single-sample `argmax`.

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