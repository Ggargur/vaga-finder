import json
from pathlib import Path

import pytest

from vaga_finder import config
from vaga_finder.db import Banco

FIXTURES = Path(__file__).parent / "fixtures"


def carregar_fixture(nome: str):
    return json.loads((FIXTURES / nome).read_text(encoding="utf-8"))


class LLMFalso:
    """Devolve respostas prontas (ou calculadas por função) e guarda as chamadas."""

    def __init__(self, *respostas):
        self.respostas = list(respostas)
        self.chamadas: list[dict] = []

    def json(self, prompt, schema, *, sistema=None, modelo=None):
        self.chamadas.append({"prompt": prompt, "schema": schema, "sistema": sistema, "modelo": modelo})
        resposta = self.respostas.pop(0) if len(self.respostas) > 1 else self.respostas[0]
        return resposta(prompt) if callable(resposta) else resposta


@pytest.fixture(autouse=True)
def ambiente_isolado(tmp_path, monkeypatch):
    """Cada teste usa uma pasta de dados e um config.yaml próprios."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("CONFIG_PATH", str(tmp_path / "config.yaml"))
    monkeypatch.setenv("GMAIL_USER", "eu@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "senha")
    monkeypatch.setenv("REMETENTE_NOME", "Fulano Teste")
    config.ambiente.cache_clear()
    yield
    config.ambiente.cache_clear()


@pytest.fixture
def banco(tmp_path) -> Banco:
    return Banco(tmp_path / "teste.db")
