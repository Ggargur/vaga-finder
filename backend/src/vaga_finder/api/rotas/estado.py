from fastapi import APIRouter, Depends

from ...config import carregar_config
from ...envio import inicio_do_dia_utc
from ..deps import Servicos, servicos

router = APIRouter(tags=["estado"])


@router.get("/estado")
def estado(s: Servicos = Depends(servicos)) -> dict:
    cfg = carregar_config()
    rodando = s.banco.tarefa_rodando()
    return {
        **s.banco.estatisticas(inicio_do_dia_utc()),
        "limite_diario": cfg.envio.limite_diario,
        "nota_minima": cfg.avaliacao.nota_minima,
        "tem_perfil": s.amb.perfil_path.exists(),
        "tem_curriculo": s.amb.curriculo_path.exists(),
        "gmail_configurado": bool(s.amb.gmail_user and s.amb.gmail_app_password),
        "gmail_user": s.amb.gmail_user,
        "tarefa_rodando": rodando.model_dump() if rodando else None,
        "fila": {
            "aprovados": len(s.banco.listar_rascunhos("aprovado")),
            "proximo_envio_em_s": s.fila.segundos_para_proximo(),
        },
    }
