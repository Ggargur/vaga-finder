from ..config import Config
from .base import Fonte
from .gupy import Gupy
from .remotive import Remotive


def fontes_ativas(cfg: Config) -> list[Fonte]:
    f = cfg.fontes
    ativas: list[Fonte] = []
    if f.gupy:
        ativas.append(Gupy())
    if f.remotive:
        ativas.append(Remotive())
    return ativas
