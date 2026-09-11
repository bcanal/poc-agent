import os
from dotenv import load_dotenv # load do .env
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel # validacao da requisicao
import httpx # cliente assync que vai chamar o LiteLLM

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

dotenv_path = Path(__file__).resolve().parent.parent / "infra" / ".env"
load_dotenv(dotenv_path = dotenv_path, override=True)

OTEL_ENDPOINT = os.getenv("OTEL_ENDPOINT")
GATEWAY_URL = os.getenv("GATEWAY_URL")
GATEWAY_API_KEY = os.getenv("GATEWAY_API_KEY")

resource = Resource(attributes={"service.name": "poc-agent-app"})
provider = TracerProvider(resource=resource)
exporter = OTLPSpanExporter(endpoint=f"{OTEL_ENDPOINT}/v1/traces")
provider.add_span_processor(BatchSpanProcessor(exporter))

trace.set_tracer_provider(provider)

app = FastAPI()
FastAPIInstrumentor.instrument_app(app)
HTTPXClientInstrumentor().instrument()

class Pergunta(BaseModel):
    pergunta: str

@app.post("/ask")
async def ask(body: Pergunta):
    async with httpx.AsyncClient() as client:
        resposta = await client.post(
            url=f"{GATEWAY_URL}/chat/completions",
            headers={"Authorization": f"Bearer {GATEWAY_API_KEY}"},
            json={
                "model": "chat-default",
                "messages": [{"role": "user", "content": body.pergunta}]
            },
        )
    return resposta.json()

