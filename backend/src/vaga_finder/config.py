"""Configuração: segredos vêm do .env, preferências do config.yaml (editável pela UI)."""

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Ambiente(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    gmail_user: str = ""
    gmail_app_password: str = ""
    remetente_nome: str = ""
    data_dir: Path = BACKEND_DIR / "data"
    config_path: Path = BACKEND_DIR / "config.yaml"
    claude_bin: str = "claude"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "vagas.db"

    @property
    def curriculo_path(self) -> Path:
        return self.data_dir / "curriculo.pdf"

    @property
    def perfil_path(self) -> Path:
        return self.data_dir / "perfil.json"


class ConfigBusca(BaseModel):
    termos: list[str] = Field(default_factory=lambda: ["python", "desenvolvedor backend"])
    # vagas cujo título contém algum destes termos são descartadas sem gastar LLM
    exclusoes: list[str] = Field(default_factory=lambda: ["estágio", "estagiário", "intern"])
    # se vazio, o pré-filtro usa as skills do perfil
    palavras_chave: list[str] = Field(default_factory=list)
    limite_por_fonte: int = 50


class ConfigFontes(BaseModel):
    gupy: bool = True
    remotive: bool = True
    remoteok: bool = True
    himalayas: bool = True
    greenhouse: list[str] = Field(default_factory=list)  # slugs, ex.: "gitlab"
    lever: list[str] = Field(default_factory=list)  # slugs, ex.: "spotify"
    ashby: list[str] = Field(default_factory=list)  # slugs, ex.: "nubank"
    paginas: list[str] = Field(default_factory=list)  # URLs de páginas de carreira
    linkedin: bool = False
    linkedin_local: str = "Brasil"


class ConfigAvaliacao(BaseModel):
    nota_minima: int = 70
    modelo: str = "haiku"
    lote: int = 5


class ConfigRedacao(BaseModel):
    modelo: str = "sonnet"
    palavras_min: int = 120
    palavras_max: int = 180
    assinatura: str = ""  # opcional; se vazio, usa nome + links do perfil


class ConfigEnvio(BaseModel):
    limite_diario: int = 20
    dias_entre_contatos: int = 60
    pausa_min_s: int = 30
    pausa_max_s: int = 90
    anexar_curriculo: bool = True


class Config(BaseModel):
    busca: ConfigBusca = Field(default_factory=ConfigBusca)
    fontes: ConfigFontes = Field(default_factory=ConfigFontes)
    avaliacao: ConfigAvaliacao = Field(default_factory=ConfigAvaliacao)
    redacao: ConfigRedacao = Field(default_factory=ConfigRedacao)
    envio: ConfigEnvio = Field(default_factory=ConfigEnvio)


@lru_cache
def ambiente() -> Ambiente:
    amb = Ambiente()
    amb.data_dir.mkdir(parents=True, exist_ok=True)
    return amb


def carregar_config(caminho: Path | None = None) -> Config:
    caminho = caminho or ambiente().config_path
    if not caminho.exists():
        cfg = Config()
        salvar_config(cfg, caminho)
        return cfg
    dados = yaml.safe_load(caminho.read_text(encoding="utf-8")) or {}
    return Config.model_validate(dados)


def salvar_config(cfg: Config, caminho: Path | None = None) -> None:
    caminho = caminho or ambiente().config_path
    caminho.write_text(
        yaml.safe_dump(cfg.model_dump(), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
