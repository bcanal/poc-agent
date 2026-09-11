# RESUMO.md — perguntas e respostas conceituais da POC

Registro do que foi perguntado e respondido durante a construção de cada
módulo — não é log de erro (isso fica no `NOTAS.md`), é material de estudo
pra consultar depois sem reabrir a conversa inteira.

---

## Módulo 01 — Fundação observável

### O que é OTLP, dentro do OpenTelemetry?

OpenTelemetry (OTel) é o padrão inteiro — SDKs, APIs, convenções de nome.
**OTLP (OpenTelemetry Protocol)** é especificamente o protocolo de
transporte: como os dados de telemetria são serializados (Protobuf ou JSON)
e transportados (gRPC na porta 4317, HTTP na 4318). É o "USB-C da
observabilidade" — qualquer SDK OTel fala OTLP, qualquer backend com um
receiver OTLP aceita, sem os dois lados precisarem se conhecer.

### O que é um "span" nesse contexto?

Um **span** é uma unidade de trabalho com início e fim — uma operação, com
duração. Um **trace** é a árvore de spans relacionados que representa uma
requisição de ponta a ponta. `traceId` amarra todos os spans de uma mesma
requisição; `parentSpanId` constrói a hierarquia (qual span aconteceu
dentro de qual). Um span sem `parentSpanId` é a raiz da árvore.

### Span mede o tempo de interação com LLM? Mede custo também?

**Latência vem de graça** — é só `endTime - startTime`, todo span já
carrega isso estruturalmente. **Custo e tokens não vêm de graça** — são
`attributes` que o código responsável pelo span precisa preencher, lendo o
campo `usage` que a resposta do LLM devolve. O backend de observabilidade
(Langfuse, no nosso caso) só converte tokens → custo usando uma tabela de
preço por modelo; ele não mede nada sozinho.

### Como o JSON de resposta do LLM vira isso?

A cadeia é: (1) o provedor devolve um JSON com `usage: {input_tokens,
output_tokens}`; (2) o código que fez a chamada mede o tempo e lê esse
campo; (3) escreve os valores nos `attributes` do span usando as chaves das
**GenAI semantic conventions** do OTel (`gen_ai.usage.input_tokens`, etc.);
(4) o span vira OTLP e é exportado. O protocolo OTLP não extrai nada — só
carrega o que o código (ou uma lib de instrumentação) já colocou no span.

### Vou ter que escrever essa função de conversão na mão?

Não necessariamente. Existe um espectro: instrumentação manual (você
escreve), auto-instrumentação genérica (HTTP/FastAPI — dá latência, não
tokens, porque não entende o formato de resposta de LLM) e instrumentação
específica de LLM. O **LiteLLM tem um callback OTel nativo**
(`litellm_settings.callbacks: ["otel"]`) que já lê `usage` e preenche os
attributes `gen_ai.*` sozinho — confirmado funcionando (ver módulo 01,
seção de validação do gateway).

### Governança de custo fica centralizada no LiteLLM?

Depende do sentido de "governança". **Bloquear gasto** (budget, rate limit)
só pode acontecer em quem está *no caminho* da requisição — isso é o
LiteLLM, o único ponto por onde toda chamada passa. **Analisar gasto**
(dashboard, comparar por trace/sessão) é o Langfuse, que recebe o dado
depois, de forma assíncrona, e nunca pode bloquear nada.

### O que exatamente foi validado no teste de telemetria?

Um payload OTLP fabricado à mão (`curl -X POST` direto na porta 4318 do
`otel-collector`, sem nenhum SDK) provou que o cano de **infraestrutura**
funciona ponta a ponta: collector recebe → exporta pro Langfuse → aparece
na API dele. Isso não testou chamada de LLM real (sem tokens/custo no
payload) nem código de app (que ainda não existe).

### Por que preciso do Langfuse se o LiteLLM já mostra métricas parecidas?

Sobreposição real hoje, porque só existe uma chamada de LLM isolada. A
diferença é **escopo**: LiteLLM só vê o que passa por ele (a chamada de
LLM). Langfuse é pensado pra ver a **árvore inteira** de uma requisição —
embedding, retrieval, guardrail, LLM, tudo com o mesmo `traceId`. A partir
do módulo 03 (RAG) e 04 (agente), essas outras partes nunca passam pelo
LiteLLM — só aparecem se o app instrumentar e mandar pro coletor. Langfuse
também tem recursos que o LiteLLM não tem: datasets (promoção de trace de
produção pra caso de teste) e scores (nota de judge anexada ao trace).

