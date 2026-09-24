from datetime import datetime, timedelta, timezone

from vaga_finder.config import Config
from vaga_finder.historico import envios_do_cabecalho, verificar
from vaga_finder.models import Envio, Vaga


def _vaga(banco, **kw):
    base = dict(fonte="t", id_fonte="1", titulo="Dev Python", empresa="Acme", url="https://x/1", emails=["rh@acme.com"])
    banco.inserir_vagas([Vaga(**(base | kw))])
    return banco.vagas_por_status("nova")[0]


def _dias_atras(n):
    return (datetime.now(timezone.utc) - timedelta(days=n)).isoformat(timespec="seconds")


def test_livre_sem_historico(banco):
    v = _vaga(banco)
    c = verificar(banco, v, "rh@acme.com", Config())
    assert not c.bloqueado and c.avisos == []


def test_bloqueia_mesma_vaga_mesmo_vinda_de_outra_fonte(banco):
    v = _vaga(banco)
    banco.registrar_envio(Envio(impressao=v.impressao, destinatario="outro@acme.com", message_id="<a>"))
    c = verificar(banco, v, "rh@acme.com", Config())
    assert c.bloqueado and "já se candidatou a esta vaga" in c.avisos[0].mensagem


def test_bloqueia_contato_recente_e_so_avisa_contato_antigo(banco):
    v = _vaga(banco)
    cfg = Config()
    banco.registrar_envio(Envio(destinatario="rh@acme.com", titulo="Dev Java", enviado_em=_dias_atras(10), message_id="<a>"))
    c = verificar(banco, v, "RH@acme.com", cfg)
    assert c.bloqueado and "Dev Java" in c.avisos[0].mensagem

    cfg.envio.dias_entre_contatos = 5
    c = verificar(banco, v, "rh@acme.com", cfg)
    assert not c.bloqueado and "Você escreveu para rh@acme.com" in c.avisos[0].mensagem


def test_avisa_outra_vaga_na_mesma_empresa(banco):
    v = _vaga(banco)
    banco.registrar_envio(Envio(empresa="ACME", titulo="Dev Go", impressao="x", destinatario="a@b.com", message_id="<a>"))
    c = verificar(banco, v, "rh@acme.com", Config())
    assert not c.bloqueado and "outra vaga na Acme" in c.avisos[0].mensagem


def test_cabecalho_gmail_importa_candidaturas_e_ignora_pessoais():
    cand = (
        b"To: RH Acme <rh@acme.com>\r\nCc: tech@acme.com\r\nSubject: =?utf-8?q?Candidatura_=C3=A0_vaga?=\r\n"
        b"Date: Mon, 07 Sep 2026 10:00:00 -0300\r\nMessage-ID: <x1@mail>\r\n\r\n"
    )
    envios = envios_do_cabecalho(cand, set())
    assert [e.destinatario for e in envios] == ["rh@acme.com", "tech@acme.com"]
    assert envios[0].assunto == "Candidatura à vaga" and envios[0].enviado_em == "2026-09-07T13:00:00+00:00"
    assert envios[0].message_id == "<x1@mail>" and envios[1].message_id == "<x1@mail>#tech@acme.com"

    pessoal = b"To: mae@gmail.com\r\nSubject: Almoco domingo\r\nDate: Mon, 07 Sep 2026 10:00:00 -0300\r\n\r\n"
    assert envios_do_cabecalho(pessoal, set()) == []
    assert len(envios_do_cabecalho(pessoal, {"mae@gmail.com"})) == 1
