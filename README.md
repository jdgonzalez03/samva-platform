# S.A.M.V.A. Platform

Plataforma de gestión agrícola con CMS headless.

## Stack

- **Backend**: Django 6 + Wagtail 7 + DRF + PostGIS + JWT
- **Frontend**: Nuxt 4 + Nuxt UI v4 + TailwindCSS 4 + TypeScript 6
- **Infra**: Docker Compose, Nginx, PostGIS 15

## Estructura

```
backend/             # Proyecto Django
├── backend/         # Config del proyecto (settings/, urls.py)
├── accounts/        # App de usuarios
├── farmer/          # App de agricultores
├── core/            # Config general y Wagtail Site Settings
├── cms/             # Páginas Wagtail y API pública
├── farm/            # App de fincas
├── docker-compose.yml  # Entorno de desarrollo
└── Dockerfile       # Multi-stage (dev / production)

frontend/            # App Nuxt 4
├── app/             # Vue app (pages/, layouts/, components/, composables/)
├── shared/          # Tipos compartidos (alias #shared/)
└── server/          # Rutas Nitro

nginx/               # Configs para probar producción
docker-compose.yml       # Producción (pruebas)
docker-compose.dev.yml   # Producción (pruebas, con MinIO)
```

## Desarrollo

```bash
cd backend
docker compose up --build
```

Servicios:
- Backend API: http://localhost:8000/api/
- Wagtail admin: http://localhost:8000/admin/
- Django admin: http://localhost:8000/django-admin/

### Comandos Django

```bash
docker compose exec backend python manage.py makemigrations
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
docker compose exec backend python manage.py shell
```

El contenedor ejecuta migraciones y crea un superusuario (admin/admin) automáticamente al iniciar.

### Frontend (desarrollo standalone)

```bash
cd frontend
npm install
npm run dev
```

Requiere el backend corriendo en `http://localhost:8000`.

## Producción (pruebas locales)

```bash
docker compose -f docker-compose.yml up --build 
# o con MinIO para almacenamiento S3:
docker compose -f docker-compose.dev.yml up --build # o desde el directorio raiz make up-dev
```

Servicios completos con Nginx en http://localhost/.

## Notas técnicas

- La base de datos es **PostGIS** (no PostgreSQL plano) — requiere GDAL/GEOS.
- Autenticación vía **JWT** (djangorestframework-simplejwt). El frontend tiene un stub de auth pendiente de implementar.
- API REST en `/api/`. Wagtail funciona como CMS headless con StreamField.
- Settings: `backend.settings.dev` (desarrollo), `backend.settings.prod` (producción).
- Tipos compartidos frontend en `frontend/shared/types/` con alias `#shared/`.
