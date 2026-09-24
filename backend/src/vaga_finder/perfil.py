"""Currículo em PDF → perfil estruturado (perfil.json), editável pela UI."""

import json
from pathlib import Path

from pydantic import BaseModel, Field
from pypdf import PdfReader

from . import prompts
from .config import ambiente
from .llm import LLM, extrair_json, obter_llm


class Idioma(BaseModel):
    idioma: str
    nivel: str = ""


class Experiencia(BaseModel):
    cargo: str
    empresa: str = ""
    periodo: str = ""
    destaques: list[str] = Field(default_factory=list)


class Preferencias(BaseModel):
    remoto: bool = True
    locais: list[str] = Field(default_factory=list)


class Perfil(BaseModel):
    nome: str = ""
    email: str = ""
    telefone: str = ""
    localizacao: str = ""
    links: list[str] = Field(default_factory=list)
    resumo: str = ""
    senioridade: str = ""
    anos_experiencia: int = 0
    cargos_alvo: list[str] = Field(default_factory=list)
    palavras_chave: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    idiomas: list[Idioma] = Field(default_factory=list)
    experiencias: list[Experiencia] = Field(default_factory=list)
    formacao: list[str] = Field(default_factory=list)
    preferencias: Preferencias = Field(default_factory=Preferencias)


def texto_do_pdf(caminho: Path) -> str:
    leitor = PdfReader(caminho)
    texto = "\n".join(pagina.extract_text() or "" for pagina in leitor.pages).strip()
    if len(texto) < 100:
        raise ValueError("Não consegui extrair texto do PDF. Ele pode ser uma imagem escaneada.")
    return texto


def gerar_perfil(caminho_pdf: Path | None = None, llm: LLM | None = None) -> Perfil:
    amb = ambiente()
    caminho_pdf = caminho_pdf or amb.curriculo_path
    curriculo = texto_do_pdf(caminho_pdf)
    dados = (llm or obter_llm()).json(
        prompts.renderizar("perfil", curriculo=curriculo),
        Perfil.model_json_schema(),
        sistema="Você extrai dados de currículos com precisão e não inventa informação.",
    )
    perfil = Perfil.model_validate(_desembrulhar(dados))
    if not perfil.nome and not perfil.skills and not perfil.experiencias:
        raise ValueError("O Claude devolveu um perfil vazio. Tente gerar de novo.")
    salvar_perfil(perfil)
    return perfil


def _desembrulhar(dados: dict) -> dict:
    """Aceita respostas embrulhadas como {"perfil": {...}} ou {"perfil": "<json em texto>"}."""
    campos = set(Perfil.model_fields)
    if len(dados) == 1 and not campos.intersection(dados):
        interno = next(iter(dados.values()))
        if isinstance(interno, str):
            interno = extrair_json(interno)
        if isinstance(interno, dict):
            return interno
    return dados


def carregar_perfil() -> Perfil | None:
    caminho = ambiente().perfil_path
    if not caminho.exists():
        return None
    return Perfil.model_validate_json(caminho.read_text(encoding="utf-8"))


def salvar_perfil(perfil: Perfil) -> None:
    ambiente().perfil_path.write_text(
        json.dumps(perfil.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8"
    )


def perfil_para_prompt(perfil: Perfil) -> str:
    """Versão compacta para os prompts (menos tokens)."""
    d = perfil.model_dump(exclude={"telefone", "email"})
    return json.dumps(d, ensure_ascii=False, separators=(",", ":"))
