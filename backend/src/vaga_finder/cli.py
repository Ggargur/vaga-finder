"""Linha de comando (útil para cron). A interface principal é a web: `vaga-finder serve`."""

import json
import logging

import typer

from .config import ambiente, carregar_config
from .db import Banco

app = typer.Typer(help="Busca vagas parecidas com o seu currículo e redige emails de candidatura.")


def _banco() -> Banco:
    return Banco(ambiente().db_path)


def _imprimir(dados) -> None:
    typer.echo(json.dumps(dados, ensure_ascii=False, indent=2))


def _progresso(i: int, total: int, msg: str) -> None:
    typer.echo(f"[{i}/{total}] {msg}", err=True)


@app.callback()
def _config_log(verboso: bool = typer.Option(False, "--verboso", "-v")) -> None:
    logging.basicConfig(level=logging.INFO if verboso else logging.WARNING, format="%(levelname)s %(message)s")


@app.command()
def perfil() -> None:
    """Gera data/perfil.json a partir de data/curriculo.pdf."""
    from .perfil import gerar_perfil

    _imprimir(gerar_perfil().model_dump())


@app.command()
def buscar() -> None:
    """Coleta vagas das fontes ligadas no config.yaml."""
    from .coleta import coletar

    _imprimir(coletar(_banco(), carregar_config(), progresso=_progresso))


@app.command()
def avaliar(limite: int = typer.Option(None, help="Máximo de vagas novas a avaliar nesta rodada")) -> None:
    """Dá nota às vagas novas e redige rascunhos para as que têm email."""
    from .llm import obter_llm
    from .pipeline import avaliar_e_redigir

    _imprimir(avaliar_e_redigir(_banco(), carregar_config(), obter_llm(), _progresso, limite))


@app.command()
def rodar() -> None:
    """Buscar + avaliar + redigir (para usar no cron)."""
    from .llm import obter_llm
    from .pipeline import rodar as rodar_tudo

    _imprimir(rodar_tudo(_banco(), carregar_config(), obter_llm(), _progresso))


@app.command()
def sincronizar(dias: int = typer.Option(365, help="Quantos dias da pasta Enviados importar")) -> None:
    """Importa candidaturas da pasta Enviados do Gmail para o histórico."""
    from .historico import sincronizar_gmail

    _imprimir(sincronizar_gmail(_banco(), ambiente(), dias, _progresso))


@app.command()
def serve(
    porta: int = typer.Option(8000, "--porta", "-p"),
    reload: bool = typer.Option(False, "--reload", help="Recarrega ao editar o código (desenvolvimento)"),
) -> None:
    """Sobe a interface web em http://127.0.0.1:PORTA."""
    import uvicorn

    typer.echo(f"vaga-finder em http://127.0.0.1:{porta}")
    uvicorn.run("vaga_finder.api.main:app", factory=True, host="127.0.0.1", port=porta, reload=reload)
