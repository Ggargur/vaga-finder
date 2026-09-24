"""Emails de contato publicados na descrição da vaga. Nunca deduz endereços."""

import re

_EMAIL = re.compile(r"(?<![\w.+-])([a-z0-9][a-z0-9._%+-]*@[a-z0-9-]+(?:\.[a-z0-9-]+)*\.[a-z]{2,24})(?![\w-])", re.I)
_OFUSCADO = [
    (re.compile(r"\s*[\[\(\{]\s*(?:at|arroba)\s*[\]\)\}]\s*", re.I), "@"),
    (re.compile(r"\s*[\[\(\{]\s*(?:dot|ponto)\s*[\]\)\}]\s*", re.I), "."),
]
_EXTENSOES_ARQUIVO = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".pdf")
# endereços publicados na vaga que não servem para candidatura
_LOCAIS_IGNORADOS = re.compile(
    r"^(no-?reply|do-?not-?reply|nao-?responda|mailer-daemon|privacy|privacidade|dpo|lgpd|gdpr|"
    r"accommodations?|accessibility|acessibilidade|abuse|security|seguranca|billing|invoice|"
    r"sales|vendas|press|imprensa|legal|juridico|ouvidoria|sac|example|exemplo|test|teste|email|seuemail|nome)$",
    re.I,
)
_DOMINIOS_IGNORADOS = re.compile(r"(^|\.)(example\.(com|org)|exemplo\.com|sentry\.io|domain\.com|email\.com)$", re.I)
# endereços com cara de recrutamento vão primeiro
_LOCAIS_RECRUTAMENTO = re.compile(
    r"(rh|hr|jobs?|careers?|carreiras?|vagas?|talent|talentos?|recruit|recrutamento|selecao|people|pessoas|hiring)",
    re.I,
)


def _cortar_palavra_colada(email: str) -> str:
    """A Gupy cola frases sem espaço: 'rh@acme.com.brNosso time' → 'rh@acme.com.br'."""
    local, _, dominio = email.partition("@")
    rotulos = dominio.split(".")
    ultimo = re.match(r"[a-z0-9-]+?(?=[A-Z][a-z])", rotulos[-1])
    if ultimo and len(ultimo.group(0)) >= 2:
        rotulos[-1] = ultimo.group(0)
    return f"{local}@{'.'.join(rotulos)}"


def extrair_emails(texto: str) -> list[str]:
    if not texto:
        return []
    minusculo = texto.lower()
    if "@" not in texto and "arroba" not in minusculo and "at]" not in minusculo and "at)" not in minusculo:
        return []
    for padrao, troca in _OFUSCADO:
        texto = padrao.sub(troca, texto)
    encontrados: list[str] = []
    for m in _EMAIL.finditer(texto):
        email = _cortar_palavra_colada(m.group(1)).lower().rstrip(".")
        local, _, dominio = email.partition("@")
        if (
            email.endswith(_EXTENSOES_ARQUIVO)
            or _LOCAIS_IGNORADOS.match(local)
            or _DOMINIOS_IGNORADOS.search(dominio)
            or email in encontrados
        ):
            continue
        encontrados.append(email)
    return sorted(encontrados, key=lambda e: not _LOCAIS_RECRUTAMENTO.search(e.split("@")[0]))
