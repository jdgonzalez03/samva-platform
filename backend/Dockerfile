FROM python:3.14-slim-bookworm AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update --yes --quiet && apt-get install --yes --quiet --no-install-recommends \
    build-essential \
    libpq-dev \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    libwebp-dev \
 && rm -rf /var/lib/apt/lists/*


WORKDIR /app
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Dev stage
FROM base AS dev
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]


# Production stage
FROM base AS production
RUN useradd -m wagtail
COPY --chown=wagtail:wagtail . .
USER wagtail
RUN DJANGO_SETTINGS_MODULE=config.settings.production \
    DJANGO_SECRET_KEY=build-time-secret \
    POSTGRES_HOST=none \
    python manage.py collectstatic --noinput --clear
EXPOSE 8000
ENTRYPOINT ["sh", "-c", "python manage.py migrate --noinput && exec \"$@\"", "--"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]