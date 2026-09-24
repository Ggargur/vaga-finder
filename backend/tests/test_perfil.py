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
