from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from .texto import impressao_vaga

StatusVaga = Literal["nova", "filtrada", "avaliada", "aplicada"]
StatusRascunho = Literal["pendente", "aprovado", "rejeitado", "enviado", "erro"]
OrigemEnvio = Literal["ferramenta", "gmail", "manual"]


def agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Vaga(BaseModel):
    id: int | None = None
    fonte: str
    id_fonte: str
    titulo: str
    empresa: str = ""
    local: str = ""
    remoto: bool | None = None
    url: str
    descricao: str = ""
    emails: list[str] = Field(default_factory=list)
    publicada_em: str | None = None
    coletada_em: str = Field(default_factory=agora)
    status: StatusVaga = "nova"
    motivo_filtro: str | None = None

    @property
    def impressao(self) -> str:
        return impressao_vaga(self.empresa, self.titulo)


class Avaliacao(BaseModel):
    nota: int = Field(ge=0, le=100)
    motivo: str
    pontos_fortes: list[str] = Field(default_factory=list)
    lacunas: list[str] = Field(default_factory=list)
    modelo: str = ""


class Aviso(BaseModel):
    tipo: Literal["slop", "historico", "contato"]
    mensagem: str
    trecho: str | None = None


class Rascunho(BaseModel):
    id: int | None = None
    vaga_id: int
    destinatario: str
    assunto: str
    corpo: str
    idioma: str = "pt"
    status: StatusRascunho = "pendente"
    avisos: list[Aviso] = Field(default_factory=list)
    erro: str | None = None
    criado_em: str = Field(default_factory=agora)
    atualizado_em: str = Field(default_factory=agora)


class Envio(BaseModel):
    id: int | None = None
    vaga_id: int | None = None
    impressao: str | None = None
    destinatario: str | None = None
    empresa: str = ""
    titulo: str = ""
    assunto: str = ""
    corpo: str = ""
    url: str | None = None
    enviado_em: str = Field(default_factory=agora)
    message_id: str | None = None
    origem: OrigemEnvio = "ferramenta"


class Tarefa(BaseModel):
    id: int | None = None
    tipo: str
    status: Literal["rodando", "concluida", "erro"] = "rodando"
    progresso: int = 0
    total: int = 0
    mensagem: str = ""
    resultado: dict = Field(default_factory=dict)
    criada_em: str = Field(default_factory=agora)
    terminada_em: str | None = None
