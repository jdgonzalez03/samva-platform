# S.A.M.V.A. Platform

A web platform for farmers. It collects environmental data from sensors in the field (temperature, humidity, rain) and shows it in a simple way. The goal: help farmers make better decisions.

For the full picture of how the system is built, read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Stack

- **Backend**: Django + Wagtail + Django REST Framework + Celery + PostGIS + JWT
- **Frontend**: Nuxt 4 + Nuxt UI v4 + Tailwind CSS 4 + TypeScript
- **E2E**: Playwright
- **Infra**: Docker Compose, Nginx, RabbitMQ

Exact versions live in `backend/requirements.txt` and `frontend/package.json`.

## Repository structure

```
backend/       # Django project (see backend/README.md)
frontend/      # Nuxt 4 app (see frontend/README.md)
e2e/           # Playwright end-to-end tests (see e2e/README.md)
nginx/         # Nginx configs for production tests
docs/          # Architecture and ADRs (decision records)
Makefile       # Common commands (see below)
docker-compose.yml       # Production test (full stack behind Nginx)
docker-compose.dev.yml   # Production test with MinIO (S3 storage)
```

## Development

Start the backend (API + database + Celery):

```bash
cd backend
docker compose up --build
```

Then you have:

- API: http://localhost:8000/api/
- Wagtail admin: http://localhost:8000/admin/
- Django admin: http://localhost:8000/django-admin/

The container runs migrations and creates a superuser (`admin` / `admin`) at start.

Start the frontend in another terminal:

```bash
cd frontend
npm install
npm run dev   # http://localhost:3000
```

## Common commands (Makefile)

Run these from the repository root. They use `docker-compose.dev.yml`.

```bash
make up-dev            # Start the full stack
make down              # Stop it
make logs              # Follow the logs
make migrations        # Django makemigrations
make migrate           # Django migrate
make createsuperuser   # Create an admin user
make loaddata          # Load seed data (users, farmers, farms)
make shell             # Django shell
make lint              # Lint backend (Ruff) + frontend (ESLint)
make format-backend    # Format backend with Ruff
make clean             # Stop and remove volumes
```

## Production (local test)

```bash
docker compose -f docker-compose.yml up --build
# or with MinIO for S3 storage:
make up-dev
```

Full stack with Nginx at http://localhost/.

## Technical notes

- The database is **PostGIS**, not plain PostgreSQL. It needs GDAL/GEOS.
- Auth uses **JWT** (djangorestframework-simplejwt). Login is with email + password.
- The API lives under `/api/`. Wagtail works as a headless CMS with StreamField.
- Django settings: `backend.settings.dev` (development), `backend.settings.prod` (production).
- Frontend shared types live in `frontend/shared/types/` (alias `#shared/`); the API layer uses the alias `#api/`.
- Architecture decisions are recorded in `docs/adr/`.
