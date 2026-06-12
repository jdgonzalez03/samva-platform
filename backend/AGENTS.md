# Backend Guidelines

## Django Apps

Do not set `default_auto_field` in individual `AppConfig` classes. The project already sets `DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'` globally in `settings/common.py`, so per-app overrides are redundant.

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