### O LiteLLM tem guardrails e "policies" nativos?

Sim. Um bloco `guardrails:` no `config.yaml`, rodando em `pre_call`,
`during_call` ou `post_call`, com mais de 40 integrações prontas
(moderação, PII, prompt injection). "Policies" (beta) agrupa guardrails
nomeados e aplica por time/chave/tag automaticamente. Isso concorre com a
pasta `guardrails/` já reservada na estrutura do projeto — decisão adiada
pro módulo 05 (ver `NOTAS.md`).

### O que é "juntar em lote" (batch) no `BatchSpanProcessor`?

Não tem nada a ver com "todos os spans de uma pergunta do usuário" — são
dois eixos independentes. Quantos spans pertencem a UMA pergunta é decidido
pelo `traceId` (lógica de negócio). Batch é só otimização de rede: em vez
de um `POST` HTTP por span, o processor guarda spans terminados numa fila e
só manda quando um timer dispara (~5s por padrão) ou o buffer enche (~512
spans) — o que vier primeiro. O que cai dentro de um lote pode ser spans de
usuários, perguntas e até `traceId`s completamente diferentes, misturados,
só porque terminaram na mesma janela de tempo. Vimos isso na prática: um
log do `otel-collector` mostrou um lote de 90 spans de uma vez, que não
eram de uma pergunta — era tráfego de fundo do LiteLLM (polling da UI,
checagem de budget) que só coincidiu de terminar junto.

### Por que os dados no Langfuse não aparecem em tempo real?

Porque existem três camadas de buffer empilhadas, cada uma independente:
(1) o `BatchSpanProcessor` da própria app/LiteLLM, até ~5s; (2) o
`processor: batch` do `otel-collector` (`otel-collector.yaml`, também
`timeout: 5s`); (3) o `langfuse-worker`, que consome de uma fila no Redis
de forma assíncrona antes de gravar no ClickHouse. No pior caso, pode levar
uns 10-15s entre o span terminar e aparecer na UI. Isso **não** atrasa a
resposta que o usuário recebe — a exportação de telemetria roda em paralelo,
desacoplada do caminho de resposta do `/ask`. Se o Langfuse cair, o `/ask`
continua respondendo normalmente.

### Qual o objetivo do Langfuse na arquitetura inteira? Ele executa alguma ação?

Três usos, mapeados aos módulos do projeto:
1. **Debug de uma transação** (módulos 01, 03, 04, 05) — abrir um trace e
   ver a cascata completa (retrieval, guardrail, LLM) pra entender por que
   uma resposta saiu errada.
2. **Análise agregada, através de muitos traces** (módulo 06) — dashboard:
   custo total, taxa de fallback, latência p95.
3. **Fonte de dados pro loop de avaliação** (módulos 02, 07) — um trace de
   produção que falhou pode ser "promovido" a caso permanente do
   `evals/dataset/` (termo do glossário do `CLAUDE.md`), fechando o loop:
   "uma falha injetada hoje reprova um PR amanhã".

Na requisição ao vivo, o Langfuse **nunca** age — não bloqueia nada, é
sempre depois do fato. A única "ação" dele é rodar um judge automatizado
que escreve uma nota (score) de volta num trace já gravado — assíncrono,
sobre dado histórico, não sobre a requisição em andamento.

### O que é "fallback"? É o Langfuse quem faz isso?

