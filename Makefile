
up-dev:
	docker compose -f docker-compose.dev.yml up

# Django management commands
migrations:
	docker compose -f docker-compose.dev.yml exec backend python manage.py makemigrations

migrate:
	docker compose -f docker-compose.dev.yml exec backend python manage.py migrate

createsuperuser:
	docker compose -f docker-compose.dev.yml exec backend python manage.py createsuperuser

collectstatic:
	docker compose -f docker-compose.dev.yml exec backend python manage.py collectstatic --noinput

shell:
	docker compose -f docker-compose.dev.yml exec backend python manage.py shell

startapp:
	@if [ -z "$(name)" ]; then \
		echo "Usage: make startapp name=app_name"; \
		exit 1; \
	fi
	docker compose -f docker-compose.dev.yml exec backend python manage.py startapp $(name)

runserver:
	docker compose -f docker-compose.dev.yml exec backend python manage.py runserver 0.0.0.0:8000

# Utility commands
logs:
	docker compose -f docker-compose.dev.yml logs -f

down:
	docker compose -f docker-compose.dev.yml down

clean:
	docker compose -f docker-compose.dev.yml down -v
	docker system prune -f