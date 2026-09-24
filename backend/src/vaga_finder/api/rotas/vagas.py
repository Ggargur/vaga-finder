from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr

from ... import historico
from ...config import carregar_config
from ...llm import LimiteDeUso
from ...models import Envio, Rascunho
from ...perfil import carregar_perfil
from ...redator import gerar_rascunho
from ..deps import Servicos, servicos

router = APIRouter(prefix="/vagas", tags=["vagas"])


@router.get("")
def listar(
    status: str | None = None,
    fonte: str | None = None,
    nota_min: int | None = None,
    com_email: bool | None = None,
    busca: str | None = None,
    limite: int = 200,
    offset: int = 0,
    s: Servicos = Depends(servicos),
) -> list[dict]:
    return s.banco.listar_vagas(
        status=status, fonte=fonte, nota_min=nota_min, com_email=com_email, busca=busca, limite=limite, offset=offset
    )


def _vaga_ou_404(s: Servicos, vaga_id: int):
    if not (v := s.banco.obter_vaga(vaga_id)):
        raise HTTPException(404, "Vaga não encontrada.")
    return v


@router.get("/{vaga_id}")
def detalhe(vaga_id: int, s: Servicos = Depends(servicos)) -> dict:
    v = _vaga_ou_404(s, vaga_id)
    a = s.banco.obter_avaliacao(v.id)
    checagem = historico.verificar(s.banco, v, v.emails[0] if v.emails else None, carregar_config())
    return {
        **v.model_dump(),
        "avaliacao": a.model_dump() if a else None,
        "rascunhos": [r.model_dump() for r in s.banco.listar_rascunhos() if r.vaga_id == v.id],
        "envios": [e.model_dump() for e in s.banco.envios_da_vaga(v.id, v.impressao)],
        "historico": {"bloqueado": checagem.bloqueado, "avisos": [x.model_dump() for x in checagem.avisos]},
    }


@router.post("/{vaga_id}/aplicada")
def marcar_aplicada(vaga_id: int, s: Servicos = Depends(servicos)) -> Envio:
    """Você se candidatou pelo link da vaga: entra no histórico com origem 'manual'."""
    v = _vaga_ou_404(s, vaga_id)
    envio = Envio(vaga_id=v.id, impressao=v.impressao, empresa=v.empresa, titulo=v.titulo, url=v.url, origem="manual")
    envio.id = s.banco.registrar_envio(envio)
    s.banco.marcar_status(v.id, "aplicada")
    return envio


@router.post("/{vaga_id}/descartar")
def descartar(vaga_id: int, s: Servicos = Depends(servicos)) -> dict:
    v = _vaga_ou_404(s, vaga_id)
    s.banco.marcar_filtrada(v.id, "descartada por você")
    return {"ok": True}


class PedidoRascunho(BaseModel):
    destinatario: EmailStr | None = None


@router.post("/{vaga_id}/rascunho")
def criar_rascunho(vaga_id: int, pedido: PedidoRascunho | None = None, s: Servicos = Depends(servicos)) -> Rascunho:
    """Gera um rascunho sob demanda, mesmo abaixo da nota mínima.
    O destinatário padrão é o email publicado na vaga."""
    v = _vaga_ou_404(s, vaga_id)
    if aberto := s.banco.rascunho_aberto_da_vaga(v.id):
        raise HTTPException(409, f"Esta vaga já tem um rascunho ({aberto.status}).")
    if pedido and pedido.destinatario:
        v.emails = [pedido.destinatario.lower()] + [e for e in v.emails if e != pedido.destinatario.lower()]
    if not v.emails:
        raise HTTPException(422, "A vaga não publica email de contato. Informe um destinatário.")
    if not (perfil := carregar_perfil()):
        raise HTTPException(409, "Envie o currículo e gere o perfil primeiro.")
    try:
        r = gerar_rascunho(s.banco, v, perfil, carregar_config(), s.llm)
    except LimiteDeUso as e:
        raise HTTPException(429, f"Cota do Claude esgotada: {e}") from e
    if r is None:
        checagem = historico.verificar(s.banco, v, v.emails[0], carregar_config())
        raise HTTPException(409, " ".join(a.mensagem for a in checagem.avisos) or "Bloqueado pelo histórico.")
    return r
