# Prompt — diagrama de arquitetura (Claude Design)

Cole o bloco abaixo. É autocontido.

---

Diagrama de arquitetura de IA em um artboard horizontal 1600×1000, para exportar
em PNG. Três bandas, só texto — sem logos nem ícones. Título:
"poc-agent — arquitetura de referência".

**Banda 1 — PLANO OFFLINE.** Quatro caixas em linha, ligadas por setas:
Datasets de avaliação → Prompt & config registry → Suíte de evals → Gate de CI/CD.

**Banda 2 — CAMINHO DA REQUISIÇÃO (runtime).** Seis caixas em linha, setas sólidas:
Cliente → Guardrails de entrada → Orquestração/agente → AI Gateway → Modelos →
Guardrails de saída. Abaixo, três caixas ligadas à Orquestração: Retrieval/RAG
("recupera"), Ferramentas & MCP ("chama"), Memória & estado ("lê · escreve").
Do Prompt registry e do Gate de CI/CD descem setas até a Orquestração,
rotuladas "serve prompt v.N" e "libera o build".

**Banda 3 — OBSERVABILIDADE EM PRODUÇÃO.** Cinco caixas com o fluxo correndo da
direita para a esquerda, setas tracejadas: Tracing (OpenTelemetry) → Plataforma
de observabilidade → Evals online → Feedback → Curadoria. Uma seta tracejada
desce do lado direito da banda 2 até Tracing: "traces · custo · latência".

**O loop**, a seta mais evidente do desenho: sai de Curadoria, contorna pela
margem esquerda subindo e entra em Datasets de avaliação. Rótulo: "loop de
melhoria contínua".

**Codificação**, com legenda no rodapé: sólida escura = requisição síncrona;
âmbar = controle que pode bloquear (os dois guardrails); tracejada cinza =
telemetria; azul = plano offline e loop.

**Estilo:** esquema de engenharia — retângulos de cantos retos, contorno fino,
sem sombra nem gradiente. Fundo claro frio, destaque #0B5D8A, âmbar #A2530F.
Grotesca nos títulos, monoespaçada nos rótulos. Tudo alinhado em grade. Toda
seta com rótulo curto. As caixas nomeiam funções, não fornecedores.

---

## Se precisar de mais detalhe, acrescente

**Subtítulos nas caixas:** "abaixo do título de cada caixa, uma linha em
monoespaçada: Datasets = golden set · casos reais · sintéticos; Prompt registry =
versionado · deploy sem release; Suíte de evals = scorers · judges · métricas
RAG; Gate = regressão · red team · custo; Guardrails de entrada = PII ·
injection · escopo; Orquestração = planejar · chamar · repetir; Gateway = rota ·
fallback · cache · quota; Modelos = multi-provider + self-hosted; Guardrails de
saída = grounding · PII; Retrieval = chunking · embeddings · vector DB · híbrida
· reranker; Ferramentas = APIs internas · sandbox; Memória = sessão · checkpoint
· long-term; Tracing = span de LLM, retrieval, tool; Evals online = judge
amostrado · drift; Feedback = thumbs · anotação · revisão humana."

**Nomes de produto:** "acrescente a ferramenta em monoespaçada sob cada caixa."

**Espaço para logo:** "reserve 24×24px no canto superior direito de cada caixa."

**Frase de rodapé:** "A seta que fecha o ciclo é o componente mais
negligenciado: sem ela, cada falha de produção é corrigida no prompt e
esquecida."
