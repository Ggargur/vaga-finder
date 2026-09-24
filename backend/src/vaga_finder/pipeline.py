"""Etapas encadeadas usadas pela API, pela CLI e pelo cron."""

from .coleta import coletar
from .config import Config
from .db import Banco
from .llm import LLM
from .matcher import avaliar_pendentes
from .perfil import carregar_perfil
from .redator import gerar_rascunhos_pendentes


class PerfilAusente(ValueError):
    pass


def _perfil():
    perfil = carregar_perfil()
    if perfil is None:
        raise PerfilAusente("Envie o currículo e gere o perfil antes de avaliar vagas.")
    return perfil


def avaliar_e_redigir(banco: Banco, cfg: Config, llm: LLM, progresso=None, limite: int | None = None) -> dict:
    perfil = _perfil()
    avaliacao = avaliar_pendentes(banco, cfg, perfil, llm, progresso, limite)
    if avaliacao["interrompido"]:
        return {"avaliacao": avaliacao}
    return {"avaliacao": avaliacao, "redacao": gerar_rascunhos_pendentes(banco, cfg, perfil, llm, progresso)}


def rodar(banco: Banco, cfg: Config, llm: LLM, progresso=None) -> dict:
    _perfil()
    return {"coleta": coletar(banco, cfg, progresso=progresso)} | avaliar_e_redigir(banco, cfg, llm, progresso)
