"""Sites de vagas da indústria de games.

Cada site é descrito por um `Quadro`: de onde vêm os links (RSS, sitemap, busca ou página de
listagem), qual o formato do link de uma vaga e a pausa entre requisições (o Crawl-delay do
robots.txt de cada site). Os detalhes da vaga vêm do JSON-LD JobPosting da página; sem JSON-LD,
do <h1> e do conteúdo principal.

Games Jobs Direct ficou de fora: o robots.txt proíbe qualquer robô. Gamejobs.co bloqueia (403).
"""

import logging
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus, urljoin, urlparse

from selectolax.parser import HTMLParser

from ..models import Vaga
from .base import cliente_http, get_com_retry, sem_repetidas, texto_casa_termos
from .pagina_generica import vaga_da_pagina

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Quadro:
    chave: str
    nome: str
    descricao: str
    modo: str  # rss | sitemap | busca | pagina
    url: str  # na busca, com {termo}
    padrao_link: str  # regex do link de uma vaga
    pausa_s: float
    max_detalhes: int = 30
    idade_max_dias: int = 30
    seletor_empresa: str | None = None  # quando a página não tem JSON-LD


QUADROS: dict[str, Quadro] = {
    q.chave: q
    for q in [
        Quadro(
            "hitmarker", "Hitmarker", "O maior quadro de vagas de games e esports.",
            "sitemap", "https://hitmarker.net/sitemap-jobs.xml/p1",
            r"^https://hitmarker\.net/jobs/[\w-]+$", 1.0,
        ),
        Quadro(
            "remotegamejobs", "Remote Game Jobs", "Vagas remotas em estúdios de games.",
            "rss", "https://remotegamejobs.com/feed.rss",
            r"^https://remotegamejobs\.com/jobs/[\w-]+$", 1.0,
        ),
        Quadro(
            "workwithindies", "Work With Indies", "Vagas em estúdios independentes.",
            "pagina", "https://www.workwithindies.com/",
            r"^https://www\.workwithindies\.com/careers/[\w-]+$", 1.0,
        ),
        Quadro(
            "ingamejob", "InGame Job", "Quadro internacional de vagas de games.",
            "busca", "https://ingamejob.com/en/jobs?q={termo}",
            r"^https://ingamejob\.com/en/job/[\w-]+$", 5.0, max_detalhes=15,
            seletor_empresa='a[href*="/en/company/"]',
        ),
        Quadro(
            "gamesindustry", "GamesIndustry.biz Jobs", "Quadro de vagas do GamesIndustry.biz (lento: 10s por página).",
            "busca", "https://jobs.gamesindustry.biz/jobs?search={termo}",
            r"^https://jobs\.gamesindustry\.biz/job/[\w-]+$", 10.0, max_detalhes=10,
        ),
    ]
}

# Estúdios de games com quadro público confirmado (setembro de 2026)
ESTUDIOS: dict[str, list[str]] = {
    "greenhouse": [
        "riotgames", "epicgames", "wildlifestudios", "roblox", "scopely",
        "bungie", "insomniac", "naughtydog",
    ],
    "lever": ["kabam", "jamcity"],
    "ashby": ["supercell", "voodoo", "believer"],
}


def _texto_do_slug(url: str) -> str:
    return urlparse(url).path.rsplit("/", 1)[-1].replace("-", " ")


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


