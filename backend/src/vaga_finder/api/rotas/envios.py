from fastapi import APIRouter, Depends, HTTPException

from ...config import carregar_config
from ...envio import ErroEnvio, enviar_teste
from ...models import Envio
from ..deps import Servicos, servicos

router = APIRouter(prefix="/envios", tags=["envios"])


@router.get("")
def listar(busca: str | None = None, origem: str | None = None, s: Servicos = Depends(servicos)) -> list[Envio]:
    return s.banco.listar_envios(busca=busca, origem=origem)


@router.post("/teste")
def teste(s: Servicos = Depends(servicos)) -> dict:
    try:
        destino = enviar_teste(s.banco, carregar_config(), s.amb, s.enviar)
    except ErroEnvio as e:
        raise HTTPException(400, str(e)) from e
    except OSError as e:
        raise HTTPException(502, f"Falha ao falar com o Gmail: {e}") from e
    return {"enviado_para": destino}
