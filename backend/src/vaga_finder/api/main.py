"""App FastAPI. Em produção também serve o front compilado (frontend/dist)."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from ..config import BACKEND_DIR, ambiente
from ..db import Banco
from ..envio import Enviador, FilaEnvio, enviar_smtp
from ..llm import LLM, obter_llm
from ..tarefas import GerenciadorTarefas
from .deps import Servicos
from .rotas import config, envios, estado, perfil, rascunhos, tarefas, vagas

FRONT_DIST = BACKEND_DIR.parent / "frontend" / "dist"


def criar_app(
    banco: Banco | None = None,
    llm: LLM | None = None,
    enviar: Enviador = enviar_smtp,
    iniciar_fila: bool = True,
    front_dist: Path = FRONT_DIST,
) -> FastAPI:
    amb = ambiente()
    banco = banco or Banco(amb.db_path)
    s = Servicos(
        amb=amb,
        banco=banco,
        llm=llm or obter_llm(),
        tarefas=GerenciadorTarefas(banco),
        fila=FilaEnvio(banco, amb, enviar),
        enviar=enviar,
    )

    @asynccontextmanager
    async def ciclo_de_vida(_app: FastAPI):
        banco.encerrar_tarefas_orfas()
        if iniciar_fila:
            s.fila.iniciar()
        yield
        s.fila.parar()
        s.tarefas.encerrar()

    app = FastAPI(title="vaga-finder", lifespan=ciclo_de_vida)
    app.state.servicos = s
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    for modulo in (estado, perfil, vagas, rascunhos, envios, tarefas, config):
        app.include_router(modulo.router, prefix="/api")

    if front_dist.exists():
        indice = front_dist / "index.html"

        @app.get("/{caminho:path}", include_in_schema=False)
        def front(caminho: str):
            if caminho.startswith("api/"):
                raise HTTPException(404)
            arquivo = (front_dist / caminho).resolve()
            if caminho and arquivo.is_file() and arquivo.is_relative_to(front_dist.resolve()):
                return FileResponse(arquivo)
            return FileResponse(indice)

    return app


def app() -> FastAPI:
    """Fábrica para o uvicorn (`--factory`)."""
    return criar_app()
