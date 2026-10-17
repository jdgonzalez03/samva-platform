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

# Narrow the run through ARGS: make test ARGS="sensors.tests.PollWeatherLinkStationTests"
test:
	docker compose exec backend python manage.py test $(ARGS)

loaddata:
	docker compose exec backend python manage.py loaddata accounts/fixtures/initial_users.json
	docker compose exec backend python manage.py loaddata farmer/fixtures/initial_farmers.json
	docker compose exec backend python manage.py loaddata farm/fixtures/initial_farms_with_plots.json
	docker compose exec backend python manage.py loaddata sensors/fixtures/initial_sensors.json
	docker compose exec backend python manage.py loaddata sensors/fixtures/lora_demo_sensors.json
	docker compose exec backend python manage.py seed_weather_readings
	docker compose exec backend python manage.py seed_sensor_readings

seed-weather:
	docker compose exec backend python manage.py seed_weather_readings

seed-sensors:
	docker compose exec backend python manage.py seed_sensor_readings

mqtt-logs:
	docker compose logs -f --tail=100 mqtt_ingest

mqtt-restart:
	docker compose up -d --force-recreate mqtt_ingest

# Extra flags go through ARGS: make simulate-lora ARGS="--count 3 --interval 5"
simulate-lora:
	docker compose exec backend python scripts/simulate_lora_node.py $(ARGS)

lint:
	docker compose exec backend ruff check .
