from fastapi import APIRouter

from ...config import Config, carregar_config, salvar_config
from ...fontes.games import ESTUDIOS, QUADROS

router = APIRouter(prefix="/config", tags=["config"])


@router.get("")
def obter() -> Config:
    return carregar_config()


@router.put("")
def atualizar(cfg: Config) -> Config:
    salvar_config(cfg)
    return cfg


@router.get("/opcoes")
def opcoes() -> dict:
    """Sites de games disponíveis e a lista pronta de estúdios (Greenhouse/Lever/Ashby)."""
    return {
        "sites_games": [
            {"chave": q.chave, "nome": q.nome, "descricao": q.descricao, "site": q.url.split("/", 3)[2]}
            for q in QUADROS.values()
        ],
        "estudios_games": ESTUDIOS,
    }
