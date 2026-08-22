# Backend Guidelines

## Django Apps

Do not set `default_auto_field` in individual `AppConfig` classes. The project already sets `DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'` globally in `settings/common.py`, so per-app overrides are redundant.

## Readability
- Prefer guard clauses (early returns) over nested `if`/`else` branching — handle the special case and `return`/`raise` early, keeping the main path unindented; avoid multi-line conditional expressions where a plain `if` block reads clearer.
- Name things explicitly — no cryptic abbreviations (`re`, `cfg`, `tmp`, `val`, `usr`, `qs`). Write the full word: `username_regex`/`username_pattern`, `config`, `user`, `queryset`. A name should read unambiguously without the reader guessing what it stands for.


## DRF API layer

- API views live in `<app>/api.py` (not `views.py`), serializers in `<app>/serializers.py`, routes in `<app>/urls.py` with `app_name`; mount in `backend/urls.py` as `path('api/<app>/', include((<app>_urlpatterns, '<app>')))` — the namespace tuple is what makes `reverse('<app>:<name>')` work in tests, since the plain list import drops `app_name`.
- Every view sets `permission_classes` explicitly: there is no `DEFAULT_PERMISSION_CLASSES`, so the DRF default is `AllowAny`.
- Scope user-owned querysets through a lookup (`Farm.objects.filter(owner__user=self.request.user)`), never `request.user.farmer` — a user without the related row raises `RelatedObjectDoesNotExist` (500) instead of returning an empty list.
- Nested resources resolve the parent with `get_object_or_404(Parent, pk=..., <owner lookup>)` so someone else's id 404s instead of returning `[]`, which would leak its existence.
- Any model exposed through a list endpoint needs `Meta.ordering` — without it the page order is unstable and DRF warns.
- Geometry fields (`PointField`/`PolygonField`) do not serialize through a plain `ModelSerializer`; exposing them needs `djangorestframework-gis`, which is not installed yet.

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