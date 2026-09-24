"""LinkedIn (opcional, desligado por padrão). Usa só a busca pública, sem login.

Os termos de uso do LinkedIn proíbem coleta automatizada; o IP pode ser bloqueado.
Por isso: poucas páginas por rodada, pausas longas e parada ao primeiro sinal de bloqueio.
"""

import logging
import random
import time
from urllib.parse import urlsplit, urlunsplit

import httpx
from selectolax.parser import HTMLParser

from ..models import Vaga
from .base import cliente_http, nova_vaga, sem_repetidas

LISTA = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
DETALHE = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{id}"
MAX_POR_RODADA = 50
POR_PAGINA = 10

log = logging.getLogger(__name__)


def _texto(no, seletor: str) -> str:
    alvo = no.css_first(seletor)
    return " ".join(alvo.text(deep=True).split()) if alvo else ""


def _sem_query(url: str) -> str:
    p = urlsplit(url)
    return urlunsplit((p.scheme, p.netloc, p.path, "", ""))


def cartoes(html: str) -> list[dict]:
    saida = []
    for card in HTMLParser(html).css("div.base-card[data-entity-urn]"):
        urn = card.attributes.get("data-entity-urn") or ""
        link = card.css_first("a.base-card__full-link")
        data = card.css_first("time")
        saida.append({
            "id": urn.rsplit(":", 1)[-1],
            "titulo": _texto(card, "h3.base-search-card__title"),
            "empresa": _texto(card, "h4.base-search-card__subtitle"),
            "local": _texto(card, "span.job-search-card__location"),
            "url": _sem_query(link.attributes.get("href", "")) if link else "",
            "publicada_em": data.attributes.get("datetime") if data else None,
        })
    return [c for c in saida if c["id"] and c["titulo"]]


def descricao(html: str) -> str:
    alvo = HTMLParser(html).css_first("div.description__text") or HTMLParser(html).css_first(
        "div.show-more-less-html__markup"
    )
    return alvo.html if alvo else ""


class LinkedIn:
    nome = "linkedin"

    def __init__(self, local: str = "Brasil", cliente=None, pausa: tuple[float, float] = (2.0, 5.0)):
        self.local = local
        self.cliente = cliente or cliente_http()
        self.pausa = pausa

    def _dormir(self) -> None:
        time.sleep(random.uniform(*self.pausa))

    def _get(self, url: str, **params) -> str | None:
        resp = self.cliente.get(url, params=params or None)
        if resp.status_code in (429, 999) or resp.status_code >= 500:
            log.warning("LinkedIn bloqueou ou limitou (HTTP %s); parando esta rodada", resp.status_code)
            return None
        resp.raise_for_status()
        return resp.text

    def buscar(self, termos: list[str], limite: int) -> list[Vaga]:
        limite = min(limite, MAX_POR_RODADA)
        achados: dict[str, dict] = {}
        bloqueado = False
        for termo in termos:
            for inicio in range(0, limite, POR_PAGINA):
                # f_TPR=r604800: publicadas na última semana
                html = self._get(LISTA, keywords=termo, location=self.local, start=inicio, f_TPR="r604800")
                if html is None:
                    bloqueado = True
                    break
                novos = cartoes(html)
                if not novos:
                    break
                for c in novos:
                    achados.setdefault(c["id"], c)
                self._dormir()
            if bloqueado or len(achados) >= limite:
                break

        vagas = []
        for c in list(achados.values())[:limite]:
            desc = ""
            if not bloqueado:
                try:
                    html = self._get(DETALHE.format(id=c["id"]))
                    if html is None:
                        bloqueado = True
                    else:
                        desc = descricao(html)
                except httpx.HTTPError as e:
                    log.warning("LinkedIn vaga %s: %s", c["id"], e)
                self._dormir()
            vagas.append(nova_vaga(
                fonte=self.nome,
                id_fonte=c["id"],
                titulo=c["titulo"],
                empresa=c["empresa"],
                url=c["url"] or f"https://www.linkedin.com/jobs/view/{c['id']}",
                descricao=desc,
                local=c["local"],
                remoto="remot" in c["local"].lower(),
                publicada_em=c["publicada_em"],
            ))
        return sem_repetidas(vagas)
