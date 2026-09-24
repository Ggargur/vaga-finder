"""Himalayas: vagas remotas internacionais (API pública com busca)."""

from datetime import datetime, timezone

from ..models import Vaga
from .base import cliente_http, get_com_retry, nova_vaga, sem_repetidas

URL = "https://himalayas.app/jobs/api/search"


class Himalayas:
    nome = "himalayas"

    def __init__(self, cliente=None):
        self.cliente = cliente or cliente_http()

    def converter(self, j: dict) -> Vaga:
        data = datetime.fromtimestamp(j["pubDate"], timezone.utc).isoformat() if j.get("pubDate") else None
        locais = j.get("locationRestrictions") or []
        return nova_vaga(
            fonte=self.nome,
            id_fonte=j.get("guid") or j.get("applicationLink"),
            titulo=j.get("title", ""),
            empresa=j.get("companyName", ""),
            url=j.get("applicationLink") or j.get("guid", ""),
            descricao=j.get("description") or j.get("excerpt", ""),
            local=", ".join(locais) if locais else "Remoto (qualquer lugar)",
            remoto=True,
            publicada_em=data,
        )

    def buscar(self, termos: list[str], limite: int) -> list[Vaga]:
        vagas: list[Vaga] = []
        for termo in termos:
            do_termo: list[Vaga] = []
            pagina = 1
            while len(do_termo) < limite:
                dados = get_com_retry(self.cliente, URL, params={"q": termo, "page": pagina}).json()
                itens = dados.get("jobs", [])
                if not itens:
                    break
                do_termo += [self.converter(j) for j in itens]
                pagina += 1
            vagas += do_termo[:limite]
        return sem_repetidas(vagas)
