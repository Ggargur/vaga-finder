"""RemoteOK: vagas remotas. A API pública pede link de volta para remoteok.com (o link da vaga já aponta para lá)."""

from datetime import datetime, timezone

from ..models import Vaga
from ..texto import normalizar
from .base import casa_termos, cliente_http, get_com_retry, nova_vaga, sem_repetidas

URL = "https://remoteok.com/api"


class RemoteOK:
    nome = "remoteok"

    def __init__(self, cliente=None):
        self.cliente = cliente or cliente_http()

    def converter(self, j: dict) -> Vaga:
        data = j.get("date")
        if not data and j.get("epoch"):
            data = datetime.fromtimestamp(j["epoch"], timezone.utc).isoformat()
        return nova_vaga(
            fonte=self.nome,
            id_fonte=j["id"],
            titulo=j.get("position", ""),
            empresa=j.get("company", ""),
            url=j.get("url") or j.get("apply_url", ""),
            descricao=j.get("description", "") + (f"<p>Tags: {', '.join(j['tags'])}</p>" if j.get("tags") else ""),
            local=j.get("location", "") or "Remoto",
            remoto=True,
            publicada_em=data,
        )

    def _feed(self, **params) -> list[dict]:
        dados = get_com_retry(self.cliente, URL, params=params or None).json()
        # o primeiro item é o aviso legal, sem "id"
        return [j for j in dados if isinstance(j, dict) and j.get("id") and j.get("position")]

    def buscar(self, termos: list[str], limite: int) -> list[Vaga]:
        itens = self._feed()
        for termo in termos:
            if len(palavras := normalizar(termo).split()) == 1:
                itens += self._feed(tag=palavras[0])
        vagas = [v for v in map(self.converter, itens) if casa_termos(v, termos)]
        return sem_repetidas(vagas)[:limite]
