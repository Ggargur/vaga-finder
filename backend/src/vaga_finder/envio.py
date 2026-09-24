"""Envio pelo Gmail (SMTP + senha de app) e fila que respeita pausas e limite diário."""

import logging
import random
import smtplib
import threading
import time
from collections.abc import Callable
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import formatdate, formataddr, make_msgid
from pathlib import Path

from . import historico
from .config import Ambiente, Config, carregar_config
from .db import Banco
from .models import Envio, Rascunho
from .perfil import carregar_perfil

log = logging.getLogger(__name__)

Enviador = Callable[[Ambiente, EmailMessage], None]


class ErroEnvio(RuntimeError):
    pass


class JaEnviado(ErroEnvio):
    pass


class LimiteDiario(ErroEnvio):
    pass


def inicio_do_dia_utc() -> str:
    meia_noite = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
    return meia_noite.astimezone(timezone.utc).isoformat(timespec="seconds")


def nome_do_anexo(nome: str) -> str:
    return f"Curriculo - {nome}.pdf" if nome else "Curriculo.pdf"


def montar_mensagem(amb: Ambiente, destinatario: str, assunto: str, corpo: str, anexo: Path | None, nome: str) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = formataddr((nome, amb.gmail_user)) if nome else amb.gmail_user
    msg["To"] = destinatario
    msg["Subject"] = assunto
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=amb.gmail_user.split("@")[-1] or "localhost")
    msg.set_content(corpo)
    if anexo:
        msg.add_attachment(anexo.read_bytes(), maintype="application", subtype="pdf", filename=nome_do_anexo(nome))
    return msg


def enviar_smtp(amb: Ambiente, msg: EmailMessage) -> None:
    if not (amb.gmail_user and amb.gmail_app_password):
        raise ErroEnvio("Configure GMAIL_USER e GMAIL_APP_PASSWORD no backend/.env")
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=60) as smtp:
            smtp.login(amb.gmail_user, amb.gmail_app_password.replace(" ", ""))
            smtp.send_message(msg)
    except smtplib.SMTPAuthenticationError as e:
        raise ErroEnvio("O Gmail recusou o login. Confira GMAIL_USER e a senha de app.") from e


def _anexo(amb: Ambiente, cfg: Config) -> Path | None:
    if not cfg.envio.anexar_curriculo:
        return None
    if not amb.curriculo_path.exists():
        raise ErroEnvio("Currículo não encontrado. Envie o PDF na tela Perfil ou desligue o anexo em Config.")
    return amb.curriculo_path


def _nome(amb: Ambiente) -> str:
    perfil = carregar_perfil()
    return amb.remetente_nome or (perfil.nome if perfil else "")


def enviar_rascunho(banco: Banco, rascunho: Rascunho, cfg: Config, amb: Ambiente, enviar: Enviador = enviar_smtp) -> Envio:
    vaga = banco.obter_vaga(rascunho.vaga_id)
    checagem = historico.verificar(banco, vaga, rascunho.destinatario, cfg)
    if checagem.bloqueado:
        raise JaEnviado(" ".join(a.mensagem for a in checagem.avisos if a.tipo == "historico"))
    if banco.contar_envios_desde(inicio_do_dia_utc()) >= cfg.envio.limite_diario:
        raise LimiteDiario(f"Limite diário de {cfg.envio.limite_diario} envios atingido.")

    msg = montar_mensagem(amb, rascunho.destinatario, rascunho.assunto, rascunho.corpo, _anexo(amb, cfg), _nome(amb))
    enviar(amb, msg)

    envio = Envio(
        vaga_id=vaga.id,
        impressao=vaga.impressao,
        destinatario=rascunho.destinatario,
        empresa=vaga.empresa,
        titulo=vaga.titulo,
        assunto=rascunho.assunto,
        corpo=rascunho.corpo,
        url=vaga.url,
        message_id=msg["Message-ID"],
        origem="ferramenta",
    )
    envio.id = banco.registrar_envio(envio)
    banco.atualizar_rascunho(rascunho.id, status="enviado", erro=None)
    banco.marcar_status(vaga.id, "aplicada")
    return envio


def enviar_teste(banco: Banco, cfg: Config, amb: Ambiente, enviar: Enviador = enviar_smtp) -> str:
    """Manda para o próprio Gmail o rascunho pendente mais recente (ou um texto de exemplo)."""
    pendentes = banco.listar_rascunhos("pendente")
    if pendentes:
        r = pendentes[-1]
        assunto, corpo = f"[TESTE] {r.assunto}", f"(Teste: este email iria para {r.destinatario})\n\n{r.corpo}"
    else:
        assunto, corpo = "[TESTE] vaga-finder", "Se você recebeu este email, o envio pelo Gmail está funcionando."
    enviar(amb, montar_mensagem(amb, amb.gmail_user, assunto, corpo, _anexo(amb, cfg), _nome(amb)))
    return amb.gmail_user


class FilaEnvio:
    """Envia em segundo plano os rascunhos aprovados, com pausa aleatória entre eles."""

    ESPERA_LIMITE_DIARIO = 30 * 60

    def __init__(self, banco: Banco, amb: Ambiente, enviar: Enviador = enviar_smtp, obter_config=carregar_config):
        self.banco = banco
        self.amb = amb
        self.enviar = enviar
        self.obter_config = obter_config
        self._acordar = threading.Event()
        self._parar = threading.Event()
        self._proximo_envio = 0.0  # time.monotonic()
        self._thread: threading.Thread | None = None

    def iniciar(self) -> None:
        self._thread = threading.Thread(target=self._loop, name="fila-envio", daemon=True)
        self._thread.start()

    def parar(self) -> None:
        self._parar.set()
        self._acordar.set()

    def acordar(self) -> None:
        self._acordar.set()

    def segundos_para_proximo(self) -> int:
        return max(0, round(self._proximo_envio - time.monotonic()))

    def processar_um(self) -> bool:
        """Envia o aprovado mais antigo. Retorna False se não havia nada a enviar."""
        aprovados = self.banco.listar_rascunhos("aprovado")
        if not aprovados:
            return False
        r = aprovados[0]
        cfg = self.obter_config()
        try:
            enviar_rascunho(self.banco, r, cfg, self.amb, self.enviar)
            log.info("enviado rascunho %s para %s", r.id, r.destinatario)
            self._proximo_envio = time.monotonic() + random.uniform(cfg.envio.pausa_min_s, cfg.envio.pausa_max_s)
        except LimiteDiario as e:
            # continua aprovado; sai amanhã
            self.banco.atualizar_rascunho(r.id, erro=f"{e} Fica na fila para amanhã.")
            self._proximo_envio = time.monotonic() + self.ESPERA_LIMITE_DIARIO
        except Exception as e:
            log.warning("falha ao enviar rascunho %s: %s", r.id, e)
            self.banco.atualizar_rascunho(r.id, status="erro", erro=str(e)[:500])
        return True

    def _loop(self) -> None:
        while not self._parar.is_set():
            espera = self._proximo_envio - time.monotonic()
            if espera > 0:
                self._parar.wait(espera)
                continue
            try:
                havia = self.processar_um()
            except Exception:
                log.exception("erro na fila de envio")
                havia = False
            if not havia:
                self._acordar.wait(timeout=60)
                self._acordar.clear()
