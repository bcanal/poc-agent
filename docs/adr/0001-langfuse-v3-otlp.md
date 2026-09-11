# 0001 — Langfuse v3 em vez de v2

- **Escolhi:** Langfuse v3 (`langfuse/langfuse:3.222.0` + `langfuse-worker`, ClickHouse, Redis, MinIO).
- **Contra:** Langfuse v2 (`langfuse/langfuse:2.95.11`, monolítico, só Postgres) — era a escolha inicial, por simplicidade.
- **Por quê:** v2 não tem endpoint OTLP nativo. Confirmado em teste manual: `POST /v1/traces` no `otel-collector` devolveu `404` em `.../api/public/otel/v1/traces` contra a v2; o endpoint só existe a partir da 3.22.0. Sem ele, a decisão já tomada (`OpenTelemetry GenAI → Langfuse`, por reversibilidade de plataforma) não se sustenta — a app teria que acoplar no SDK proprietário do Langfuse em vez de falar OTel puro.
- **Custo aceito:** infra do módulo 01 salta de 4 pra 8 serviços antes de existir `/ask`.
