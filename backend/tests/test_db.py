from vaga_finder.models import Avaliacao, Envio, Rascunho, Vaga


def vaga(**kw) -> Vaga:
    base = dict(fonte="remotive", id_fonte="1", titulo="Dev Python", empresa="Acme", url="https://x/1")
    return Vaga(**(base | kw))


def test_insere_e_ignora_repetida(banco):
    assert banco.inserir_vagas([vaga()]) == (1, 0)
    assert banco.inserir_vagas([vaga()]) == (0, 1)


def test_mesma_vaga_em_outra_fonte_soma_emails(banco):
    banco.inserir_vagas([vaga()])
    novas, repetidas = banco.inserir_vagas(
        [vaga(fonte="gupy", id_fonte="99", titulo="Dev Python (Remoto)", emails=["rh@acme.com"])]
    )
    assert (novas, repetidas) == (0, 1)
    [v] = banco.vagas_por_status("nova")
    assert v.fonte == "remotive" and v.emails == ["rh@acme.com"]


def test_avaliacao_muda_status_e_lista(banco):
    banco.inserir_vagas([vaga(), vaga(id_fonte="2", titulo="Dev Java")])
    v1 = banco.vagas_por_status("nova")[-1]
    banco.salvar_avaliacao(v1.id, Avaliacao(nota=85, motivo="ok", pontos_fortes=["python"]))
    lista = banco.listar_vagas(nota_min=80)
    assert [d["id"] for d in lista] == [v1.id]
    assert lista[0]["avaliacao"]["pontos_fortes"] == ["python"]
    assert banco.obter_vaga(v1.id).status == "avaliada"


def test_rascunho_e_envio(banco):
    banco.inserir_vagas([vaga()])
    v = banco.vagas_por_status("nova")[0]
    rid = banco.criar_rascunho(Rascunho(vaga_id=v.id, destinatario="rh@acme.com", assunto="a", corpo="b"))
    banco.atualizar_rascunho(rid, status="enviado")
    assert banco.obter_rascunho(rid).status == "enviado"
    assert banco.registrar_envio(Envio(vaga_id=v.id, impressao=v.impressao, destinatario="RH@acme.com", message_id="<m1>"))
    assert banco.registrar_envio(Envio(destinatario="rh@acme.com", message_id="<m1>", origem="gmail")) is None
    assert len(banco.envios_para("rh@acme.com")) == 1
    assert banco.listar_vagas()[0]["enviado_em"]


def test_tarefas(banco):
    t = banco.criar_tarefa("buscar")
    assert banco.tarefa_rodando().id == t.id
    banco.atualizar_tarefa(t.id, status="concluida", resultado={"novas": 3})
    t2 = banco.obter_tarefa(t.id)
    assert t2.status == "concluida" and t2.resultado == {"novas": 3} and t2.terminada_em
    assert banco.tarefa_rodando() is None