class SiteGames:
    def __init__(self, chave: str, cliente=None, pausa_s: float | None = None, agora: datetime | None = None):
        self.quadro = QUADROS[chave]
        self.nome = chave
        self.cliente = cliente or cliente_http()
        self.pausa_s = self.quadro.pausa_s if pausa_s is None else pausa_s
        self.agora = agora
        self._primeira = True

    def _get(self, url: str) -> str:
        # respeita o Crawl-delay entre todas as requisições ao site
        if not self._primeira:
            time.sleep(self.pausa_s)
        self._primeira = False
        return get_com_retry(self.cliente, url).text

    def _empresa(self, html: str) -> str:
        for no in HTMLParser(html).css(self.quadro.seletor_empresa):
            if texto := " ".join(no.text(deep=True).split()):
                return texto
        return ""

    def _email_do_site(self, email: str) -> bool:
        dominio = email.rsplit("@", 1)[-1]
        site = (urlparse(self.quadro.url).hostname or "").removeprefix("www.").removeprefix("jobs.")
        return dominio == site or dominio.endswith("." + site)

    def _casa_link(self, url: str) -> bool:
        return bool(re.match(self.quadro.padrao_link, url))

    # ---- candidatos: (url, texto usado para filtrar pelos termos) ----

    def candidatos_rss(self, xml: str, termos: list[str]) -> list[str]:
        saida = []
        for item in ET.fromstring(xml).iter("item"):
            link = (item.findtext("link") or "").strip()
            texto = f"{item.findtext('title') or ''} {item.findtext('description') or ''}"
            if self._casa_link(link) and texto_casa_termos(texto, termos):
                saida.append(link)
        return saida

    def candidatos_sitemap(self, xml: str, termos: list[str]) -> list[str]:
        limite = (self.agora or datetime.now(timezone.utc)) - timedelta(days=self.quadro.idade_max_dias)
        saida = []
        for url in ET.fromstring(xml):
            campos = {_local(c.tag): (c.text or "").strip() for c in url}
            loc, lastmod = campos.get("loc", ""), campos.get("lastmod")
            if not self._casa_link(loc):
                continue
            if lastmod:
                try:
                    if datetime.fromisoformat(lastmod) < limite:
                        continue
                except ValueError:
                    pass
            if texto_casa_termos(_texto_do_slug(loc), termos):
                saida.append(loc)
        return saida

    def candidatos_html(self, html: str, base: str, termos: list[str] | None) -> list[str]:
        """Links de vaga numa página. Com `termos`, filtra pelo texto do link (listagem);
        sem, aceita todos (resultado de busca, já filtrado pelo site)."""
        saida = []
        for a in HTMLParser(html).css("a[href]"):
            link = urljoin(base, a.attributes.get("href") or "").split("?")[0].split("#")[0]
            if not self._casa_link(link) or link in saida:
                continue
            texto = f"{a.text(deep=True)} {_texto_do_slug(link)}"
            if termos is None or texto_casa_termos(texto, termos):
                saida.append(link)
        return saida

    def candidatos(self, termos: list[str]) -> list[str]:
        q = self.quadro
        if q.modo == "rss":
            return self.candidatos_rss(self._get(q.url), termos)
        if q.modo == "sitemap":
            return self.candidatos_sitemap(self._get(q.url), termos)
        if q.modo == "pagina":
            return self.candidatos_html(self._get(q.url), q.url, termos)
        links: list[str] = []
        for termo in termos:
            url = q.url.format(termo=quote_plus(termo))
            links += [x for x in self.candidatos_html(self._get(url), url, None) if x not in links]
        return links

    def buscar(self, termos: list[str], limite: int) -> list[Vaga]:
        links = self.candidatos(termos)[: min(limite, self.quadro.max_detalhes)]
        vagas = []
        for link in links:
            try:
                html = self._get(link)
            except Exception as e:
                log.warning("%s: vaga %s: %s", self.nome, link, e)
                continue
            vaga = vaga_da_pagina(html, link, _texto_do_slug(link), "", fonte=self.nome)
            vaga.id_fonte = link
            if not vaga.empresa and self.quadro.seletor_empresa:
                vaga.empresa = self._empresa(html)
            # o rodapé do quadro tem os emails do próprio site; não são contato da vaga
            vaga.emails = [e for e in vaga.emails if not self._email_do_site(e)]
            vagas.append(vaga)
        return sem_repetidas(vagas)

