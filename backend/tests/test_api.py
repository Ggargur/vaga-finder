import time

import pytest
from fastapi.testclient import TestClient

from vaga_finder.api.main import criar_app
from vaga_finder.config import ambiente
from vaga_finder.models import Avaliacao, Envio, Rascunho, Vaga
from vaga_finder.perfil import Perfil, salvar_perfil

from .conftest import LLMFalso
from .test_envio import EnviadorFalso

EMAIL = {"assunto": "Dev Python | Fulano", "corpo": "Olá, equipe da Acme. Vi a vaga no Gupy.", "idioma": "pt"}


@pytest.fixture
def ctx(banco, tmp_path):
    llm = LLMFalso(EMAIL)
    enviar = EnviadorFalso()
    app = criar_app(banco=banco, llm=llm, enviar=enviar, iniciar_fila=False, front_dist=tmp_path / "sem-front")
    with TestClient(app) as cliente:
        yield cliente, banco, llm, enviar, app


def _vaga(banco, emails=("rh@acme.com",), nota=85):
    banco.inserir_vagas([Vaga(fonte="gupy", id_fonte="1", titulo="Dev Python", empresa="Acme", url="https://x/1",
                              descricao="Vaga com Python", emails=list(emails))])
    v = banco.vagas_por_status("nova")[0]
    banco.salvar_avaliacao(v.id, Avaliacao(nota=nota, motivo="bom"))
    return v


def test_estado(ctx):
    cliente, *_ = ctx
    r = cliente.get("/api/estado").json()
    assert r["tem_perfil"] is False and r["gmail_configurado"] is True and r["fila"]["aprovados"] == 0


def test_config_ida_e_volta(ctx):
    cliente, *_ = ctx
    cfg = cliente.get("/api/config").json()
    cfg["avaliacao"]["nota_minima"] = 55
    assert cliente.put("/api/config", json=cfg).status_code == 200
    assert cliente.get("/api/config").json()["avaliacao"]["nota_minima"] == 55


def test_fluxo_rascunho_aprovar_enviar_e_bloquear(ctx):
    cliente, banco, llm, enviar, app = ctx
    salvar_perfil(Perfil(nome="Fulano"))
    ambiente().curriculo_path.write_bytes(b"%PDF-1.4")
    v = _vaga(banco)

    r = cliente.post(f"/api/vagas/{v.id}/rascunho").json()
    assert r["destinatario"] == "rh@acme.com" and r["status"] == "pendente"
    assert cliente.post(f"/api/vagas/{v.id}/rascunho").status_code == 409  # já existe

    editado = cliente.put(f"/api/rascunhos/{r['id']}", json={
        "assunto": "Novo assunto", "corpo": "Sou apaixonado por Python — muito.", "destinatario": "RH@acme.com"}).json()
    assert editado["assunto"] == "Novo assunto" and editado["destinatario"] == "rh@acme.com"
    assert any(a["tipo"] == "slop" for a in editado["avisos"])

    listados = cliente.get("/api/rascunhos", params={"status": "pendente"}).json()
    assert listados[0]["vaga"]["titulo"] == "Dev Python"

    assert cliente.post(f"/api/rascunhos/{r['id']}/aprovar").json()["status"] == "aprovado"
    assert cliente.put(f"/api/rascunhos/{r['id']}", json={
        "assunto": "x", "corpo": "y", "destinatario": "a@b.com"}).status_code == 409

    app.state.servicos.fila.processar_um()
    assert len(enviar.mensagens) == 1
    assert cliente.get(f"/api/rascunhos/{r['id']}").json()["status"] == "enviado"
    envios = cliente.get("/api/envios").json()
    assert envios[0]["destinatario"] == "rh@acme.com" and envios[0]["origem"] == "ferramenta"

    detalhe = cliente.get(f"/api/vagas/{v.id}").json()
    assert detalhe["historico"]["bloqueado"] is True and detalhe["status"] == "aplicada"


def test_aprovar_bloqueado_pelo_historico(ctx):
    cliente, banco, *_ = ctx
    v = _vaga(banco)
    rid = banco.criar_rascunho(Rascunho(vaga_id=v.id, destinatario="rh@acme.com", assunto="a", corpo="b"))
    banco.registrar_envio(Envio(destinatario="rh@acme.com", message_id="<g1>", origem="gmail"))
    resp = cliente.post(f"/api/rascunhos/{rid}/aprovar")
    assert resp.status_code == 409 and "rh@acme.com" in resp.json()["detail"]


def test_regerar_e_rejeitar(ctx):
    cliente, banco, llm, *_ = ctx
    salvar_perfil(Perfil(nome="Fulano"))
    v = _vaga(banco)
    rid = banco.criar_rascunho(Rascunho(vaga_id=v.id, destinatario="rh@acme.com", assunto="a", corpo="b"))
    r = cliente.post(f"/api/rascunhos/{rid}/regerar", json={"instrucao": "mais curto"}).json()
    assert r["assunto"] == EMAIL["assunto"] and "mais curto" in llm.chamadas[0]["prompt"]
    assert cliente.post(f"/api/rascunhos/{rid}/rejeitar").json()["status"] == "rejeitado"


def test_rascunho_sem_email_exige_destinatario(ctx):
    cliente, banco, *_ = ctx
    salvar_perfil(Perfil(nome="Fulano"))
    v = _vaga(banco, emails=())
    assert cliente.post(f"/api/vagas/{v.id}/rascunho").status_code == 422
    r = cliente.post(f"/api/vagas/{v.id}/rascunho", json={"destinatario": "Pessoa@Acme.com"})
    assert r.status_code == 200 and r.json()["destinatario"] == "pessoa@acme.com"


def test_marcar_aplicada_pelo_link(ctx):
    cliente, banco, *_ = ctx
    v = _vaga(banco, emails=())
    e = cliente.post(f"/api/vagas/{v.id}/aplicada").json()
    assert e["origem"] == "manual"
    lista = cliente.get("/api/vagas", params={"com_email": False}).json()
    assert lista[0]["status"] == "aplicada" and lista[0]["enviado_em"]


def test_tarefa_buscar_em_segundo_plano(ctx, monkeypatch):
    cliente, *_ = ctx
    from vaga_finder.api.rotas import tarefas as rota

    monkeypatch.setattr(rota, "coletar", lambda banco, cfg, progresso: {"novas": 2})
    t = cliente.post("/api/tarefas/buscar").json()
    for _ in range(50):
        t = cliente.get(f"/api/tarefas/{t['id']}").json()
        if t["status"] != "rodando":
            break
        time.sleep(0.05)
    assert t["status"] == "concluida" and t["resultado"] == {"novas": 2}


def test_avaliar_exige_perfil(ctx):
    cliente, *_ = ctx
    assert cliente.post("/api/tarefas/avaliar").status_code == 409


def test_upload_curriculo_rejeita_nao_pdf(ctx):
    cliente, *_ = ctx
    r = cliente.post("/api/perfil/curriculo", files={"arquivo": ("cv.pdf", b"nada", "application/pdf")})
    assert r.status_code == 422
