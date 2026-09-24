"""Gupy: portal de vagas usado por muitas empresas brasileiras (API pública do portal)."""

from urllib.parse import urlparse

from ..models import Vaga
from .base import cliente_http, get_com_retry, nova_vaga, sem_repetidas

URL = "https://employability-portal.gupy.io/api/v1/jobs"
POR_PAGINA = 50


def empresa_da_url(url: str) -> str:
    """'https://fcamara.gupy.io/job/...' → 'fcamara'. O careerPageName costuma ser um slogan."""
    host = urlparse(url or "").hostname or ""
    sub = host.split(".")[0] if host.endswith(".gupy.io") else ""
    return sub.replace("-", " ").title() if sub else ""


class Gupy:
    nome = "gupy"

    def __init__(self, cliente=None):
        self.cliente = cliente or cliente_http()

    def converter(self, j: dict) -> Vaga:
        local = ", ".join(p for p in (j.get("city"), j.get("state")) if p)
        remoto = bool(j.get("isRemoteWork")) or j.get("workplaceType") == "remote"
        return nova_vaga(
            fonte=self.nome,
            id_fonte=j["id"],
            titulo=j.get("name", ""),
            empresa=empresa_da_url(j.get("jobUrl") or j.get("careerPageUrl", "")),
            url=j.get("jobUrl", ""),
            descricao=j.get("description", ""),
            local=local or ("Remoto" if remoto else ""),
            remoto=remoto,
            publicada_em=j.get("publishedDate"),
        )

    def buscar(self, termos: list[str], limite: int) -> list[Vaga]:
        vagas: list[Vaga] = []
        for termo in termos:
            offset = 0
            while offset < limite:
                resp = get_com_retry(
                    self.cliente,
                    URL,
                    params={"jobName": termo, "offset": offset, "limit": min(POR_PAGINA, limite - offset)},
                )
                dados = resp.json()
                itens = dados.get("data", [])
                vagas += [self.converter(j) for j in itens]
                total = dados.get("pagination", {}).get("total", 0)
                offset += len(itens)
                if not itens or offset >= total:
                    break
        return sem_repetidas(vagas)
