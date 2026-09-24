"""Utilitários de texto: normalização, impressão digital de vaga e HTML → texto."""

import hashlib
import html
import re
import unicodedata

from selectolax.parser import HTMLParser

# palavras que variam entre fontes para a mesma vaga e não ajudam a identificá-la
_RUIDO_TITULO = re.compile(
    r"\b(remote|remoto|remota|hibrido|hybrid|presencial|vaga|pj|clt|"
    r"full[- ]?time|part[- ]?time|home office)\b"
)
_SUFIXOS_EMPRESA = re.compile(r"\b(ltda|s\.?a\.?|inc|llc|ltd|gmbh|corp|corporation|me|eireli)\b\.?")


def normalizar(texto: str) -> str:
    """Minúsculas, sem acento, só letras/números separados por um espaço."""
    sem_acento = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", sem_acento.lower()).strip()


def impressao_vaga(empresa: str, titulo: str) -> str:
    """Identifica a mesma vaga publicada em fontes diferentes."""
    emp = _SUFIXOS_EMPRESA.sub(" ", normalizar(empresa))
    tit = _RUIDO_TITULO.sub(" ", normalizar(titulo))
    tit = re.sub(r"\([^)]*\)", " ", tit)
    chave = " ".join(emp.split()) + "|" + " ".join(tit.split())
    return hashlib.sha1(chave.encode()).hexdigest()[:16]


def html_para_texto(conteudo: str) -> str:
    if not conteudo:
        return ""
    conteudo = html.unescape(conteudo) if "&lt;" in conteudo else conteudo
    if "<" not in conteudo:
        return conteudo.strip()
    arvore = HTMLParser(conteudo)
    for tag in arvore.css("script, style"):
        tag.decompose()
    for tag in arvore.css("br, p, li, h1, h2, h3, h4, div"):
        tag.insert_after("\n")
    texto = arvore.text(separator="")
    texto = re.sub(r"[ \t\xa0]+", " ", texto)
    return re.sub(r"\n\s*\n+", "\n\n", texto).strip()


def consertar_mojibake(texto: str) -> str:
    """Corrige UTF-8 lido como Latin-1 (ex.: 'weâ\\x80\\x99re'), comum no RemoteOK."""
    if not texto or not re.search(r"[ÃÂâ][\x80-\xbf€™œ]", texto):
        return texto
    for codificacao in ("latin-1", "cp1252"):
        try:
            return texto.encode(codificacao).decode("utf-8")
        except UnicodeError:
            continue
    return texto
