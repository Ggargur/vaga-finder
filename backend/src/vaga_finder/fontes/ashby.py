"""Ashby: quadro de vagas público de cada empresa (jobs.ashbyhq.com/<slug>)."""

import logging

from ..models import Vaga
from .base import casa_termos, cliente_http, get_com_retry, nova_vaga

URL = "https://api.ashbyhq.com/posting-api/job-board/{slug}"
log = logging.getLogger(__name__)


class Ashby:
    nome = "ashby"

    def __init__(self, empresas: list[str], cliente=None):
        self.empresas = empresas
        self.cliente = cliente or cliente_http()

    def converter(self, j: dict, slug: str) -> Vaga:
        return nova_vaga(
            fonte=self.nome,
            id_fonte=f"{slug}:{j['id']}",
            titulo=j.get("title", ""),
            empresa=slug.replace("-", " ").title(),
            url=j.get("jobUrl") or j.get("applyUrl", ""),
            descricao=j.get("descriptionHtml") or j.get("descriptionPlain", ""),
            local=j.get("location", ""),
            remoto=bool(j.get("isRemote")) or j.get("workplaceType") == "Remote",
            publicada_em=j.get("publishedAt"),
        )

    def buscar(self, termos: list[str], limite: int) -> list[Vaga]:
        vagas: list[Vaga] = []
        for slug in self.empresas:
            try:
                dados = get_com_retry(self.cliente, URL.format(slug=slug)).json()
            except Exception as e:
                log.warning("ashby %s: %s", slug, e)
                continue
            achadas = [
                v for j in dados.get("jobs", []) if j.get("isListed", True) and casa_termos(v := self.converter(j, slug), termos)
            ]
            vagas += achadas[:limite]
        return vagas
