import re
from functools import lru_cache
from pathlib import Path
from string import Template

from .config import BACKEND_DIR

PASTA = BACKEND_DIR / "prompts"
PASTA_STOP_SLOP = PASTA / "stop_slop"


def renderizar(nome: str, **valores: object) -> str:
    texto = (PASTA / f"{nome}.md").read_text(encoding="utf-8")
    return Template(texto).substitute({k: str(v) for k, v in valores.items()})


def _sem_frontmatter(texto: str) -> str:
    return re.sub(r"\A---\n.*?\n---\n", "", texto, flags=re.S)


@lru_cache
def sistema_stop_slop() -> str:
    """Regras do stop-slop (e a lista PT-BR) como system prompt da revisão."""
    partes = [
        "Você é um editor de texto. Siga estas regras de escrita ao revisar.",
        _sem_frontmatter((PASTA_STOP_SLOP / "SKILL.md").read_text(encoding="utf-8")),
    ]
    for nome in ("phrases.md", "structures.md", "examples.md", "pt-br.md"):
        partes.append((PASTA_STOP_SLOP / nome).read_text(encoding="utf-8"))
    partes.append(
        "Exceção para emails de candidatura: primeira pessoa e voz ativa ('desenvolvi', 'liderei'). "
        "Uma saudação curta ('Olá, equipe da X,' / 'Hi X team,') e uma despedida curta são permitidas."
    )
    return "\n\n".join(partes)


def frases_proibidas(arquivo: Path) -> list[str]:
    """Extrai as frases entre aspas das listas `- "..."` de um arquivo de regras."""
    frases = []
    for linha in arquivo.read_text(encoding="utf-8").splitlines():
        for m in re.finditer(r'"([^"]+)"', linha) if linha.lstrip().startswith("- ") else ():
            frase = m.group(1).split("[")[0].strip().rstrip(".:,")
            if len(frase) >= 3:
                frases.append(frase)
    return frases
