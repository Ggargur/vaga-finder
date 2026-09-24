from typing import Literal

from fastapi import APIRouter, Depends, HTTPException

from ...coleta import coletar
from ...config import carregar_config
from ...historico import sincronizar_gmail
from ...models import Tarefa
from ...pipeline import PerfilAusente, avaliar_e_redigir, rodar
from ...tarefas import TarefaEmAndamento
from ..deps import Servicos, servicos

router = APIRouter(prefix="/tarefas", tags=["tarefas"])

TipoTarefa = Literal["buscar", "avaliar", "rodar", "sincronizar"]


@router.post("/{tipo}", status_code=202)
def iniciar(tipo: TipoTarefa, s: Servicos = Depends(servicos)) -> Tarefa:
    cfg = carregar_config()
    if tipo in ("avaliar", "rodar") and not s.amb.perfil_path.exists():
        raise HTTPException(409, str(PerfilAusente("Envie o currículo e gere o perfil antes de avaliar vagas.")))
    funcoes = {
        "buscar": lambda p: coletar(s.banco, cfg, progresso=p),
        "avaliar": lambda p: avaliar_e_redigir(s.banco, cfg, s.llm, p),
        "rodar": lambda p: rodar(s.banco, cfg, s.llm, p),
        "sincronizar": lambda p: sincronizar_gmail(s.banco, s.amb, progresso=p),
    }
    try:
        return s.tarefas.iniciar(tipo, funcoes[tipo])
    except TarefaEmAndamento as e:
        raise HTTPException(409, str(e)) from e


@router.get("")
def listar(s: Servicos = Depends(servicos)) -> list[Tarefa]:
    return s.banco.listar_tarefas()


@router.get("/{tarefa_id}")
def obter(tarefa_id: int, s: Servicos = Depends(servicos)) -> Tarefa:
    if not (t := s.banco.obter_tarefa(tarefa_id)):
        raise HTTPException(404, "Tarefa não encontrada.")
    return t
