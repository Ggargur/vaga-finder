from fastapi import APIRouter

from ...config import Config, carregar_config, salvar_config

router = APIRouter(prefix="/config", tags=["config"])


@router.get("")
def obter() -> Config:
    return carregar_config()


@router.put("")
def atualizar(cfg: Config) -> Config:
    salvar_config(cfg)
    return cfg
