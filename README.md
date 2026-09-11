# poc-agent

Um assistente sobre documentação técnica pública, construído em sete módulos.
O assistente é a desculpa; a arquitetura é o assunto.

Ao final, uma arquitetura completa de engenharia de IA — gateway, retrieval,
agente, guardrails, avaliação automatizada e observabilidade — roda inteira em
containers na máquina local, e cada peça está no desenho porque um número a
justificou.

O repo começa vazio. Nada aqui é herdado de estudo anterior.

## A regra que organiza o repo

> Nenhum número neste README existe sem um script que o reproduz.

Se uma decisão aparece documentada — chunk_size, k, agente ou pipeline, qual
guardrail — existe um arquivo que roda e mostra a medição que a sustentou.
Print de terminal não sobrevive à semana seguinte.

## Estado atual

| # | Módulo | Entrega | Status |
|---|---|---|---|
| 01 | Fundação observável | `curl /ask` responde e o trace mostra custo, tokens e latência | ⬜ |
| 02 | Dataset e o gate | um PR que piora o prompt é reprovado automaticamente | ⬜ |
| 03 | RAG medido | tabela de recall@k escolhe o chunk_size; faithfulness no gate | ⬜ |
| 04 | Do pipeline ao agente | agente multi-step com estado retomável e eval de trajetória | ⬜ |
| 05 | Guardrails e red team | taxa de ataque medida antes/depois, falso positivo < 2% | ⬜ |
| 06 | Produção | provedor cai, fallback aparece no dashboard, resposta continua saindo | ⬜ |
| 07 | Fechar o loop | uma falha injetada hoje reprova um PR amanhã | ⬜ |

Um módulo é marcado como feito **apenas** pelo critério de pronto — nunca por
"acho que funciona". Os critérios estão em `docs/modulos/NN_*.md`.

## Instalação

Pré-requisitos: Docker + Compose, Python 3.10+, 16 GB de RAM e ~40 GB de disco.

```bash
cp .env.example .env      # preencha a chave da API do provedor
make up                   # sobe a stack completa
make pull-model           # baixa o modelo local no Ollama (~5 GB)
make demo                 # faz uma pergunta e imprime o link do trace
```

`make down` derruba tudo. `make nuke` derruba e apaga os volumes — use quando
quiser provar que o projeto sobe do zero em uma máquina limpa.

## Arquitetura

```
                 ┌── plano offline ──────────────────────────────────┐
                 │  datasets → prompt registry → evals → gate de CI   │
                 └───────────────────┬───────────────────────────────┘
                                     │ serve prompt v.N / libera build
                                     ▼
  cliente → guardrail entrada → orquestração → gateway → modelos → guardrail saída
                                     │             │
                          ┌──────────┼─────────┐   └─ rota · fallback · cache · quota
                          ▼          ▼         ▼
                      retrieval   ferramentas  memória
                                     │
                                     │ traces, tokens, custo, latência (assíncrono)
                                     ▼
   curadoria ← feedback ← evals online ← plataforma de obs ← tracing (OTel GenAI)
       │
       └──────────────────── volta para os datasets ─────────────────────┘
```

A seta de baixo é o ponto do projeto inteiro. Sem ela, cada falha de produção é
resolvida no prompt e esquecida; com ela, cada falha vira caso permanente na
suíte que roda no próximo PR.

## Componentes

| Camada | O que roda aqui | Por que está no desenho |
|---|---|---|
| Gateway | LiteLLM | fronteira de agnosticismo: nenhuma parte da app conhece nome de provedor |
| Modelos | Ollama (local) + 1 API | commodity intercambiável atrás do gateway |
| Retrieval | Postgres + pgvector, BM25, reranker | busca híbrida porque jargão quebra busca só vetorial |
| Orquestração | LangGraph + checkpointer em Postgres | falha no passo 8 não repaga os 7 anteriores |
| Guardrails | Presidio, classificador de injection, checagem de ancoragem | controle inline, com orçamento de latência declarado |
| Evals | promptfoo, Ragas, judge calibrado | determinístico primeiro; judge só onde os outros não alcançam |
| Observabilidade | OpenTelemetry GenAI → Langfuse | telemetria é padrão aberto, plataforma é decisão reversível |

## Estrutura

```
poc-agent/
├── app/                   # FastAPI: /ask, /feedback, /health
├── graph/                 # nós e arestas do LangGraph
├── ingest/                # markdown → chunk → embedding → pgvector
├── guardrails/            # entrada e saída, com medição de latência
├── evals/
│   ├── dataset/           # 30+ casos com fonte e gabarito (YAML versionado)
│   ├── promptfooconfig.yaml
│   └── ragas/
├── scripts/               # NN_nome.py — um script, uma pergunta
├── infra/
│   ├── docker-compose.yml
│   ├── litellm.config.yaml
│   └── otel-collector.yaml
├── docs/
│   ├── README.md          # este arquivo
│   ├── adr/               # uma decisão, cinco linhas, o número que a sustentou
│   ├── modulos/           # critério de pronto de cada módulo
│   └── NOTAS.md           # o que deu errado — metade do aprendizado
└── .github/workflows/     # o gate
```

