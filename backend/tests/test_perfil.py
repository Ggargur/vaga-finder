import json

from vaga_finder import perfil as mod_perfil
from vaga_finder.config import ambiente

from .conftest import LLMFalso


def test_gerar_perfil_salva_json(monkeypatch, tmp_path):
    monkeypatch.setattr(mod_perfil, "texto_do_pdf", lambda _: "Fulano, dev Python há 5 anos. " * 10)
    llm = LLMFalso({"nome": "Fulano", "skills": ["python", "django"], "senioridade": "pleno", "anos_experiencia": 5})
    p = mod_perfil.gerar_perfil(tmp_path / "cv.pdf", llm=llm)
    assert p.nome == "Fulano" and p.skills == ["python", "django"]
    assert "Fulano, dev Python" in llm.chamadas[0]["prompt"]
    salvo = json.loads(ambiente().perfil_path.read_text())
    assert salvo["senioridade"] == "pleno"
    assert mod_perfil.carregar_perfil() == p


def test_perfil_para_prompt_omite_contato():
    p = mod_perfil.Perfil(nome="A", email="a@b.com", telefone="123", skills=["x"])
    texto = mod_perfil.perfil_para_prompt(p)
    assert "a@b.com" not in texto and "123" not in texto and '"skills":["x"]' in texto


def test_resposta_embrulhada_em_texto_e_desembrulhada(monkeypatch, tmp_path):
    monkeypatch.setattr(mod_perfil, "texto_do_pdf", lambda _: "cv " * 50)
    interno = json.dumps({"nome": "Gabriel", "skills": ["C#", "Unity"], "experiencias": [{"cargo": "Dev"}]})
    p = mod_perfil.gerar_perfil(tmp_path / "cv.pdf", llm=LLMFalso({"perfil": interno}))
    assert p.nome == "Gabriel" and p.skills == ["C#", "Unity"] and p.experiencias[0].cargo == "Dev"


def test_perfil_vazio_da_erro_e_nao_sobrescreve(monkeypatch, tmp_path):
    import pytest

    monkeypatch.setattr(mod_perfil, "texto_do_pdf", lambda _: "cv " * 50)
    with pytest.raises(ValueError, match="vazio"):
        mod_perfil.gerar_perfil(tmp_path / "cv.pdf", llm=LLMFalso({"outra_coisa": 1, "mais": 2}))
    assert not ambiente().perfil_path.exists()


def test_schema_enviado_ao_claude_nao_tem_ref():
    from vaga_finder.llm import expandir_schema

    schema = expandir_schema(mod_perfil.Perfil.model_json_schema())
    texto = json.dumps(schema)
    assert "$ref" not in texto and "$defs" not in texto
    assert schema["properties"]["experiencias"]["items"]["properties"]["cargo"]["type"] == "string"
