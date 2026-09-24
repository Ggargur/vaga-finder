"""Base dos coletores. Cada fonte devolve `Vaga`s já com texto limpo e emails extraídos."""

import html
import time
from typing import Protocol

import httpx

from ..contato import extrair_emails
from ..models import Vaga
from ..texto import consertar_mojibake, html_para_texto, normalizar

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) vaga-finder/0.1 (+https://github.com/Ggargur/vaga-finder)"
MAX_DESCRICAO = 20_000


class Fonte(Protocol):
    nome: str

    def buscar(self, termos: list[str], limite: int) -> list[Vaga]: ...


def cliente_http(**kwargs) -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": USER_AGENT, "Accept": "application/json, text/html;q=0.9"},
        timeout=30,
        follow_redirects=True,
        **kwargs,
    )


def get_com_retry(cliente: httpx.Client, url: str, tentativas: int = 3, **kwargs) -> httpx.Response:
    for tentativa in range(tentativas):
        try:
            resp = cliente.get(url, **kwargs)
            if resp.status_code in (429, 502, 503, 504) and tentativa < tentativas - 1:
                time.sleep(2 ** (tentativa + 1))
                continue
            resp.raise_for_status()
            return resp
        except httpx.TransportError:
            if tentativa == tentativas - 1:
                raise
            time.sleep(2 ** (tentativa + 1))
    raise RuntimeError("inalcançável")


def nova_vaga(
    *,
    fonte: str,
    id_fonte: object,
    titulo: str,
    url: str,
    empresa: str = "",
    descricao: str = "",
    local: str = "",
    remoto: bool | None = None,
    publicada_em: str | None = None,
) -> Vaga:
    texto = consertar_mojibake(html_para_texto(descricao))[:MAX_DESCRICAO]
    return Vaga(
        fonte=fonte,
        id_fonte=str(id_fonte),
        titulo=consertar_mojibake(html.unescape(titulo or "").strip()),
        empresa=consertar_mojibake(html.unescape(empresa or "").strip()),
        url=url,
        descricao=texto,
        emails=extrair_emails(texto),
        local=(local or "").strip(),
        remoto=remoto,
        publicada_em=publicada_em,
    )


def sem_repetidas(vagas: list[Vaga]) -> list[Vaga]:
    vistas, saida = set(), []
    for v in vagas:
        if v.id_fonte not in vistas:
            vistas.add(v.id_fonte)
            saida.append(v)
    return saida


def texto_casa_termos(texto: str, termos: list[str]) -> bool:
    """Todas as palavras de algum termo aparecem no texto (sem acento/pontuação)."""
    texto = f" {normalizar(texto)} "
    for termo in termos:
        palavras = normalizar(termo).split()
        if palavras and all(f" {p} " in texto for p in palavras):
            return True
    return not termos


def casa_termos(vaga: Vaga, termos: list[str]) -> bool:
    """Para fontes sem busca (Greenhouse, Lever, feed geral): filtra por título e descrição."""
    return texto_casa_termos(f"{vaga.titulo} {vaga.descricao}", termos)
