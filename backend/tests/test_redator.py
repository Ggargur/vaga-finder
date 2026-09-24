from vaga_finder.config import Config
from vaga_finder.models import Avaliacao, Envio, Vaga
from vaga_finder.perfil import Perfil
from vaga_finder.redator import detectar_idioma, gerar_rascunho, gerar_rascunhos_pendentes, regerar

from .conftest import LLMFalso

RASCUNHO = {"assunto": "Dev Python — Fulano", "corpo": "Sou apaixonado por Python — de verdade.", "idioma": "pt"}
REVISADO = {"assunto": "Dev Python | Fulano", "corpo": "Olá, equipe da Acme.\n\n\n\nVi a vaga de Dev Python no Gupy.", "idioma": "pt"}


def _vaga_avaliada(banco, nota=85, emails=("rh@acme.com",)):
    banco.inserir_vagas([Vaga(fonte="gupy", id_fonte="1", titulo="Dev Python", empresa="Acme",
                              url="https://x/1", descricao="Vaga para desenvolvedor com experiência em Python",
                              emails=list(emails))])
    v = banco.vagas_por_status("nova")[0]
    banco.salvar_avaliacao(v.id, Avaliacao(nota=nota, motivo="bom", pontos_fortes=["python"]))
    return banco.obter_vaga(v.id)


def test_detectar_idioma():
    assert detectar_idioma("Buscamos pessoa desenvolvedora com experiência em Python para atuar") == "pt"
    assert detectar_idioma("We are looking for an engineer with experience in Python to join our team") == "en"


def test_gera_rascunho_em_dois_passos_com_stop_slop(banco):
    v = _vaga_avaliada(banco)
    llm = LLMFalso(RASCUNHO, REVISADO)
    r = gerar_rascunho(banco, v, Perfil(nome="Fulano", skills=["python"]), Config(), llm)
    assert r.destinatario == "rh@acme.com" and r.assunto == "Dev Python | Fulano"
    assert r.corpo == "Olá, equipe da Acme.\n\nVi a vaga de Dev Python no Gupy."
    # 1ª chamada redige; 2ª revisa com as regras do stop-slop e recebe os problemas do linter
    assert "Stop Slop" in llm.chamadas[1]["sistema"] and "pt-br" not in llm.chamadas[0]["sistema"]
    assert "Travessão" in llm.chamadas[1]["prompt"] and "sou apaixonado por" in llm.chamadas[1]["prompt"]
    assert llm.chamadas[0]["modelo"] == "sonnet"
    assert banco.obter_rascunho(r.id).status == "pendente"


def test_nao_gera_quando_historico_bloqueia(banco):
    v = _vaga_avaliada(banco)
    banco.registrar_envio(Envio(destinatario="rh@acme.com", message_id="<a>"))
    llm = LLMFalso(RASCUNHO)
    assert gerar_rascunho(banco, v, Perfil(), Config(), llm) is None
    assert llm.chamadas == []


def test_pendentes_respeita_nota_minima_e_rascunho_existente(banco):
    _vaga_avaliada(banco, nota=50)
    llm = LLMFalso(RASCUNHO, REVISADO)
    assert gerar_rascunhos_pendentes(banco, Config(), Perfil(), llm)["rascunhos"] == 0

    banco.salvar_avaliacao(1, Avaliacao(nota=90, motivo="ok"))
    assert gerar_rascunhos_pendentes(banco, Config(), Perfil(), llm)["rascunhos"] == 1
    assert gerar_rascunhos_pendentes(banco, Config(), Perfil(), llm)["rascunhos"] == 0


def test_regerar_passa_instrucao(banco):
    v = _vaga_avaliada(banco)
    llm = LLMFalso(RASCUNHO, REVISADO)
    r = gerar_rascunho(banco, v, Perfil(), Config(), llm)
    regerar(banco, r.id, Perfil(), Config(), llm, instrucao="mais curto")
    assert "mais curto" in llm.chamadas[2]["prompt"]
