# NOTAS.md — o que deu errado (e o que ficou em aberto)

Uma seção por módulo. Erros e decisões adiadas, não crônica do que funcionou.

---

## Módulo 01 — Fundação observável

- **Langfuse v2 → v3, descoberto em debug, não planejado.** O `docker-compose.yml`
  inicial usava `langfuse/langfuse:3` como se fosse trivial, mas a v3 exige
  ClickHouse + Redis + MinIO (não só Postgres). Tentamos simplificar voltando
  pra v2 — só pra descobrir que a v2 não tem endpoint OTLP nativo
  (`/api/public/otel` só existe a partir da 3.22.0), o que quebra a decisão
  já tomada de `OpenTelemetry GenAI → Langfuse`. Voltamos pra v3
  (`3.222.0`). Falta o ADR dessa decisão em `docs/adr/`.

- **Guardrail: LiteLLM ou código próprio? (decidir no módulo 05, não antes)**
  Descoberto ao explorar a UI do LiteLLM: ele tem um bloco `guardrails:` no
  `config.yaml` (pre_call/during_call/post_call) com 40+ integrações prontas
  (moderação, PII, prompt injection), mais um recurso de "policies" (beta)
  pra atribuir guardrails por time/chave/tag automaticamente. Isso concorre
  com a pasta `guardrails/` já reservada na estrutura do projeto, que sugere
  código customizado. Duas opções, cada uma com motivo:
  - **LiteLLM nativo**: menos código, testado por terceiros, guardrail vira
    configuração, não implementação.
  - **Customizado em `guardrails/`**: mais lento, mas é o que ensina a
    implementar de verdade — bate com o objetivo do projeto ("saber construir
    isto de novo, sozinho").
  Não decidir agora — só não esquecer que a pergunta existe quando chegar lá.
