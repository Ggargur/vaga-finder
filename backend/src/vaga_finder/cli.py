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
