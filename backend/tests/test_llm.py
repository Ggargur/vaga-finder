import json

import pytest

from vaga_finder.llm import ClaudeCLI, ErroLLM, LimiteDeUso, extrair_json, interpretar_saida


def test_structured_output_tem_prioridade():
    saida = json.dumps({"is_error": False, "result": "ignorado", "structured_output": {"nota": 80}})
    assert interpretar_saida(saida) == {"nota": 80}


def test_json_em_bloco_markdown():
    assert extrair_json('Aqui:\n```json\n{"a": 1}\n```') == {"a": 1}
    assert extrair_json('texto {"a": 2} fim') == {"a": 2}


def test_erro_e_limite():
    with pytest.raises(LimiteDeUso):
        interpretar_saida(json.dumps({"is_error": True, "result": "Claude usage limit reached. Resets 5pm"}))
    with pytest.raises(ErroLLM):
        interpretar_saida(json.dumps({"is_error": True, "result": "outra coisa"}))
    with pytest.raises(ErroLLM):
        interpretar_saida("não é json")


def test_comando_desliga_ferramentas_e_mcp():
    cmd = ClaudeCLI().comando({"type": "object"}, "sistema", "haiku")
    assert cmd[:2] == ["claude", "-p"]
    assert "--strict-mcp-config" in cmd and cmd[cmd.index("--tools") + 1] == ""
    assert cmd[cmd.index("--model") + 1] == "haiku"
    assert cmd[cmd.index("--system-prompt") + 1] == "sistema"
