"""Página de carreira qualquer. Em ordem:
1. se a página (ou um link nela) é de um ATS com API pública (Greenhouse, Lever, Ashby), usa a API;
2. lê JobPosting em JSON-LD (padrão do Google for Jobs);
3. segue os links cujo texto bate com os termos de busca.
Páginas montadas só com JavaScript e sem link para ATS não funcionam."""

import json
import logging
import re
import time
from urllib.parse import urljoin, urlparse

from selectolax.parser import HTMLParser

from ..models import Vaga
from ..texto import normalizar
from .ashby import Ashby
from .base import cliente_http, get_com_retry, nova_vaga, sem_repetidas
from .greenhouse import Greenhouse
from .lever import Lever

log = logging.getLogger(__name__)

_ATS = {
    "greenhouse": re.compile(r"(?:boards|job-boards)(?:-api)?\.greenhouse\.io/(?:embed/job_board\?for=|v1/boards/)?([\w-]+)", re.I),
    "lever": re.compile(r"jobs\.lever\.co/([\w-]+)", re.I),
    "ashby": re.compile(r"jobs\.ashbyhq\.com/([\w.-]+)", re.I),
}
_SLUGS_IGNORADOS = {"embed", "api", "v1", "jobs", "job"}


def ats_citados(html: str, url: str) -> dict[str, list[str]]:
    """Slugs de ATS conhecidos na própria URL ou nos links da página."""
    achados: dict[str, list[str]] = {}
    alvos = [url] + [a.attributes.get("href") or "" for a in HTMLParser(html).css("a[href]")] if html else [url]
    for alvo in alvos:
        for nome, padrao in _ATS.items():
            if (m := padrao.search(alvo)) and (slug := m.group(1).lower()) not in _SLUGS_IGNORADOS:
                lista = achados.setdefault(nome, [])
                if slug not in lista:
                    lista.append(slug)
    return achados


def fontes_de_ats(achados: dict[str, list[str]], cliente) -> list:
    classes = {"greenhouse": Greenhouse, "lever": Lever, "ashby": Ashby}
    return [classes[nome](slugs, cliente) for nome, slugs in achados.items()]


def _empresa_da_pagina(arvore: HTMLParser, url: str) -> str:
    meta = arvore.css_first('meta[property="og:site_name"]')
    if meta and meta.attributes.get("content"):
        return meta.attributes["content"].strip()
    host = (urlparse(url).hostname or "").removeprefix("www.")
    return host.split(".")[0].replace("-", " ").title()


def _objetos_jsonld(arvore: HTMLParser) -> list[dict]:
    objetos: list[dict] = []
    for script in arvore.css('script[type="application/ld+json"]'):
        try:
            dados = json.loads(script.text(deep=True) or "null", strict=False)
        except json.JSONDecodeError:
            continue
        pilha = dados if isinstance(dados, list) else [dados]
        while pilha:
            o = pilha.pop()
            if isinstance(o, dict):
                objetos.append(o)
                pilha.extend(o.get("@graph", []) if isinstance(o.get("@graph"), list) else [])
    return objetos


def _texto_jsonld(valor) -> str:
    """Campos do schema.org podem vir como texto, objeto ({"name": ...}) ou lista."""
    if isinstance(valor, str):
        return "" if valor.strip().lower() in ("null", "none") else valor.strip()
    if isinstance(valor, list):
        return ", ".join(t for t in map(_texto_jsonld, valor) if t)
    if isinstance(valor, dict):
        return _texto_jsonld(valor.get("name") or "")
    return ""


def _local_jsonld(local) -> str:
    if isinstance(local, list):
        return ", ".join(dict.fromkeys(t for t in map(_local_jsonld, local) if t))
    if not isinstance(local, dict):
        return _texto_jsonld(local)
    endereco = local.get("address")
    if not isinstance(endereco, dict):
        return _texto_jsonld(endereco) or _texto_jsonld(local.get("name"))
    for campo in ("addressLocality", "addressRegion", "addressCountry"):
        if texto := _texto_jsonld(endereco.get(campo)):
            return texto
    return ""


