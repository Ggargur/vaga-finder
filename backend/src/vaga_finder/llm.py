"""Acesso ao LLM. Hoje via `claude -p` (Claude Code headless, cota da assinatura Pro).

Para trocar pela API da Anthropic, implemente outra classe com o mesmo método `json`
e devolva-a em `obter_llm()`.
"""

import json
import re
import subprocess
import tempfile
import threading
import time
from functools import lru_cache
from typing import Protocol

from .config import ambiente


class ErroLLM(RuntimeError):
    pass


class LimiteDeUso(ErroLLM):
    """A cota da assinatura acabou; não adianta tentar de novo agora."""


class LLM(Protocol):
    def json(self, prompt: str, schema: dict, *, sistema: str | None = None, modelo: str | None = None) -> dict: ...


_PADROES_LIMITE = re.compile(r"usage limit|rate limit|limit reached|quota|too many requests|429", re.I)

# `claude -p` concorrente disputa a mesma cota; uma chamada por vez é suficiente
_trava = threading.Lock()


def expandir_schema(schema: dict) -> dict:
    """Troca os `$ref` por cópias das definições em `$defs`. Com `$ref`, o `claude -p` ignorou o
    schema e devolveu {"perfil": "<json em texto>"}; schema expandido ele respeita."""
    defs = schema.get("$defs", {})

    def resolver(no):
        if isinstance(no, dict):
            if "$ref" in no:
                return resolver(defs[no["$ref"].rsplit("/", 1)[-1]])
            return {k: resolver(v) for k, v in no.items() if k != "$defs"}
        if isinstance(no, list):
            return [resolver(x) for x in no]
        return no

    return resolver(schema)


def extrair_json(texto: str) -> dict:
    """Aceita JSON puro ou dentro de ```json ... ```."""
    texto = texto.strip()
    bloco = re.search(r"```(?:json)?\s*(\{.*\})\s*```", texto, re.S)
    if bloco:
        texto = bloco.group(1)
    else:
        inicio, fim = texto.find("{"), texto.rfind("}")
        if inicio != -1 and fim > inicio:
            texto = texto[inicio : fim + 1]
    try:
        return json.loads(texto)
    except json.JSONDecodeError as e:
        raise ErroLLM(f"resposta não é JSON: {texto[:200]}") from e


def interpretar_saida(stdout: str) -> dict:
    """Lê o envelope de `claude -p --output-format json`."""
    try:
        envelope = json.loads(stdout)
    except json.JSONDecodeError as e:
        if _PADROES_LIMITE.search(stdout):
            raise LimiteDeUso(stdout.strip()[:300]) from e
        raise ErroLLM(f"saída inesperada do claude: {stdout[:300]}") from e
    if envelope.get("is_error"):
        msg = str(envelope.get("result") or envelope.get("subtype") or "erro desconhecido")
        if _PADROES_LIMITE.search(msg) or envelope.get("api_error_status") == 429:
            raise LimiteDeUso(msg)
        raise ErroLLM(msg)
    if isinstance(envelope.get("structured_output"), dict):
        return envelope["structured_output"]
    return extrair_json(str(envelope.get("result", "")))


class ClaudeCLI:
    def __init__(self, binario: str = "claude", modelo_padrao: str = "sonnet", timeout: int = 300, tentativas: int = 3):
        self.binario = binario
        self.modelo_padrao = modelo_padrao
        self.timeout = timeout
        self.tentativas = tentativas

    def comando(self, schema: dict, sistema: str | None, modelo: str) -> list[str]:
        cmd = [
            self.binario, "-p",
            "--output-format", "json",
            "--model", modelo,
            "--json-schema", json.dumps(expandir_schema(schema), ensure_ascii=False),
            "--tools", "",
            # sem MCP, CLAUDE.md ou settings: corta ~25k tokens de contexto por chamada
            "--strict-mcp-config",
            "--setting-sources", "",
            "--no-session-persistence",
        ]
        if sistema:
            cmd += ["--system-prompt", sistema]
        return cmd

    def json(self, prompt: str, schema: dict, *, sistema: str | None = None, modelo: str | None = None) -> dict:
        cmd = self.comando(schema, sistema, modelo or self.modelo_padrao)
        ultimo_erro: Exception | None = None
        for tentativa in range(self.tentativas):
            try:
                with _trava, tempfile.TemporaryDirectory() as pasta_vazia:
                    proc = subprocess.run(
                        cmd, input=prompt, capture_output=True, text=True, timeout=self.timeout, cwd=pasta_vazia
                    )
                if proc.returncode != 0 and not proc.stdout.strip():
                    erro = (proc.stderr or "").strip()
                    if _PADROES_LIMITE.search(erro):
                        raise LimiteDeUso(erro[:300])
                    raise ErroLLM(f"claude saiu com código {proc.returncode}: {erro[:300]}")
                return interpretar_saida(proc.stdout)
            except LimiteDeUso:
                raise
            except FileNotFoundError as e:
                raise ErroLLM(f"'{self.binario}' não encontrado. Instale e faça login no Claude Code.") from e
            except (ErroLLM, subprocess.TimeoutExpired) as e:
                ultimo_erro = e
                time.sleep(2 * (tentativa + 1))
        raise ErroLLM(f"falhou após {self.tentativas} tentativas: {ultimo_erro}")


@lru_cache
def obter_llm() -> LLM:
    return ClaudeCLI(binario=ambiente().claude_bin)
