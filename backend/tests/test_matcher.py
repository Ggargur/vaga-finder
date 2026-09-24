from vaga_finder.config import Config
from vaga_finder.matcher import avaliar_pendentes, palavras_chave, prefiltro
from vaga_finder.models import Vaga
from vaga_finder.perfil import Perfil

from .conftest import LLMFalso


def vaga(i, titulo="Desenvolvedor Python", descricao="Django e APIs REST"):
    return Vaga(fonte="t", id_fonte=str(i), titulo=titulo, empresa=f"E{i}", url=f"https://x/{i}", descricao=descricao)


def test_palavras_chave_ignora_termos_de_uma_letra():
    perfil = Perfil(skills=["Python", "C", "Node.js"])
    cfg = Config()
    cfg.busca.termos = []
    assert palavras_chave(perfil, cfg) == ["node js", "python"]


def test_prefiltro():
    chaves = ["python", "django"]
    assert prefiltro(vaga(1), chaves, ["estágio"]) is None
    assert "estágio" in prefiltro(vaga(2, titulo="Estágio em Python"), chaves, ["estágio"])
    assert prefiltro(vaga(3, titulo="Contador", descricao="planilhas"), chaves, []) == "nenhuma palavra-chave do perfil"


def test_avaliar_pendentes_filtra_e_avalia_em_lote(banco):
    banco.inserir_vagas([vaga(1), vaga(2, titulo="Dev Python Sênior"), vaga(3, titulo="Contador", descricao="planilhas")])
    ids = [v.id for v in banco.vagas_por_status("nova") if v.titulo != "Contador"]
    llm = LLMFalso({"avaliacoes": [
        {"id": ids[0], "nota": 150, "motivo": "ótimo", "pontos_fortes": ["python"], "lacunas": []},
        {"id": 999, "nota": 10, "motivo": "id inventado", "pontos_fortes": [], "lacunas": []},
    ]})
    cfg = Config()
    resumo = avaliar_pendentes(banco, cfg, Perfil(skills=["python"]), llm)
    assert resumo == {"filtradas": 1, "avaliadas": 1, "falhas": 1, "interrompido": None}
    assert len(llm.chamadas) == 1 and llm.chamadas[0]["modelo"] == "haiku"
    assert banco.obter_avaliacao(ids[0]).nota == 100
    # a vaga sem resposta continua 'nova' para a próxima rodada
    assert [v.id for v in banco.vagas_por_status("nova")] == [ids[1]]


def test_avaliar_para_quando_cota_acaba(banco):
    from vaga_finder.llm import LimiteDeUso

    def estoura(_):
        raise LimiteDeUso("usage limit")

    banco.inserir_vagas([vaga(1)])
    resumo = avaliar_pendentes(banco, Config(), Perfil(skills=["python"]), LLMFalso(estoura))
    assert resumo["interrompido"].startswith("cota do Claude esgotada")
