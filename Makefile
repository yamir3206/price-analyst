.PHONY: backend-install backend-test backend-lint backend-run api-contract frontend-analyze frontend-test \
	webui-run webui-test \
	deploy-config deploy-up deploy-down deploy-logs deploy-backup

backend-install:
	python3 -m pip install -e 'backend[dev]'

backend-test:
	PYTHONPATH=backend/src pytest backend/tests

backend-lint:
	ruff check backend/src backend/tests backend/scripts
	mypy backend/src

backend-run:
	uvicorn price_analyst.main:app --app-dir backend/src --host 0.0.0.0 --port 8000 --reload

api-contract:
	python backend/scripts/export_openapi.py

frontend-analyze:
	cd frontend && flutter analyze

frontend-test:
	cd frontend && flutter test

webui-run:
	python3 webui/serve.py --start-backend

webui-test:
	python3 -m unittest discover -s webui/tests -v

deploy-config:
	docker compose -f deploy/docker-compose.yml config

deploy-up:
	docker compose -f deploy/docker-compose.yml up --build -d

deploy-down:
	docker compose -f deploy/docker-compose.yml down

deploy-logs:
	docker compose -f deploy/docker-compose.yml logs -f api web

deploy-backup:
	./deploy/backup-sqlite.sh
