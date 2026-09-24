"""Greenhouse: quadro de vagas público de cada empresa (boards.greenhouse.io/<slug>)."""

import logging

from ..models import Vaga
from .base import casa_termos, cliente_http, get_com_retry, nova_vaga

URL = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
log = logging.getLogger(__name__)


class Greenhouse:
    nome = "greenhouse"

    def __init__(self, empresas: list[str], cliente=None):
        self.empresas = empresas
        self.cliente = cliente or cliente_http()

    def converter(self, j: dict, slug: str) -> Vaga:
        local = (j.get("location") or {}).get("name", "")
        return nova_vaga(
            fonte=self.nome,
            id_fonte=f"{slug}:{j['id']}",
            titulo=j.get("title", ""),
            empresa=j.get("company_name") or slug.replace("-", " ").title(),
            url=j.get("absolute_url", ""),
            descricao=j.get("content", ""),
            local=local,
            remoto="remote" in local.lower() or "remoto" in local.lower(),
            publicada_em=j.get("first_published") or j.get("updated_at"),
        )

    def buscar(self, termos: list[str], limite: int) -> list[Vaga]:
        vagas: list[Vaga] = []
        for slug in self.empresas:
            try:
                dados = get_com_retry(self.cliente, URL.format(slug=slug), params={"content": "true"}).json()
            except Exception as e:  # slug errado não derruba as outras empresas
                log.warning("greenhouse %s: %s", slug, e)
                continue
            achadas = [v for j in dados.get("jobs", []) if casa_termos(v := self.converter(j, slug), termos)]
            vagas += achadas[:limite]
        return vagas
