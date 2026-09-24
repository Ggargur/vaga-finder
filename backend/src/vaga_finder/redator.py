"""Redação dos emails com o Claude: rascunho → revisão com as regras do stop-slop → linter."""

import json
import logging
import re
from dataclasses import dataclass

from . import historico, prompts, slop_lint
from .config import Config, ambiente
from .db import Banco
from .llm import LLM, LimiteDeUso
from .matcher import MAX_DESCRICAO_PROMPT
from .models import Avaliacao, Aviso, Rascunho, Vaga
from .perfil import Perfil, perfil_para_prompt

log = logging.getLogger(__name__)

SCHEMA_EMAIL = {
    "type": "object",
    "properties": {
        "assunto": {"type": "string"},
        "corpo": {"type": "string"},
        "idioma": {"type": "string", "enum": ["pt", "en"]},
    },
    "required": ["assunto", "corpo", "idioma"],
}

SISTEMA_REDACAO = (
    "Você escreve emails de candidatura curtos, diretos e específicos, em primeira pessoa, "
    "usando só fatos do perfil do candidato."
)

_PT = re.compile(r"\b(de|para|com|você|vaga|experiência|requisitos|empresa|atuar|conhecimento|são|não)\b", re.I)
_EN = re.compile(r"\b(the|and|with|you|we|our|experience|requirements|role|will|team|about)\b", re.I)


def detectar_idioma(texto: str) -> str:
    amostra = texto[:3000]
    return "pt" if len(_PT.findall(amostra)) >= len(_EN.findall(amostra)) else "en"


@dataclass
class Email:
    assunto: str
    corpo: str
    idioma: str
    avisos: list[Aviso]


def _limpar(corpo: str) -> str:
    corpo = corpo.replace("\r\n", "\n").strip()
    return re.sub(r"\n{3,}", "\n\n", corpo)


def redigir(
    vaga: Vaga,
    avaliacao: Avaliacao | None,
    perfil: Perfil,
    cfg: Config,
    llm: LLM,
    instrucao: str | None = None,
) -> Email:
    r = cfg.redacao
    idioma = detectar_idioma(f"{vaga.titulo}\n{vaga.descricao}")
    idioma_instrucao = (
        "português do Brasil (a vaga está em português)." if idioma == "pt" else "inglês (a vaga está em inglês)."
    )
    assinatura = r.assinatura.strip()
    nome = perfil.nome or ambiente().remetente_nome
    extra = f"\nPedido do candidato para esta versão: {instrucao.strip()}\n" if instrucao and instrucao.strip() else ""

    rascunho = llm.json(
        prompts.renderizar(
            "redigir",
            idioma_instrucao=idioma_instrucao,
            palavras_min=r.palavras_min,
            palavras_max=r.palavras_max,
            fonte=vaga.fonte.capitalize(),
            assinatura_instrucao=f" Use exatamente esta assinatura:\n{assinatura}" if assinatura else f" Nome: {nome}.",
            instrucao_extra=extra,
            perfil=perfil_para_prompt(perfil),
            avaliacao=json.dumps(avaliacao.model_dump(exclude={"modelo"}), ensure_ascii=False) if avaliacao else "{}",
            vaga=json.dumps(
                {"titulo": vaga.titulo, "empresa": vaga.empresa, "local": vaga.local,
                 "descricao": vaga.descricao[:MAX_DESCRICAO_PROMPT]},
                ensure_ascii=False,
            ),
        ),
        SCHEMA_EMAIL,
        sistema=SISTEMA_REDACAO,
        modelo=r.modelo,
    )

    problemas = slop_lint.verificar(rascunho["corpo"] + "\n" + rascunho["assunto"], r.palavras_min, r.palavras_max)
    lista_problemas = (
        "\nO linter já encontrou estes problemas no rascunho:\n" + "\n".join(f"- {a.mensagem}" for a in problemas) + "\n"
        if problemas
        else ""
    )
    revisado = llm.json(
        prompts.renderizar(
            "revisar_slop",
            palavras_min=r.palavras_min,
            palavras_max=r.palavras_max,
            problemas=lista_problemas,
            assunto=rascunho["assunto"],
            corpo=rascunho["corpo"],
        ),
        SCHEMA_EMAIL,
        sistema=prompts.sistema_stop_slop(),
        modelo=r.modelo,
    )
    assunto = revisado.get("assunto", "").strip() or rascunho["assunto"].strip()
    corpo = _limpar(revisado.get("corpo", "") or rascunho["corpo"])
    return Email(
        assunto=assunto,
        corpo=corpo,
        idioma=revisado.get("idioma") or idioma,
        avisos=slop_lint.verificar(corpo + "\n" + assunto, r.palavras_min, r.palavras_max),
    )


