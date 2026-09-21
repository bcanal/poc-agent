COMPOSE = docker compose -f infra/docker-compose.yml --env-file infra/.env
MODELO ?= llama3.2:3b

.PHONY: up down nuke pull-model demo eval custo

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

nuke:
	$(COMPOSE) down -v

pull-model:
	docker exec infra-ollama-1 ollama pull $(MODELO)

demo:
	@echo "⚠️  demo ainda não implementado — disponível no módulo 01"

eval:
	uv run python evals/build_tests.py
	set -a && . infra/.env && set +a && OPENAI_API_KEY="$$GATEWAY_API_KEY" npx promptfoo@latest eval -c evals/promptfooconfig.yaml

custo:
	@echo "⚠️  custo ainda não implementado — disponível após o LiteLLM entrar"
