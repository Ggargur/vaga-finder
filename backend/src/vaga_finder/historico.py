"""Controle de candidaturas já enviadas e importação da pasta Enviados do Gmail."""

import email
import imaplib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from email.header import decode_header, make_header
from email.utils import getaddresses, parsedate_to_datetime

from .config import Ambiente, Config
from .db import Banco
from .models import Aviso, Envio, Vaga
from .texto import normalizar

log = logging.getLogger(__name__)


@dataclass
class Checagem:
    bloqueado: bool = False
    avisos: list[Aviso] = field(default_factory=list)

    def bloquear(self, mensagem: str) -> None:
        self.bloqueado = True
        self.avisos.append(Aviso(tipo="historico", mensagem=mensagem))

    def avisar(self, mensagem: str) -> None:
        self.avisos.append(Aviso(tipo="historico", mensagem=mensagem))


def _data(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).astimezone().strftime("%d/%m/%Y")
    except ValueError:
        return iso[:10]


def _sobre(e: Envio) -> str:
    return e.titulo or e.assunto or "outra vaga"


def verificar(banco: Banco, vaga: Vaga, destinatario: str | None, cfg: Config) -> Checagem:
    """Bloqueia reenvio da mesma vaga ou para o mesmo contato dentro do intervalo configurado."""
    c = Checagem()
    for e in banco.envios_da_vaga(vaga.id, vaga.impressao):
        c.bloquear(f"Você já se candidatou a esta vaga em {_data(e.enviado_em)} ({e.origem}).")
        break

    if destinatario:
        dias = cfg.envio.dias_entre_contatos
        limite = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat(timespec="seconds")
        anteriores = banco.envios_para(destinatario)
        recentes = [e for e in anteriores if e.enviado_em >= limite]
        if recentes:
            e = recentes[0]
            c.bloquear(
                f"Você já escreveu para {destinatario} em {_data(e.enviado_em)} sobre “{_sobre(e)}” "
                f"(menos de {dias} dias)."
            )
        elif anteriores:
            e = anteriores[0]
            c.avisar(f"Você escreveu para {destinatario} em {_data(e.enviado_em)} sobre “{_sobre(e)}”.")

    empresa = normalizar(vaga.empresa)
    if empresa:
        outras = [
            e for e in banco.listar_envios(limite=5000)
            if normalizar(e.empresa) == empresa and e.impressao != vaga.impressao
        ]
        if outras:
            e = outras[0]
            c.avisar(f"Você já se candidatou a outra vaga na {vaga.empresa} em {_data(e.enviado_em)}: “{_sobre(e)}”.")
    return c


# ---------- Gmail (IMAP) ----------

# só importa emails enviados com cara de candidatura, para o histórico não virar sua caixa inteira
_ASSUNTO_CANDIDATURA = re.compile(
    r"vaga|candidat|curr[ií]culo|\bcv\b|processo seletivo|oportunidade|application|applying|"
    r"position|\brole\b|\bjob\b|resume|opening|developer|desenvolvedor|engineer|engenheir",
    re.I,
)


def _decodificar(valor: str | None) -> str:
    if not valor:
        return ""
    try:
        return str(make_header(decode_header(valor)))
    except Exception:
        return valor


def pasta_enviados(imap: imaplib.IMAP4_SSL) -> str:
    """O nome muda com o idioma da conta ('[Gmail]/Sent Mail', '[Gmail]/E-mails enviados');
    a flag \\Sent é fixa."""
    _, pastas = imap.list()
    for linha in pastas or []:
        texto = linha.decode(errors="ignore")
        if "\\Sent" in texto:
            return texto.rsplit(' "/" ', 1)[-1].strip()
    return '"[Gmail]/Sent Mail"'


def envios_do_cabecalho(cabecalho: bytes, emails_de_vagas: set[str]) -> list[Envio]:
    msg = email.message_from_bytes(cabecalho)
    assunto = _decodificar(msg.get("Subject"))
    destinatarios = [
        end.lower() for _, end in getaddresses(msg.get_all("To", []) + msg.get_all("Cc", [])) if "@" in end
    ]
    if not destinatarios:
        return []
    if not _ASSUNTO_CANDIDATURA.search(assunto) and not emails_de_vagas.intersection(destinatarios):
        return []
    try:
        data = parsedate_to_datetime(msg.get("Date")).astimezone(timezone.utc).isoformat(timespec="seconds")
    except (TypeError, ValueError):
        return []
    message_id = (msg.get("Message-ID") or "").strip() or None
    envios = []
    for i, dest in enumerate(destinatarios):
        mid = message_id if (i == 0 or not message_id) else f"{message_id}#{dest}"
        envios.append(Envio(destinatario=dest, assunto=assunto, enviado_em=data, message_id=mid, origem="gmail"))
    return envios


def sincronizar_gmail(banco: Banco, amb: Ambiente, dias: int = 365, progresso=None) -> dict:
    if not (amb.gmail_user and amb.gmail_app_password):
        raise ValueError("Configure GMAIL_USER e GMAIL_APP_PASSWORD no backend/.env")
    desde = (datetime.now() - timedelta(days=dias)).strftime("%d-%b-%Y")
    emails_de_vagas = {e for v in banco.listar_vagas(limite=100_000) for e in v["emails"]}
    importados = ignorados = 0
    with imaplib.IMAP4_SSL("imap.gmail.com") as imap:
        imap.login(amb.gmail_user, amb.gmail_app_password.replace(" ", ""))
        imap.select(pasta_enviados(imap), readonly=True)
        _, dados = imap.search(None, "SINCE", desde)
        ids = dados[0].split()
        for i in range(0, len(ids), 200):
            lote = ids[i : i + 200]
            if progresso:
                progresso(i, len(ids), f"lendo enviados {i + 1}-{i + len(lote)} de {len(ids)}")
            _, partes = imap.fetch(b",".join(lote), "(BODY.PEEK[HEADER.FIELDS (TO CC SUBJECT DATE MESSAGE-ID)])")
            for parte in partes:
                if not isinstance(parte, tuple):
                    continue
                envios = envios_do_cabecalho(parte[1], emails_de_vagas)
                if not envios:
                    ignorados += 1
                for e in envios:
                    if banco.registrar_envio(e):
                        importados += 1
    return {"importados": importados, "ignorados": ignorados, "desde": desde}
