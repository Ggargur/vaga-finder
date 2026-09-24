"""Checagem local dos padrões do stop-slop que sobreviveram à revisão do Claude."""

import re
from functools import lru_cache

from .models import Aviso
from .prompts import PASTA_STOP_SLOP, frases_proibidas

_ESTRUTURAS = [
    (re.compile(r"—|\s–\s"), "Travessão: troque por vírgula ou ponto."),
    (
        re.compile(r"\bnão (?:é|foi|são)\b[^.!?]{1,60}[,;] (?:mas |e sim )?(?:é|foi|são)\b", re.I),
        "Contraste “não é X, é Y”: diga Y direto.",
    ),
    (re.compile(r"\bnão (?:apenas|só|somente)\b[^.!?]{1,80}\bmas (?:também)?", re.I), "“Não apenas X, mas Y”: diga direto."),
    (re.compile(r"\b(?:isn't|is not|wasn't|not)\b[^.!?]{1,60}[,;.] (?:it's|it is|it was)\b", re.I), "“Not X, it's Y”: state Y directly."),
    (re.compile(r"\bnot (?:just|only)\b[^.!?]{1,80}\bbut\b", re.I), "“Not just X but Y”: state it directly."),
    (re.compile(r"\bhere'?s (?:what|why|the thing|how)\b", re.I), "“Here's what/why”: cut the setup."),
]


# entradas das listas que dão falso positivo fora do contexto original ("probation period")
_IGNORAR = {"period"}


@lru_cache
def _frases() -> list[tuple[re.Pattern, str]]:
    frases = frases_proibidas(PASTA_STOP_SLOP / "phrases.md") + frases_proibidas(PASTA_STOP_SLOP / "pt-br.md")
    vistas, saida = set(_IGNORAR), []
    for f in frases:
        chave = f.lower()
        if chave in vistas:
            continue
        vistas.add(chave)
        saida.append((re.compile(r"(?<!\w)" + re.escape(f) + r"(?!\w)", re.I), f))
    return saida


def contar_palavras(texto: str) -> int:
    return len(re.findall(r"\b\w+\b", texto))


def verificar(texto: str, palavras_min: int | None = None, palavras_max: int | None = None) -> list[Aviso]:
    avisos: list[Aviso] = []
    for padrao, frase in _frases():
        if m := padrao.search(texto):
            avisos.append(Aviso(tipo="slop", mensagem=f"Frase de enchimento: “{frase}”.", trecho=m.group(0)))
    for padrao, mensagem in _ESTRUTURAS:
        if m := padrao.search(texto):
            avisos.append(Aviso(tipo="slop", mensagem=mensagem, trecho=m.group(0)))
    n = contar_palavras(texto)
    if palavras_min and n < palavras_min * 0.8:
        avisos.append(Aviso(tipo="slop", mensagem=f"Texto curto: {n} palavras (alvo {palavras_min}-{palavras_max})."))
    if palavras_max and n > palavras_max * 1.25:
        avisos.append(Aviso(tipo="slop", mensagem=f"Texto longo: {n} palavras (alvo {palavras_min}-{palavras_max})."))
    return avisos