## Os scripts

Cada arquivo roda sozinho, responde a uma pergunta e imprime a explicação junto
com o resultado. A numeração acompanha a ordem dos módulos.

| Script | Módulo | Pergunta que responde |
|---|---|---|
| `01_gateway_smoke.py` | 01 | a mesma pergunta nos dois modelos custa e demora quanto? |
| `02_anatomia_trace.py` | 01 | o que exatamente virou span — e o que ficou de fora? |
| `03_judge_calibracao.py` | 02 | o judge concorda comigo? (kappa < 0.6 → não serve ainda) |
| `04_recall_at_k.py` | 03 | qual chunk_size e qual k para ESTE corpus? |
| `05_diluicao.py` | 03 | por que o chunk grande perde a busca mesmo sem truncar? |
| `06_agente_vs_pipeline.py` | 04 | o agente ganha do grafo linear, ou só somou latência? |
| `07_guardrail_custo.py` | 05 | quantos ms cada guardrail adiciona, e quantos legítimos ele barra? |
| `08_trafego_sintetico.py` | 06 | 200 requisições variadas, para haver o que observar |

```bash
python3 scripts/01_gateway_smoke.py
```

Arquivos com `_` no início são apoio, não exercício: `_comum.py` (helpers),
`_corpus.py` (carga do corpus e do gabarito).

## Trocando o modelo

Nunca no código. O alias é o contrato:

```bash
MODELO=local/qwen2.5 make demo
MODELO=api/provedor  make demo
```

A app fala com `chat-default` e o gateway decide. Rodar a suíte de eval inteira
com os dois é, sozinho, meio módulo de estudo: você vê o score mudar, o custo
mudar em duas ordens de grandeza e a latência trocar de gargalo.

Para provar o fallback:

```bash
docker compose stop ollama && make demo   # continua respondendo, pela API
```

## As três ideias centrais

**Guardrail não é eval.** Guardrail roda inline em toda requisição, precisa ser
rápido e pode bloquear. Eval roda sobre um conjunto, pode ser lenta e não
bloqueia nada em produção. Confundir os dois entrega latência inaceitável ou
falsa sensação de qualidade.

**Separe a culpa antes de otimizar.** Resposta ruim tem duas causas distintas: o
contexto certo não chegou (retrieval) ou chegou e o modelo não usou
(prompt/modelo). As métricas precisam distinguir uma da outra — senão se ajusta
prompt para resolver problema de chunking. `recall@k` e `context precision`
acusam a primeira; `faithfulness` acusa a segunda.

**Sem gate, não existe avaliação.** Uma suíte que roda e não bloqueia nada é
relatório, não teste. O valor aparece no momento em que um PR é reprovado por
queda de score. Antes disso, é custo.

## Convenções

- **Um script, uma pergunta.** Se o arquivo responde duas, são dois arquivos.
- **Uma decisão, um ADR.** `docs/adr/NNNN-titulo.md`, cinco linhas: o que
  escolhi, contra o que, por qual número.
- **O que falhou fica escrito.** `docs/NOTAS.md`, uma seção por módulo.
- **Chunk se mede em token, não em caractere.** Caractere é medida traiçoeira:
  a mesma contagem dá número de tokens diferente em português, em inglês, em
  código e em tabela — e o excedente da janela é descartado sem aviso.
- **Time-box.** Estourou o tempo do módulo? Corte escopo, nunca o critério de
  pronto.

## O que este projeto deliberadamente não cobre

- Fine-tuning e treino de modelo — outra disciplina; aqui o modelo é variável do
  experimento, não objeto de estudo.
- Multi-tenancy e isolamento de dado por cliente — importante em produto, ruído
  aqui.
- Kubernetes — o Compose ensina as mesmas peças sem o imposto de complexidade.
- Benchmark de modelo base — avalia-se a aplicação, não o modelo.

## Aviso sobre o corpus

O corpus padrão é documentação pública (markdown aberto, comunidade com
perguntas reais o bastante para virar dataset). Isso remove atrito de dado
sensível e deixa o método inteiro portátil.

O que **não** é portátil de graça é o dataset: as 30 perguntas com gabarito são
específicas do corpus e são o ativo mais caro do repo. Trocar o corpus por
documentação interna é uma tarde de trabalho no `ingest/`; refazer o dataset é
uma semana. Planeje nessa ordem.

## Custo

Infraestrutura: R$ 0 — tudo roda em container local.
API do provedor: reserve ~US$ 15 para as sete semanas, com folga. O grosso vai
em eval (a suíte roda a cada PR) e em judge, não nas respostas.

`make custo` imprime o acumulado por modelo lido do gateway — a única fonte de
verdade de custo no projeto.
