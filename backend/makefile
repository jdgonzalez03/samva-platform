migrations: 
	docker compose exec backend python manage.py makemigrations

migrate:
	docker compose exec backend python manage.py migrate

createsuperuser:
	docker compose exec backend python manage.py createsuperuser

shell:
	docker compose exec backend python manage.py shell

bash:
	docker compose exec -it backend bash

loaddata:
	docker compose exec backend python manage.py loaddata accounts/fixtures/initial_users.json
	docker compose exec backend python manage.py loaddata farmer/fixtures/initial_farmers.json
	docker compose exec backend python manage.py loaddata farm/fixtures/initial_farms_with_plots.json