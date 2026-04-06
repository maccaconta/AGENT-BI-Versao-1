# ─── Agent-BI Makefile ────────────────────────────────────────────────────────
.PHONY: help install setup migrate seed run test lint format docker-up docker-down

PYTHON := python
MANAGE := $(PYTHON) manage.py
SETTINGS := config.settings.development

help: ## Mostrar ajuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ─── Setup ────────────────────────────────────────────────────────────────────

install: ## Instalar dependências Python
	pip install -r requirements.txt

setup: install ## Setup completo do projeto
	cp -n .env.example .env || true
	$(MANAGE) migrate --settings=$(SETTINGS)
	$(MANAGE) createsuperuser --settings=$(SETTINGS) || true
	@echo "✅ Setup concluído!"

# ─── Database ─────────────────────────────────────────────────────────────────

migrate: ## Executar migrações
	$(MANAGE) migrate --settings=$(SETTINGS)

makemigrations: ## Criar migrações
	$(MANAGE) makemigrations --settings=$(SETTINGS)

shell: ## Abrir shell Django
	$(MANAGE) shell_plus --settings=$(SETTINGS)

# ─── Dev Server ───────────────────────────────────────────────────────────────

run: ## Iniciar servidor de desenvolvimento
	$(MANAGE) runserver 0.0.0.0:8000 --settings=$(SETTINGS)

run-celery: ## Iniciar Celery worker
	celery -A config.celery worker --loglevel=info --concurrency=4

run-celery-beat: ## Iniciar Celery beat scheduler
	celery -A config.celery beat --loglevel=info

# ─── Docker ───────────────────────────────────────────────────────────────────

docker-up: ## Subir serviços Docker (db, redis, minio)
	docker-compose up -d db redis minio
	@echo "⏳ Aguardando serviços..."
	sleep 5
	@echo "✅ Serviços prontos!"

docker-up-all: ## Subir todos os serviços Docker
	docker-compose up -d

docker-down: ## Parar serviços Docker
	docker-compose down

docker-logs: ## Ver logs dos containers
	docker-compose logs -f

docker-build: ## Build da imagem Docker
	docker build -t agent-bi:latest .

# ─── Test ─────────────────────────────────────────────────────────────────────

test: ## Executar testes
	pytest apps/ -v --tb=short

test-cov: ## Testes com cobertura
	pytest apps/ -v --cov=apps/ --cov-report=html --cov-report=term-missing

test-fast: ## Testes rápidos (sem I/O lento)
	pytest apps/ -v -m "not slow" --tb=short

# ─── Code Quality ─────────────────────────────────────────────────────────────

lint: ## Verificar qualidade do código
	flake8 apps/ config/ --max-line-length=100
	mypy apps/ --ignore-missing-imports

format: ## Formatar código
	black apps/ config/ --line-length=100
	isort apps/ config/

format-check: ## Verificar formatação
	black apps/ config/ --check --line-length=100
	isort apps/ config/ --check-only

# ─── AWS ──────────────────────────────────────────────────────────────────────

minio-setup: ## Criar buckets no MinIO local
	@echo "Criando buckets MinIO..."
	aws --endpoint-url http://localhost:9000 s3 mb s3://agent-bi-datalake-local --region us-east-1 || true
	aws --endpoint-url http://localhost:9000 s3 mb s3://agent-bi-dashboards-local --region us-east-1 || true
	aws --endpoint-url http://localhost:9000 s3 mb s3://agent-bi-athena-results-local --region us-east-1 || true
	@echo "✅ Buckets criados!"

# ─── Utilities ────────────────────────────────────────────────────────────────

seed: ## Popular banco com dados de exemplo
	$(MANAGE) runscript seed_data --settings=$(SETTINGS)

collect-static: ## Coletar arquivos estáticos
	$(MANAGE) collectstatic --noinput --settings=$(SETTINGS)

check: ## Verificar configuração Django
	$(MANAGE) check --settings=$(SETTINGS)

urls: ## Listar todas as URLs da API
	$(MANAGE) show_urls --settings=$(SETTINGS)