def gerar_rascunho(banco: Banco, vaga: Vaga, perfil: Perfil, cfg: Config, llm: LLM) -> Rascunho | None:
    """Cria o rascunho da vaga, ou None se o histórico bloquear (já enviada / contato recente)."""
    if not vaga.emails:
        return None
    destinatario = vaga.emails[0]
    checagem = historico.verificar(banco, vaga, destinatario, cfg)
    if checagem.bloqueado:
        return None
    email = redigir(vaga, banco.obter_avaliacao(vaga.id), perfil, cfg, llm)
    rascunho = Rascunho(
        vaga_id=vaga.id,
        destinatario=destinatario,
        assunto=email.assunto,
        corpo=email.corpo,
        idioma=email.idioma,
        avisos=checagem.avisos + email.avisos,
    )
    rascunho.id = banco.criar_rascunho(rascunho)
    return rascunho


def regerar(banco: Banco, rascunho_id: int, perfil: Perfil, cfg: Config, llm: LLM, instrucao: str | None = None) -> Rascunho:
    rascunho = banco.obter_rascunho(rascunho_id)
    if not rascunho:
        raise KeyError(rascunho_id)
    vaga = banco.obter_vaga(rascunho.vaga_id)
    email = redigir(vaga, banco.obter_avaliacao(vaga.id), perfil, cfg, llm, instrucao)
    checagem = historico.verificar(banco, vaga, rascunho.destinatario, cfg)
    banco.atualizar_rascunho(
        rascunho_id,
        assunto=email.assunto,
        corpo=email.corpo,
        idioma=email.idioma,
        avisos=checagem.avisos + email.avisos,
        status="pendente",
        erro=None,
    )
    return banco.obter_rascunho(rascunho_id)


def vagas_para_rascunho(banco: Banco, cfg: Config) -> list[Vaga]:
    """Avaliadas, acima da nota mínima, com email e sem nenhum rascunho ainda."""
    candidatas = banco.listar_vagas(status="avaliada", nota_min=cfg.avaliacao.nota_minima, com_email=True, limite=10_000)
    return [
        banco.obter_vaga(d["id"])
        for d in candidatas
        if d["rascunho_status"] is None and d["enviado_em"] is None
    ]


def gerar_rascunhos_pendentes(banco: Banco, cfg: Config, perfil: Perfil, llm: LLM, progresso=None) -> dict:
    vagas = vagas_para_rascunho(banco, cfg)
    resumo = {"rascunhos": 0, "bloqueadas_historico": 0, "falhas": 0, "interrompido": None}
    for i, vaga in enumerate(vagas):
        if progresso:
            progresso(i, len(vagas), f"redigindo email {i + 1} de {len(vagas)}: {vaga.titulo}")
        try:
            if gerar_rascunho(banco, vaga, perfil, cfg, llm):
                resumo["rascunhos"] += 1
            else:
                resumo["bloqueadas_historico"] += 1
        except LimiteDeUso as e:
            resumo["interrompido"] = f"cota do Claude esgotada: {e}"
            break
        except Exception as e:
            log.warning("falha ao redigir para a vaga %s: %s", vaga.id, e)
            resumo["falhas"] += 1
    return resumo
