"""Remotive: vagas remotas internacionais. API pública; pedem no máximo ~4 chamadas por dia."""

from ..models import Vaga
from .base import cliente_http, get_com_retry, nova_vaga, sem_repetidas

URL = "https://remotive.com/api/remote-jobs"


class Remotive:
    nome = "remotive"

    def __init__(self, cliente=None):
        self.cliente = cliente or cliente_http()

    def converter(self, j: dict) -> Vaga:
        return nova_vaga(
            fonte=self.nome,
            id_fonte=j["id"],
            titulo=j.get("title", ""),
            empresa=j.get("company_name", ""),
            url=j.get("url", ""),
            descricao=j.get("description", ""),
            local=j.get("candidate_required_location", ""),
            remoto=True,
            publicada_em=j.get("publication_date"),
        )

    def buscar(self, termos: list[str], limite: int) -> list[Vaga]:
        vagas: list[Vaga] = []
        for termo in termos:
            resp = get_com_retry(self.cliente, URL, params={"search": termo, "limit": limite})
            vagas += [self.converter(j) for j in resp.json().get("jobs", [])]
        return sem_repetidas(vagas)
