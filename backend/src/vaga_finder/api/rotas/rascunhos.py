from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr

from ... import historico, slop_lint
from ...config import carregar_config
from ...llm import LimiteDeUso
from ...models import Rascunho
from ...perfil import carregar_perfil
from ...redator import regerar
from ..deps import Servicos, servicos

router = APIRouter(prefix="/rascunhos", tags=["rascunhos"])


def _completo(s: Servicos, r: Rascunho) -> dict:
    v = s.banco.obter_vaga(r.vaga_id)
    a = s.banco.obter_avaliacao(r.vaga_id)
    return {
        **r.model_dump(),
        "palavras": slop_lint.contar_palavras(r.corpo),
        "vaga": {
            "id": v.id, "titulo": v.titulo, "empresa": v.empresa, "url": v.url, "fonte": v.fonte,
            "local": v.local, "remoto": v.remoto, "descricao": v.descricao, "emails": v.emails,
        },
        "avaliacao": a.model_dump() if a else None,
    }


def _rascunho_ou_404(s: Servicos, rascunho_id: int) -> Rascunho:
    if not (r := s.banco.obter_rascunho(rascunho_id)):
        raise HTTPException(404, "Rascunho não encontrado.")
    return r


@router.get("")
def listar(status: str | None = None, s: Servicos = Depends(servicos)) -> list[dict]:
    return [_completo(s, r) for r in s.banco.listar_rascunhos(status)]


@router.get("/{rascunho_id}")
def obter(rascunho_id: int, s: Servicos = Depends(servicos)) -> dict:
    return _completo(s, _rascunho_ou_404(s, rascunho_id))


class Edicao(BaseModel):
    assunto: str
    corpo: str
    destinatario: EmailStr


@router.put("/{rascunho_id}")
def editar(rascunho_id: int, edicao: Edicao, s: Servicos = Depends(servicos)) -> dict:
    r = _rascunho_ou_404(s, rascunho_id)
    if r.status in ("enviado", "aprovado"):
        raise HTTPException(409, f"Rascunho {r.status} não pode ser editado.")
    cfg = carregar_config()
    vaga = s.banco.obter_vaga(r.vaga_id)
    destinatario = str(edicao.destinatario).lower()
    avisos = historico.verificar(s.banco, vaga, destinatario, cfg).avisos + slop_lint.verificar(
        edicao.corpo + "\n" + edicao.assunto, cfg.redacao.palavras_min, cfg.redacao.palavras_max
    )
    s.banco.atualizar_rascunho(
        rascunho_id, assunto=edicao.assunto.strip(), corpo=edicao.corpo.strip(),
        destinatario=destinatario, avisos=avisos,
    )
    return _completo(s, s.banco.obter_rascunho(rascunho_id))


class PedidoRegerar(BaseModel):
    instrucao: str | None = None


@router.post("/{rascunho_id}/regerar")
def gerar_de_novo(rascunho_id: int, pedido: PedidoRegerar, s: Servicos = Depends(servicos)) -> dict:
    r = _rascunho_ou_404(s, rascunho_id)
    if r.status in ("enviado", "aprovado"):
        raise HTTPException(409, f"Rascunho {r.status} não pode ser alterado.")
    if not (perfil := carregar_perfil()):
        raise HTTPException(409, "Perfil não encontrado.")
    try:
        novo = regerar(s.banco, rascunho_id, perfil, carregar_config(), s.llm, pedido.instrucao)
    except LimiteDeUso as e:
        raise HTTPException(429, f"Cota do Claude esgotada: {e}") from e
    return _completo(s, novo)


@router.post("/{rascunho_id}/aprovar")
def aprovar(rascunho_id: int, s: Servicos = Depends(servicos)) -> dict:
    """Coloca na fila de envio. A fila respeita a pausa entre envios e o limite diário."""
    r = _rascunho_ou_404(s, rascunho_id)
    if r.status not in ("pendente", "erro"):
        raise HTTPException(409, f"Rascunho {r.status} não pode ser aprovado.")
    vaga = s.banco.obter_vaga(r.vaga_id)
    checagem = historico.verificar(s.banco, vaga, r.destinatario, carregar_config())
    if checagem.bloqueado:
        raise HTTPException(409, " ".join(a.mensagem for a in checagem.avisos if a.tipo == "historico"))
    s.banco.atualizar_rascunho(rascunho_id, status="aprovado", erro=None)
    s.fila.acordar()
    return _completo(s, s.banco.obter_rascunho(rascunho_id))


@router.post("/{rascunho_id}/cancelar")
def cancelar(rascunho_id: int, s: Servicos = Depends(servicos)) -> dict:
    """Tira da fila um rascunho aprovado que ainda não saiu."""
    r = _rascunho_ou_404(s, rascunho_id)
    if r.status != "aprovado":
        raise HTTPException(409, "Só rascunhos aprovados (na fila) podem ser cancelados.")
    s.banco.atualizar_rascunho(rascunho_id, status="pendente")
    return _completo(s, s.banco.obter_rascunho(rascunho_id))


@router.post("/{rascunho_id}/rejeitar")
def rejeitar(rascunho_id: int, s: Servicos = Depends(servicos)) -> dict:
    r = _rascunho_ou_404(s, rascunho_id)
    if r.status == "enviado":
        raise HTTPException(409, "Rascunho já enviado.")
    s.banco.atualizar_rascunho(rascunho_id, status="rejeitado")
    return _completo(s, s.banco.obter_rascunho(rascunho_id))