def vagas_jsonld(html: str, url: str, fonte: str = "pagina") -> list[Vaga]:
    arvore = HTMLParser(html)
    vagas = []
    for o in _objetos_jsonld(arvore):
        tipo = o.get("@type")
        if tipo != "JobPosting" and not (isinstance(tipo, list) and "JobPosting" in tipo):
            continue
        link = o.get("url") if isinstance(o.get("url"), str) else url
        vagas.append(
            nova_vaga(
                fonte=fonte,
                id_fonte=link if link != url else f"{url}#{_texto_jsonld(o.get('title'))}",
                titulo=_texto_jsonld(o.get("title")),
                empresa=_texto_jsonld(o.get("hiringOrganization")),
                url=link,
                descricao=_texto_jsonld(o.get("description")),
                local=_local_jsonld(o.get("jobLocation")),
                remoto=o.get("jobLocationType") == "TELECOMMUTE" or None,
                publicada_em=o.get("datePosted"),
            )
        )
    return vagas


def links_de_vagas(html: str, url: str, termos: list[str]) -> list[tuple[str, str]]:
    """(url, texto) dos links cujo texto contém todas as palavras de algum termo."""
    termos_n = [normalizar(t).split() for t in termos if normalizar(t)]
    vistos, saida = set(), []
    for a in HTMLParser(html).css("a[href]"):
        texto = " ".join(a.text(deep=True).split())
        href = urljoin(url, a.attributes.get("href") or "")
        if not texto or not href.startswith("http") or href in vistos or href.split("#")[0] == url:
            continue
        n = f" {normalizar(texto)} "
        if any(all(f" {p} " in n for p in palavras) for palavras in termos_n):
            vistos.add(href)
            saida.append((href, texto))
    return saida


def vaga_da_pagina(html: str, url: str, titulo_link: str, empresa_padrao: str, fonte: str = "pagina") -> Vaga:
    if achadas := vagas_jsonld(html, url, fonte):
        v = achadas[0]
        v.url, v.id_fonte = url, url
        v.empresa = v.empresa or empresa_padrao
        return v
    arvore = HTMLParser(html)
    for tag in arvore.css("script, style, nav, header, footer, noscript"):
        tag.decompose()
    h1 = arvore.css_first("h1")
    corpo = arvore.css_first("main") or arvore.css_first("article") or arvore.body
    return nova_vaga(
        fonte=fonte,
        id_fonte=url,
        titulo=(h1.text(deep=True).strip() if h1 else "") or titulo_link,
        empresa=empresa_padrao,
        url=url,
        descricao=corpo.html if corpo else "",
    )


class PaginaGenerica:
    nome = "pagina"

    def __init__(self, urls: list[str], cliente=None, pausa_s: float = 1.0):
        self.urls = urls
        self.cliente = cliente or cliente_http()
        self.pausa_s = pausa_s

    def buscar(self, termos: list[str], limite: int) -> list[Vaga]:
        vagas: list[Vaga] = []
        for url in self.urls:
            if direto := ats_citados("", url):
                for fonte in fontes_de_ats(direto, self.cliente):
                    vagas += fonte.buscar(termos, limite)
                continue
            try:
                html = get_com_retry(self.cliente, url).text
            except Exception as e:
                log.warning("página %s: %s", url, e)
                continue
            empresa = _empresa_da_pagina(HTMLParser(html), url)
            achadas = vagas_jsonld(html, url)
            if not achadas and (ats := ats_citados(html, url)):
                log.info("página %s usa ATS %s", url, ats)
                for fonte in fontes_de_ats(ats, self.cliente):
                    achadas += fonte.buscar(termos, limite)
            for v in achadas:
                v.empresa = v.empresa or empresa
            if not achadas:
                for link, texto in links_de_vagas(html, url, termos)[:limite]:
                    time.sleep(self.pausa_s)
                    try:
                        achadas.append(vaga_da_pagina(get_com_retry(self.cliente, link).text, link, texto, empresa))
                    except Exception as e:
                        log.warning("vaga %s: %s", link, e)
            vagas += achadas[:limite]
        return sem_repetidas(vagas)
