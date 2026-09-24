"""Coleta: consulta as fontes ligadas e grava as vagas novas."""

import logging
from collections.abc import Callable

from .config import Config
from .db import Banco
from .fontes import Fonte, fontes_ativas

log = logging.getLogger(__name__)

Progresso = Callable[[int, int, str], None]


def coletar(
    banco: Banco,
    cfg: Config,
    fontes: list[Fonte] | None = None,
    progresso: Progresso | None = None,
) -> dict:
    fontes = fontes if fontes is not None else fontes_ativas(cfg)
    resumo: dict = {"novas": 0, "repetidas": 0, "por_fonte": {}, "erros": {}}
    for i, fonte in enumerate(fontes):
        if progresso:
            progresso(i, len(fontes), f"buscando em {fonte.nome}")
        try:
            vagas = fonte.buscar(cfg.busca.termos, cfg.busca.limite_por_fonte)
        except Exception as e:  # uma fonte fora do ar não derruba as outras
            log.warning("fonte %s falhou: %s", fonte.nome, e)
            resumo["erros"][fonte.nome] = str(e)[:300]
            continue
        novas, repetidas = banco.inserir_vagas(vagas)
        resumo["novas"] += novas
        resumo["repetidas"] += repetidas
        resumo["por_fonte"][fonte.nome] = {"coletadas": len(vagas), "novas": novas}
    if progresso:
        progresso(len(fontes), len(fontes), "coleta concluída")
    return resumo
