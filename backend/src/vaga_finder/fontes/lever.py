"""Lever: página pública de vagas de cada empresa (jobs.lever.co/<slug>)."""

import logging
from datetime import datetime, timezone

from ..models import Vaga
from .base import casa_termos, cliente_http, get_com_retry, nova_vaga

URL = "https://api.lever.co/v0/postings/{slug}"
log = logging.getLogger(__name__)


class Lever:
    nome = "lever"

    def __init__(self, empresas: list[str], cliente=None):
        self.empresas = empresas
        self.cliente = cliente or cliente_http()

    def converter(self, j: dict, slug: str) -> Vaga:
        cat = j.get("categories") or {}
        listas = "".join(f"<h3>{x.get('text', '')}</h3>{x.get('content', '')}" for x in j.get("lists") or [])
        descricao = f"{j.get('description', '')}{listas}{j.get('additional', '')}"
        data = datetime.fromtimestamp(j["createdAt"] / 1000, timezone.utc).isoformat() if j.get("createdAt") else None
        return nova_vaga(
            fonte=self.nome,
            id_fonte=f"{slug}:{j['id']}",
            titulo=j.get("text", ""),
            empresa=slug.replace("-", " ").title(),
            url=j.get("hostedUrl", ""),
            descricao=descricao,
            local=cat.get("location", ""),
            remoto=j.get("workplaceType") == "remote",
            publicada_em=data,
        )

    def buscar(self, termos: list[str], limite: int) -> list[Vaga]:
        vagas: list[Vaga] = []
        for slug in self.empresas:
            try:
                dados = get_com_retry(self.cliente, URL.format(slug=slug), params={"mode": "json"}).json()
            except Exception as e:
                log.warning("lever %s: %s", slug, e)
                continue
            achadas = [v for j in dados if casa_termos(v := self.converter(j, slug), termos)]
            vagas += achadas[:limite]
        return vagas
