# Backend — S.A.M.V.A. Platform

Django project with Wagtail (headless CMS), Django REST Framework, Celery, and PostGIS.

## Run it

```bash
docker compose up --build
```

This starts the API, the PostGIS database, RabbitMQ, and the Celery worker.
The container runs migrations and creates a superuser (`admin` / `admin`) at start.

- API: http://localhost:8000/api/
- Wagtail admin: http://localhost:8000/admin/
- Django admin: http://localhost:8000/django-admin/

Common commands (from this folder, with the containers running):

```bash
make migrations       # makemigrations
make migrate          # migrate
make createsuperuser  # create an admin user
make shell            # Django shell
make bash             # bash inside the container
make loaddata         # load seed data
```

Do not run `python manage.py` on your machine directly — the app needs GDAL/GEOS and the database host from Docker.

## Apps

- **`accounts`** — Users, JWT login (email + password), and profiles. API at `/api/accounts/`.
- **`farmer`** — The farmer model, one-to-one with a user. We do not extend `AbstractUser`; extra user data lives here.
- **`core`** — Common code and global Wagtail settings. Things that do not belong to one app.
- **`cms`** — Landing page content with Wagtail StreamField. The frontend reads `/api/cms/landing/`.
- **`farm`** — Farms and plots. GeoDjango + Leaflet maps: you can draw farm polygons in the admin.
- **`sensors`** — Sensor data and weather station providers (WeatherLink). A Celery task polls the stations every 5 minutes. Planned: public API with `x-api-key` so field sensors can push data.
- **`predictions`** — Predictions with fuzzy logic (for example, irrigation time) based on sensor data.

## Configuration

- Settings are split in `backend/settings/`: `common.py` (shared), `dev.py`, `prod.py`.
  Select one with `DJANGO_SETTINGS_MODULE=backend.settings.dev` (or `.prod`).
- Secrets come from environment variables: `DJANGO_SECRET_KEY`, `POSTGRES_*`, `RABBITMQ_*`.
- The database is **PostGIS** (`django.contrib.gis`), not plain PostgreSQL.
- Scheduled jobs live in `CELERY_BEAT_SCHEDULE` in `settings/common.py`.

## Code style

Ruff formats and lints the code (config in `ruff.toml`):

```bash
# from the repository root:
make lint-backend
make format-backend
```

Rules for changing this code live in [CLAUDE.md](CLAUDE.md).
The full system picture is in [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md).