Não, é recurso do **LiteLLM** (gateway), não do Langfuse. Quando o modelo
principal falha (erro, timeout, rate limit), o gateway reenvia
automaticamente a mesma pergunta pra um modelo backup já configurado — o
usuário nem percebe. É o que fecha o critério do módulo 06 ("provedor cai,
resposta continua saindo"). O papel do Langfuse é só mostrar, depois, que
aquele trace usou o backup — um número a mais no dashboard, não uma decisão
dele.

### O que são "scores" no Langfuse?

Uma nota anexada a um trace, respondendo "essa resposta foi boa?" segundo
algum critério. Três origens: manual (humano anota), automatizada (um
"judge" — ver próxima pergunta) ou feedback do usuário final (via endpoint
`/feedback`). É o que alimenta o **gate** do módulo 02: o CI roda o
dataset, calcula a média dos scores, reprova o PR se caiu.

### O que é o "judge"?

Um LLM configurado pra avaliar uma resposta segundo uma rubrica (ex:
"ancorada no contexto? nota 0-1"), numa chamada separada e assíncrona,
depois que a resposta original já foi entregue ao usuário. Duas ressalvas
documentadas no `CLAUDE.md`: (1) precisa ser **calibrado** contra anotação
humana antes de valer — mede-se concordância via kappa; `kappa < 0.6`
significa que o judge não serve (script `03_judge_calibracao.py`); (2)
**não roda em 100% do tráfego ao vivo** — dobra a conta sem mudar decisão.
Uso principal: contra o golden set (`evals/dataset/`), em CI, não contra
toda pergunta real de produção.

### Quem é o gateway na arquitetura: LiteLLM ou Langfuse?

LiteLLM. Gateway é quem fica **no caminho da requisição** — sem ele, não
sai resposta. Por isso só ele pode fazer governança de custo de verdade
(bloquear). Langfuse nunca está no caminho — recebe cópia assíncrona depois
do fato; se cair, o `/ask` continua funcionando.

### Como funciona o fluxo de uma requisição através do LiteLLM?

`/ask` (app) → `POST /chat/completions` no LiteLLM com `model: "chat-default"`
→ LiteLLM olha o `model_list`, vê que o alias aponta pra Anthropic, chama a
API real da Anthropic → Anthropic responde pro LiteLLM → LiteLLM devolve
essa resposta direto pra quem chamou (a app) → app devolve pro chamador do
`/ask`. `chat-default` só existe como **parâmetro** da chamada de saída —
não é uma entidade que "recebe" a resposta de volta, é só o rótulo usado
pra pedir a chamada.

### O `/ask` é um endpoint padrão do FastAPI?

Não — o FastAPI não vem com rota nenhuma pronta, toda rota é declarada por
quem usa o framework. `/ask` é convenção **deste projeto** (documentada no
`CLAUDE.md`), escolhida por fazer sentido semântico com "assistente que
responde perguntas". Poderia ter qualquer outro nome.

### O que são os três aliases no LiteLLM (`ollama-llama3.2`, `anthropic-haiku`, `chat-default`)?

São três **nomes** no `model_list`, não três modelos físicos — dois já
comparam modelos (usados pelo script `01_gateway_smoke.py`), o terceiro
(`chat-default`) é o que a app chama, seguindo a decisão de que a app nunca
deve saber qual provedor está por trás (seção 9 do `CLAUDE.md`).
Importante: `chat-default` é uma indireção **fixa** (aponta pra um backend
só, hoje Anthropic), não dinâmica — não existe lógica condicional
decidindo em tempo de request. Alternância automática entre modelos seria
outro recurso do LiteLLM (fallback/routing), relevante só a partir do
módulo 06.

### O que significa "instrumentar a app com OTel desde já" (em vez de deixar simples)?

Sem instrumentação própria, o `/ask` só repassaria a chamada HTTP pro
LiteLLM, e o único trace gerado seria o do LiteLLM — órfão, sem span "pai"
da aplicação. Funcionaria pro módulo 01, mas quando o módulo 03 adicionar
retrieval, aquele span nasceria desconectado do resto, exigindo retrabalho
(a armadilha "instrumentar depois", já listada no `CLAUDE.md`). Fazer
certo desde já significa: a app abre um span raiz por request
(automaticamente, via `FastAPIInstrumentor`) e propaga o contexto desse
trace pra fora, na chamada ao gateway (via `HTTPXClientInstrumentor`) — daí
em diante, tudo que a app e o LiteLLM gerarem cai na mesma árvore.

### Onde foi configurado o `traceparent`?

Em nenhum lugar explícito do tipo `headers={"traceparent": ...}`. A
configuração real é uma linha só: `HTTPXClientInstrumentor().instrument()`
([app/main.py:33](../app/main.py)). A partir dela, toda chamada feita via
`httpx.AsyncClient` passa a injetar o header sozinha, derivado do span
ativo no momento da chamada — em conjunto com o `FastAPIInstrumentor`, que
cria esse span ativo a cada request recebida.

### Um span "é" um JSON que contém informações do Langfuse e do LiteLLM?

Não, duas confusões aí. (1) Span é uma estrutura de dados em memória (um
objeto), não um JSON — ele só *vira* JSON (ou Protobuf, se for gRPC) no
momento de ser exportado pela rede. (2) Um span pertence a **um produtor
só** — `POST /ask` é span da app (`service.name: poc-agent-app`),
`litellm_request` é span do LiteLLM (`service.name: litellm-gateway`),
objetos diferentes, criados por códigos diferentes. O Langfuse não cria nem
entra dentro de span nenhum — só recebe e exibe, depois do fato. O que
junta spans de origens diferentes numa árvore visual é o `traceId`
compartilhado (via `traceparent`), não conteúdo comum dentro do span.

### O que fazem as linhas de setup do OTel no `main.py` (`Resource`, `TracerProvider`, `exporter`, `processor`)?

Analogia de correio: `Resource` é o **crachá** da app (`service.name`,
grudado em todo span que sair daqui). `TracerProvider` é o **departamento**
de correio, já nascendo com o crachá. `OTLPSpanExporter` é o **carteiro**,
que sabe o endereço (`otel-collector`) e o formato de empacotamento
(OTLP). `BatchSpanProcessor` é a instrução "não saia toda vez que uma carta
ficar pronta — junta um lote antes". `trace.set_tracer_provider(provider)`
é pendurar esse departamento num **quadro de avisos visível pra empresa
inteira** — qualquer código do processo acha ele sozinho depois.

### O `TracerProvider` é quem cria os spans?

Não diretamente — ele cria/entrega `Tracer`s, e é o `Tracer` quem de fato
cria o span (`tracer.start_span(...)`). No `main.py` a gente nunca chama
`trace.get_tracer(...)` na mão; quem faz isso por baixo dos panos é o
`FastAPIInstrumentor` e o `HTTPXClientInstrumentor`, pegando um `Tracer`
emprestado do `TracerProvider` que registramos.

### Como o `FastAPIInstrumentor` e o `HTTPXClientInstrumentor` "acham" o `TracerProvider`, se isso não foi passado explicitamente?

Estado global dentro do próprio pacote `opentelemetry-api`: o módulo
`opentelemetry.trace` guarda uma variável interna (`_TRACER_PROVIDER`).
`trace.set_tracer_provider(provider)` escreve nela; `trace.get_tracer_provider()`
lê dela. Como módulos Python são singletons dentro de um processo, importar
`opentelemetry.trace` em qualquer arquivo dá o mesmo objeto, com a mesma
variável. As libs de instrumentação, quando chamadas sem um
`tracer_provider=` explícito (como fizemos), caem no `else` e chamam
`trace.get_tracer_provider()` — pegando exatamente o que registramos. É por
isso que a **ordem no arquivo importa**: se a instrumentação rodasse antes
do `set_tracer_provider`, o quadro de avisos estaria vazio, e os spans
morreriam silenciosamente contra um provider no-op.

### Como e quando um span chega até o Langfuse, na prática?

Corrente de 4 `POST`s HTTP independentes, nenhum síncrono com a resposta
que o usuário recebe: (1) span termina → `BatchSpanProcessor` da app
guarda numa fila local; (2) gatilho dispara (timer ou buffer cheio) →
`OTLPSpanExporter` faz `POST` pro `otel-collector`; (3) `otel-collector`
reagrupa no próprio `processor: batch` dele e faz outro `POST` pro endpoint
OTLP nativo do Langfuse (`langfuse-web`); (4) `langfuse-web` enfileira no
Redis; `langfuse-worker` consome a fila e grava no ClickHouse — só então o
trace fica visível na UI/API.

---

### Fechamento do módulo 01

O trace final do `/ask` (pergunta real, via `chat-default` → Anthropic)
confirmou os quatro pilares do critério de pronto, no mesmo trace, todos
verificados na prática (não presumidos):
- **tokens**: `13 → 67 (Σ 80)`
- **latência**: `1.91s` no span raiz
- **custo real, não-zero**: `$0.000348` (`0.000013` input + `0.000335`
  output, soma confere) — calculado pelo LiteLLM a partir do preço de
  tabela do `claude-haiku-4-5-20251001`
- **árvore única**: span da app como pai, `litellm_request` como filho —
  propagação de contexto funcionando

Módulo 01 fechado na prática. Falta formalizar em `docs/modulos/01_*.md` e
atualizar a seção 3 ("Estado atual") do `CLAUDE.md`.
