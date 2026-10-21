# NADI — one place to run everything the project needs.
# Backend runs in Docker (db + MinIO + ml-service + api, auto-migrated & seeded).
# The Expo mobile app runs on your laptop for the LAN demo:  make app
#
#   make up        bring the whole backend stack up (build + migrate + seed)
#   make down      stop the stack (keeps data volumes)
#   make reset     wipe volumes and bring up a fresh, re-seeded stack
#   make seed      re-run the demo seed inside the running api container
#   make logs      follow logs from all services
#   make ps        show service status + health
#   make health    curl the api health endpoint
#   make app       start the Expo dev server (phones join over LAN)
#   make test      run the mobile test suite + the api test suite
#   make help      list these targets

COMPOSE := docker compose -f infra/docker-compose.yml

.DEFAULT_GOAL := help

.PHONY: up down reset seed logs ps health app test test-mobile test-api help

up: ## Build + start the backend stack (api auto-migrates & seeds on first boot)
	$(COMPOSE) up -d --build
	@echo ""
	@echo "Stack starting. Watch readiness with:  make ps"
	@echo "API:            http://localhost:8000  (health: /health)"
	@echo "MinIO console:  http://localhost:9001  (user: nadi / pass: nadi12345)"
	@echo "Demo logins — patient: any new +91 (OTP 123456) | doctor: +915000000001 | pharmacy: +915000020000"

down: ## Stop the stack, keeping data volumes
	$(COMPOSE) down

reset: ## Wipe volumes and bring up a fresh, re-seeded stack
	$(COMPOSE) down -v
	$(COMPOSE) up -d --build
	@echo "Fresh stack starting (empty volumes -> migrate + seed). Watch:  make ps"

seed: ## Re-run the demo seed inside the running api container (idempotent)
	$(COMPOSE) exec api python -m seed.seed

logs: ## Follow logs from all services
	$(COMPOSE) logs -f

ps: ## Show service status and health
	$(COMPOSE) ps

health: ## Curl the api health endpoint
	@curl -s -o /dev/null -w "api /health -> %{http_code}\n" http://localhost:8000/health || echo "api not reachable yet"

app: ## Start the Expo dev server (run on the laptop; phones join over LAN)
	cd apps/mobile && npm start

test-mobile: ## Run the mobile jest suite + typecheck
	cd apps/mobile && npm test && npm run typecheck

test-api: ## Run the api test suite (expects the stack up; reseed for a clean run)
	cd apps/api && ./.venv/Scripts/python.exe -m pytest -q

test: test-mobile test-api ## Run both test suites

help: ## List available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  make %-12s %s\n", $$1, $$2}'
