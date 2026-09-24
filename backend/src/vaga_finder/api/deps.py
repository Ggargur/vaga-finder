from dataclasses import dataclass

from fastapi import Request

from ..config import Ambiente
from ..db import Banco
from ..envio import Enviador, FilaEnvio
from ..llm import LLM
from ..tarefas import GerenciadorTarefas


@dataclass
class Servicos:
    amb: Ambiente
    banco: Banco
    llm: LLM
    tarefas: GerenciadorTarefas
    fila: FilaEnvio
    enviar: Enviador


def servicos(request: Request) -> Servicos:
    return request.app.state.servicos
