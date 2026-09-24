"""Pré-filtro barato por palavras-chave e avaliação de aderência com o Claude."""

import json
import logging

from . import prompts
from .config import Config
from .db import Banco
from .llm import LLM, LimiteDeUso
from .models import Avaliacao, Vaga
from .perfil import Perfil, perfil_para_prompt
from .texto import normalizar

log = logging.getLogger(__name__)

MAX_DESCRICAO_PROMPT = 3500

SCHEMA_AVALIACOES = {
    "type": "object",
    "properties": {
        "avaliacoes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "nota": {"type": "integer", "minimum": 0, "maximum": 100},
                    "motivo": {"type": "string"},
                    "pontos_fortes": {"type": "array", "items": {"type": "string"}},
                    "lacunas": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["id", "nota", "motivo", "pontos_fortes", "lacunas"],
            },
        }
    },
    "required": ["avaliacoes"],
}


def palavras_chave(perfil: Perfil | None, cfg: Config) -> list[str]:
    if cfg.busca.palavras_chave:
        base = cfg.busca.palavras_chave
    elif perfil:
        base = perfil.palavras_chave or perfil.skills[:30]
    else:
        base = []
    base = base + cfg.busca.termos
    # termos de 1 letra ("c", "r") casariam com qualquer texto depois de normalizados
    return sorted({n for p in base if len(n := normalizar(p)) >= 2})


def prefiltro(vaga: Vaga, chaves: list[str], exclusoes: list[str]) -> str | None:
    """Devolve o motivo do descarte, ou None se a vaga deve ir para o Claude."""
    titulo = f" {normalizar(vaga.titulo)} "
    for ex in exclusoes:
        if (n := normalizar(ex)) and f" {n} " in titulo:
            return f"título contém '{ex}'"
    if not chaves:
        return None
    texto = f" {normalizar(vaga.titulo)} {normalizar(vaga.descricao)} "
    if not any(f" {c} " in texto for c in chaves):
        return "nenhuma palavra-chave do perfil"
    return None


def vaga_para_prompt(v: Vaga) -> dict:
    return {
        "id": v.id,
        "titulo": v.titulo,
        "empresa": v.empresa,
        "local": v.local,
        "remoto": v.remoto,
        "descricao": v.descricao[:MAX_DESCRICAO_PROMPT],
    }


def avaliar_lote(vagas: list[Vaga], perfil: Perfil, cfg: Config, llm: LLM) -> dict[int, Avaliacao]:
    prompt = prompts.renderizar(
        "avaliar",
        perfil=perfil_para_prompt(perfil),
        vagas=json.dumps([vaga_para_prompt(v) for v in vagas], ensure_ascii=False),
    )
    resposta = llm.json(
        prompt,
        SCHEMA_AVALIACOES,
        sistema="Você é um recrutador técnico experiente e avalia aderência de candidatos a vagas com rigor.",
        modelo=cfg.avaliacao.modelo,
    )
    ids = {v.id for v in vagas}
    saida: dict[int, Avaliacao] = {}
    for item in resposta.get("avaliacoes", []):
        if item.get("id") not in ids:
            continue
        saida[item["id"]] = Avaliacao(
            nota=max(0, min(100, int(item["nota"]))),
            motivo=item.get("motivo", ""),
            pontos_fortes=item.get("pontos_fortes", [])[:5],
            lacunas=item.get("lacunas", [])[:5],
            modelo=cfg.avaliacao.modelo,
        )
    return saida


def avaliar_pendentes(banco: Banco, cfg: Config, perfil: Perfil, llm: LLM, progresso=None, limite: int | None = None) -> dict:
    """Filtra e avalia as vagas com status 'nova'. Para cedo se a cota do Claude acabar."""
    pendentes = banco.vagas_por_status("nova", limite)
    chaves = palavras_chave(perfil, cfg)
    resumo = {"filtradas": 0, "avaliadas": 0, "falhas": 0, "interrompido": None}

    para_avaliar: list[Vaga] = []
    for v in pendentes:
        if motivo := prefiltro(v, chaves, cfg.busca.exclusoes):
            banco.marcar_filtrada(v.id, motivo)
            resumo["filtradas"] += 1
        else:
            para_avaliar.append(v)

    tamanho = max(1, cfg.avaliacao.lote)
    for i in range(0, len(para_avaliar), tamanho):
        lote = para_avaliar[i : i + tamanho]
        if progresso:
            progresso(i, len(para_avaliar), f"avaliando vagas {i + 1}-{i + len(lote)} de {len(para_avaliar)}")
        try:
            avaliacoes = avaliar_lote(lote, perfil, cfg, llm)
        except LimiteDeUso as e:
            resumo["interrompido"] = f"cota do Claude esgotada: {e}"
            break
        except Exception as e:
            log.warning("falha ao avaliar lote: %s", e)
            resumo["falhas"] += len(lote)
            continue
        for vaga_id, a in avaliacoes.items():
            banco.salvar_avaliacao(vaga_id, a)
        resumo["avaliadas"] += len(avaliacoes)
        resumo["falhas"] += len(lote) - len(avaliacoes)
    return resumo
