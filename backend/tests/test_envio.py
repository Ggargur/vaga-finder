from vaga_finder.config import Config, ambiente
from vaga_finder.envio import FilaEnvio, JaEnviado, LimiteDiario, enviar_rascunho
from vaga_finder.models import Rascunho, Vaga

import pytest


class EnviadorFalso:
    def __init__(self):
        self.mensagens = []

    def __call__(self, amb, msg):
        self.mensagens.append(msg)


def _rascunho(banco, status="aprovado", vaga_id="1", email="rh@acme.com"):
    banco.inserir_vagas([Vaga(fonte="t", id_fonte=vaga_id, titulo=f"Dev {vaga_id}", empresa=f"Acme{vaga_id}",
                              url="https://x", emails=[email])])
    v = [x for x in banco.vagas_por_status("nova") if x.id_fonte == vaga_id][0]
    rid = banco.criar_rascunho(Rascunho(vaga_id=v.id, destinatario=email, assunto="Assunto", corpo="Corpo", status=status))
    return banco.obter_rascunho(rid)


def _cv():
    ambiente().curriculo_path.write_bytes(b"%PDF-1.4 falso")


def test_envia_com_anexo_e_registra(banco):
    _cv()
    r = _rascunho(banco)
    enviar = EnviadorFalso()
    envio = enviar_rascunho(banco, r, Config(), ambiente(), enviar)
    msg = enviar.mensagens[0]
    assert msg["To"] == "rh@acme.com" and msg["From"] == "Fulano Teste <eu@gmail.com>"
    anexos = list(msg.iter_attachments())
    assert anexos[0].get_filename() == "Curriculo - Fulano Teste.pdf"
    assert envio.message_id == msg["Message-ID"]
    assert banco.obter_rascunho(r.id).status == "enviado"
    assert banco.obter_vaga(r.vaga_id).status == "aplicada"
    # segunda tentativa é bloqueada pelo histórico
    with pytest.raises(JaEnviado):
        enviar_rascunho(banco, r, Config(), ambiente(), enviar)
    assert len(enviar.mensagens) == 1


def test_limite_diario(banco):
    _cv()
    cfg = Config()
    cfg.envio.limite_diario = 1
    enviar = EnviadorFalso()
    enviar_rascunho(banco, _rascunho(banco, vaga_id="1", email="a@x.com"), cfg, ambiente(), enviar)
    with pytest.raises(LimiteDiario):
        enviar_rascunho(banco, _rascunho(banco, vaga_id="2", email="b@y.com"), cfg, ambiente(), enviar)


def test_fila_envia_aprovados_e_marca_erro(banco):
    _cv()
    ok = _rascunho(banco, vaga_id="1", email="a@x.com")
    pendente = _rascunho(banco, status="pendente", vaga_id="2", email="b@y.com")
    enviar = EnviadorFalso()
    fila = FilaEnvio(banco, ambiente(), enviar, obter_config=Config)
    assert fila.processar_um() is True
    assert fila.processar_um() is False  # pendente não sai sem aprovação
    assert banco.obter_rascunho(ok.id).status == "enviado"
    assert banco.obter_rascunho(pendente.id).status == "pendente"
    assert fila.segundos_para_proximo() >= 29

    def quebra(amb, msg):
        raise OSError("sem rede")

    banco.atualizar_rascunho(pendente.id, status="aprovado")
    FilaEnvio(banco, ambiente(), quebra, obter_config=Config).processar_um()
    r = banco.obter_rascunho(pendente.id)
    assert r.status == "erro" and "sem rede" in r.erro
