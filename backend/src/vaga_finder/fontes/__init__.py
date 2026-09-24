from ..config import Config
from .ashby import Ashby
from .base import Fonte
from .games import QUADROS, SiteGames
from .greenhouse import Greenhouse
from .gupy import Gupy
from .himalayas import Himalayas
from .lever import Lever
from .linkedin import LinkedIn
from .pagina_generica import PaginaGenerica
from .remoteok import RemoteOK
from .remotive import Remotive


def fontes_ativas(cfg: Config) -> list[Fonte]:
    f = cfg.fontes
    ativas: list[Fonte] = []
    if f.gupy:
        ativas.append(Gupy())
    if f.remotive:
        ativas.append(Remotive())
    if f.remoteok:
        ativas.append(RemoteOK())
    if f.himalayas:
        ativas.append(Himalayas())
    if f.greenhouse:
        ativas.append(Greenhouse(f.greenhouse))
    if f.lever:
        ativas.append(Lever(f.lever))
    if f.ashby:
        ativas.append(Ashby(f.ashby))
    if f.paginas:
        ativas.append(PaginaGenerica(f.paginas))
    ativas += [SiteGames(chave) for chave in f.games if chave in QUADROS]
    if f.linkedin:
        ativas.append(LinkedIn(f.linkedin_local))
    return ativas
