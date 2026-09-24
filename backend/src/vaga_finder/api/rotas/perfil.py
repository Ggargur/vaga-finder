from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ...perfil import Perfil, carregar_perfil, gerar_perfil, salvar_perfil
from ..deps import Servicos, servicos

router = APIRouter(prefix="/perfil", tags=["perfil"])

TAMANHO_MAXIMO = 10 * 1024 * 1024


@router.get("")
def obter() -> Perfil | None:
    return carregar_perfil()


@router.put("")
def atualizar(perfil: Perfil) -> Perfil:
    salvar_perfil(perfil)
    return perfil


@router.post("/curriculo")
def enviar_curriculo(arquivo: UploadFile, s: Servicos = Depends(servicos)) -> Perfil:
    """Salva o PDF e gera o perfil com o Claude (leva ~30s)."""
    conteudo = arquivo.file.read(TAMANHO_MAXIMO + 1)
    if len(conteudo) > TAMANHO_MAXIMO:
        raise HTTPException(413, "PDF maior que 10 MB.")
    if not conteudo.startswith(b"%PDF"):
        raise HTTPException(422, "O arquivo não é um PDF.")
    s.amb.curriculo_path.write_bytes(conteudo)
    try:
        return gerar_perfil(s.amb.curriculo_path, llm=s.llm)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e


@router.post("/regerar")
def regerar(s: Servicos = Depends(servicos)) -> Perfil:
    if not s.amb.curriculo_path.exists():
        raise HTTPException(404, "Nenhum currículo enviado.")
    try:
        return gerar_perfil(s.amb.curriculo_path, llm=s.llm)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e


@router.get("/curriculo")
def baixar_curriculo(s: Servicos = Depends(servicos)):
    if not s.amb.curriculo_path.exists():
        raise HTTPException(404, "Nenhum currículo enviado.")
    return FileResponse(s.amb.curriculo_path, media_type="application/pdf", filename="curriculo.pdf")
