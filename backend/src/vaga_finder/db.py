"""Persistência em SQLite. Uma conexão por operação, seguro para as threads das tarefas."""

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from .models import Avaliacao, Aviso, Envio, Rascunho, Tarefa, Vaga, agora

ESQUEMA = """
CREATE TABLE IF NOT EXISTS vagas (
    id INTEGER PRIMARY KEY,
    fonte TEXT NOT NULL,
    id_fonte TEXT NOT NULL,
    titulo TEXT NOT NULL,
    empresa TEXT NOT NULL DEFAULT '',
    local TEXT NOT NULL DEFAULT '',
    remoto INTEGER,
    url TEXT NOT NULL,
    descricao TEXT NOT NULL DEFAULT '',
    emails TEXT NOT NULL DEFAULT '[]',
    publicada_em TEXT,
    coletada_em TEXT NOT NULL,
    impressao TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'nova',
    motivo_filtro TEXT,
    UNIQUE (fonte, id_fonte)
);
CREATE INDEX IF NOT EXISTS idx_vagas_impressao ON vagas (impressao);
CREATE INDEX IF NOT EXISTS idx_vagas_status ON vagas (status);

CREATE TABLE IF NOT EXISTS avaliacoes (
    vaga_id INTEGER PRIMARY KEY REFERENCES vagas (id) ON DELETE CASCADE,
    nota INTEGER NOT NULL,
    motivo TEXT NOT NULL,
    pontos_fortes TEXT NOT NULL DEFAULT '[]',
    lacunas TEXT NOT NULL DEFAULT '[]',
    modelo TEXT NOT NULL DEFAULT '',
    criada_em TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rascunhos (
    id INTEGER PRIMARY KEY,
    vaga_id INTEGER NOT NULL REFERENCES vagas (id) ON DELETE CASCADE,
    destinatario TEXT NOT NULL,
    assunto TEXT NOT NULL,
    corpo TEXT NOT NULL,
    idioma TEXT NOT NULL DEFAULT 'pt',
    status TEXT NOT NULL DEFAULT 'pendente',
    avisos TEXT NOT NULL DEFAULT '[]',
    erro TEXT,
    criado_em TEXT NOT NULL,
    atualizado_em TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_rascunhos_status ON rascunhos (status);

CREATE TABLE IF NOT EXISTS envios (
    id INTEGER PRIMARY KEY,
    vaga_id INTEGER REFERENCES vagas (id) ON DELETE SET NULL,
    impressao TEXT,
    destinatario TEXT,
    empresa TEXT NOT NULL DEFAULT '',
    titulo TEXT NOT NULL DEFAULT '',
    assunto TEXT NOT NULL DEFAULT '',
    corpo TEXT NOT NULL DEFAULT '',
    url TEXT,
    enviado_em TEXT NOT NULL,
    message_id TEXT UNIQUE,
    origem TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_envios_impressao ON envios (impressao);
CREATE INDEX IF NOT EXISTS idx_envios_destinatario ON envios (destinatario);

CREATE TABLE IF NOT EXISTS tarefas (
    id INTEGER PRIMARY KEY,
    tipo TEXT NOT NULL,
    status TEXT NOT NULL,
    progresso INTEGER NOT NULL DEFAULT 0,
    total INTEGER NOT NULL DEFAULT 0,
    mensagem TEXT NOT NULL DEFAULT '',
    resultado TEXT NOT NULL DEFAULT '{}',
    criada_em TEXT NOT NULL,
    terminada_em TEXT
);
"""


def _vaga(linha: sqlite3.Row) -> Vaga:
    d = dict(linha)
    d["emails"] = json.loads(d["emails"])
    d["remoto"] = None if d["remoto"] is None else bool(d["remoto"])
    return Vaga.model_validate(d)


def _rascunho(linha: sqlite3.Row) -> Rascunho:
    d = dict(linha)
    d["avisos"] = [Aviso.model_validate(a) for a in json.loads(d["avisos"])]
    return Rascunho.model_validate(d)


def _tarefa(linha: sqlite3.Row) -> Tarefa:
    d = dict(linha)
    d["resultado"] = json.loads(d["resultado"])
    return Tarefa.model_validate(d)


class Banco:
    def __init__(self, caminho: Path):
        self.caminho = caminho
        with self.conexao() as c:
            c.executescript(ESQUEMA)

    @contextmanager
    def conexao(self) -> Iterator[sqlite3.Connection]:
        c = sqlite3.connect(self.caminho, timeout=30)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys = ON")
        c.execute("PRAGMA journal_mode = WAL")
        try:
            yield c
            c.commit()
        finally:
            c.close()

    # ---------- vagas ----------

    def inserir_vagas(self, vagas: list[Vaga]) -> tuple[int, int]:
        """Insere vagas novas. A mesma vaga vinda de outra fonte (mesma impressão)
        não vira linha nova: só soma os emails à existente. Retorna (novas, repetidas)."""
        novas = repetidas = 0
        with self.conexao() as c:
            for v in vagas:
                existente = c.execute(
                    "SELECT id, emails FROM vagas WHERE (fonte = ? AND id_fonte = ?) OR impressao = ? LIMIT 1",
                    (v.fonte, v.id_fonte, v.impressao),
                ).fetchone()
                if existente:
                    repetidas += 1
                    emails = json.loads(existente["emails"])
                    extras = [e for e in v.emails if e not in emails]
                    if extras:
                        c.execute(
                            "UPDATE vagas SET emails = ? WHERE id = ?",
                            (json.dumps(emails + extras), existente["id"]),
                        )
                    continue
                c.execute(
                    """INSERT INTO vagas (fonte, id_fonte, titulo, empresa, local, remoto, url, descricao,
                       emails, publicada_em, coletada_em, impressao, status)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'nova')""",
                    (
                        v.fonte, v.id_fonte, v.titulo, v.empresa, v.local,
                        None if v.remoto is None else int(v.remoto),
                        v.url, v.descricao, json.dumps(v.emails), v.publicada_em,
                        v.coletada_em, v.impressao,
                    ),
                )
                novas += 1
        return novas, repetidas

    def obter_vaga(self, vaga_id: int) -> Vaga | None:
        with self.conexao() as c:
            linha = c.execute("SELECT * FROM vagas WHERE id = ?", (vaga_id,)).fetchone()
        return _vaga(linha) if linha else None

    def vagas_por_status(self, status: str, limite: int | None = None) -> list[Vaga]:
        sql = "SELECT * FROM vagas WHERE status = ? ORDER BY coletada_em DESC, id DESC"
        params: list = [status]
        if limite:
            sql += " LIMIT ?"
            params.append(limite)
        with self.conexao() as c:
            return [_vaga(r) for r in c.execute(sql, params)]

    def marcar_filtrada(self, vaga_id: int, motivo: str) -> None:
        with self.conexao() as c:
            c.execute(
                "UPDATE vagas SET status = 'filtrada', motivo_filtro = ? WHERE id = ?", (motivo, vaga_id)
            )

    def marcar_status(self, vaga_id: int, status: str) -> None:
        with self.conexao() as c:
            c.execute("UPDATE vagas SET status = ? WHERE id = ?", (status, vaga_id))

    def listar_vagas(
        self,
        *,
        status: str | None = None,
        fonte: str | None = None,
        nota_min: int | None = None,
        com_email: bool | None = None,
        busca: str | None = None,
        limite: int = 200,
        offset: int = 0,
    ) -> list[dict]:
        """Vagas com a avaliação e o estado do rascunho/envio, para a UI."""
        where, params = ["1 = 1"], []
        if status:
            where.append("v.status = ?")
            params.append(status)
        if fonte:
            where.append("v.fonte = ?")
            params.append(fonte)
        if nota_min is not None:
            where.append("a.nota >= ?")
            params.append(nota_min)
        if com_email is True:
            where.append("v.emails != '[]'")
        elif com_email is False:
            where.append("v.emails = '[]'")
        if busca:
            where.append("(v.titulo LIKE ? OR v.empresa LIKE ?)")
            params += [f"%{busca}%", f"%{busca}%"]
        sql = f"""
            SELECT v.*, a.nota, a.motivo, a.pontos_fortes, a.lacunas,
                   (SELECT r.status FROM rascunhos r WHERE r.vaga_id = v.id ORDER BY r.id DESC LIMIT 1) AS rascunho_status,
                   (SELECT MAX(e.enviado_em) FROM envios e WHERE e.vaga_id = v.id OR e.impressao = v.impressao) AS enviado_em
            FROM vagas v LEFT JOIN avaliacoes a ON a.vaga_id = v.id
            WHERE {' AND '.join(where)}
            ORDER BY a.nota IS NULL, a.nota DESC, v.coletada_em DESC
            LIMIT ? OFFSET ?"""
        params += [limite, offset]
        with self.conexao() as c:
            linhas = c.execute(sql, params).fetchall()
        saida = []
        for r in linhas:
            d = _vaga(r).model_dump()
            d["impressao"] = r["impressao"]
            d["avaliacao"] = (
                None
                if r["nota"] is None
                else {
                    "nota": r["nota"],
                    "motivo": r["motivo"],
                    "pontos_fortes": json.loads(r["pontos_fortes"]),
                    "lacunas": json.loads(r["lacunas"]),
                }
            )
            d["rascunho_status"] = r["rascunho_status"]
            d["enviado_em"] = r["enviado_em"]
            saida.append(d)
        return saida

    # ---------- avaliações ----------

    def salvar_avaliacao(self, vaga_id: int, a: Avaliacao) -> None:
        with self.conexao() as c:
            c.execute(
                """INSERT OR REPLACE INTO avaliacoes (vaga_id, nota, motivo, pontos_fortes, lacunas, modelo, criada_em)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (vaga_id, a.nota, a.motivo, json.dumps(a.pontos_fortes, ensure_ascii=False),
                 json.dumps(a.lacunas, ensure_ascii=False), a.modelo, agora()),
            )
            c.execute("UPDATE vagas SET status = 'avaliada' WHERE id = ? AND status = 'nova'", (vaga_id,))

    def obter_avaliacao(self, vaga_id: int) -> Avaliacao | None:
        with self.conexao() as c:
            r = c.execute("SELECT * FROM avaliacoes WHERE vaga_id = ?", (vaga_id,)).fetchone()
        if not r:
            return None
        return Avaliacao(
            nota=r["nota"], motivo=r["motivo"], pontos_fortes=json.loads(r["pontos_fortes"]),
            lacunas=json.loads(r["lacunas"]), modelo=r["modelo"],
        )

    # ---------- rascunhos ----------

    def criar_rascunho(self, r: Rascunho) -> int:
        with self.conexao() as c:
            cur = c.execute(
                """INSERT INTO rascunhos (vaga_id, destinatario, assunto, corpo, idioma, status, avisos,
                   erro, criado_em, atualizado_em) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (r.vaga_id, r.destinatario, r.assunto, r.corpo, r.idioma, r.status,
                 json.dumps([a.model_dump() for a in r.avisos], ensure_ascii=False),
                 r.erro, r.criado_em, r.atualizado_em),
            )
            return cur.lastrowid

    def atualizar_rascunho(self, rascunho_id: int, **campos) -> None:
        if "avisos" in campos:
            campos["avisos"] = json.dumps(
                [a.model_dump() if isinstance(a, Aviso) else a for a in campos["avisos"]], ensure_ascii=False
            )
        campos["atualizado_em"] = agora()
        colunas = ", ".join(f"{k} = ?" for k in campos)
        with self.conexao() as c:
            c.execute(f"UPDATE rascunhos SET {colunas} WHERE id = ?", (*campos.values(), rascunho_id))

    def obter_rascunho(self, rascunho_id: int) -> Rascunho | None:
        with self.conexao() as c:
            r = c.execute("SELECT * FROM rascunhos WHERE id = ?", (rascunho_id,)).fetchone()
        return _rascunho(r) if r else None

    def listar_rascunhos(self, status: str | None = None) -> list[Rascunho]:
        sql, params = "SELECT * FROM rascunhos", []
        if status:
            sql += " WHERE status = ?"
            params.append(status)
        sql += " ORDER BY id"
        with self.conexao() as c:
            return [_rascunho(r) for r in c.execute(sql, params)]

    def rascunho_aberto_da_vaga(self, vaga_id: int) -> Rascunho | None:
        with self.conexao() as c:
            r = c.execute(
                "SELECT * FROM rascunhos WHERE vaga_id = ? AND status IN ('pendente', 'aprovado') ORDER BY id DESC LIMIT 1",
                (vaga_id,),
            ).fetchone()
        return _rascunho(r) if r else None

    # ---------- envios ----------

    def registrar_envio(self, e: Envio) -> int | None:
        """Retorna o id, ou None se o Message-ID já estava registrado."""
        with self.conexao() as c:
            cur = c.execute(
                """INSERT OR IGNORE INTO envios (vaga_id, impressao, destinatario, empresa, titulo, assunto, corpo,
                   url, enviado_em, message_id, origem) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (e.vaga_id, e.impressao, e.destinatario.lower() if e.destinatario else None, e.empresa,
                 e.titulo, e.assunto, e.corpo, e.url, e.enviado_em, e.message_id, e.origem),
            )
            return cur.lastrowid if cur.rowcount else None

    def envios_da_vaga(self, vaga_id: int, impressao: str) -> list[Envio]:
        with self.conexao() as c:
            linhas = c.execute(
                "SELECT * FROM envios WHERE vaga_id = ? OR impressao = ? ORDER BY enviado_em DESC",
                (vaga_id, impressao),
            ).fetchall()
        return [Envio.model_validate(dict(r)) for r in linhas]

    def envios_para(self, destinatario: str, desde: str | None = None) -> list[Envio]:
        sql, params = "SELECT * FROM envios WHERE destinatario = ?", [destinatario.lower()]
        if desde:
            sql += " AND enviado_em >= ?"
            params.append(desde)
        with self.conexao() as c:
            linhas = c.execute(sql + " ORDER BY enviado_em DESC", params).fetchall()
        return [Envio.model_validate(dict(r)) for r in linhas]

    def listar_envios(self, busca: str | None = None, origem: str | None = None, limite: int = 500) -> list[Envio]:
        where, params = ["1 = 1"], []
        if busca:
            where.append("(destinatario LIKE ? OR empresa LIKE ? OR assunto LIKE ? OR titulo LIKE ?)")
            params += [f"%{busca}%"] * 4
        if origem:
            where.append("origem = ?")
            params.append(origem)
        with self.conexao() as c:
            linhas = c.execute(
                f"SELECT * FROM envios WHERE {' AND '.join(where)} ORDER BY enviado_em DESC LIMIT ?",
                (*params, limite),
            ).fetchall()
        return [Envio.model_validate(dict(r)) for r in linhas]

    def contar_envios_desde(self, desde: str, origem: str = "ferramenta") -> int:
        with self.conexao() as c:
            return c.execute(
                "SELECT COUNT(*) FROM envios WHERE origem = ? AND enviado_em >= ?", (origem, desde)
            ).fetchone()[0]

    # ---------- tarefas ----------

    def criar_tarefa(self, tipo: str, mensagem: str = "") -> Tarefa:
        t = Tarefa(tipo=tipo, mensagem=mensagem)
        with self.conexao() as c:
            cur = c.execute(
                "INSERT INTO tarefas (tipo, status, mensagem, criada_em) VALUES (?, ?, ?, ?)",
                (t.tipo, t.status, t.mensagem, t.criada_em),
            )
            t.id = cur.lastrowid
        return t

    def atualizar_tarefa(self, tarefa_id: int, **campos) -> None:
        if "resultado" in campos:
            campos["resultado"] = json.dumps(campos["resultado"], ensure_ascii=False)
        if campos.get("status") in ("concluida", "erro"):
            campos["terminada_em"] = agora()
        colunas = ", ".join(f"{k} = ?" for k in campos)
        with self.conexao() as c:
            c.execute(f"UPDATE tarefas SET {colunas} WHERE id = ?", (*campos.values(), tarefa_id))

    def obter_tarefa(self, tarefa_id: int) -> Tarefa | None:
        with self.conexao() as c:
            r = c.execute("SELECT * FROM tarefas WHERE id = ?", (tarefa_id,)).fetchone()
        return _tarefa(r) if r else None

    def tarefa_rodando(self) -> Tarefa | None:
        with self.conexao() as c:
            r = c.execute("SELECT * FROM tarefas WHERE status = 'rodando' ORDER BY id DESC LIMIT 1").fetchone()
        return _tarefa(r) if r else None

    def listar_tarefas(self, limite: int = 20) -> list[Tarefa]:
        with self.conexao() as c:
            return [_tarefa(r) for r in c.execute("SELECT * FROM tarefas ORDER BY id DESC LIMIT ?", (limite,))]

    def encerrar_tarefas_orfas(self) -> None:
        """Tarefas que ficaram 'rodando' porque o servidor caiu."""
        with self.conexao() as c:
            c.execute(
                "UPDATE tarefas SET status = 'erro', mensagem = 'interrompida (servidor reiniciado)', terminada_em = ? "
                "WHERE status = 'rodando'",
                (agora(),),
            )

    # ---------- painel ----------

    def estatisticas(self, desde_hoje: str) -> dict:
        with self.conexao() as c:
            por_status = dict(c.execute("SELECT status, COUNT(*) FROM vagas GROUP BY status").fetchall())
            pendentes = c.execute("SELECT COUNT(*) FROM rascunhos WHERE status = 'pendente'").fetchone()[0]
            enviados_hoje = c.execute(
                "SELECT COUNT(*) FROM envios WHERE origem = 'ferramenta' AND enviado_em >= ?", (desde_hoje,)
            ).fetchone()[0]
            enviados_total = c.execute("SELECT COUNT(*) FROM envios").fetchone()[0]
            por_fonte = dict(c.execute("SELECT fonte, COUNT(*) FROM vagas GROUP BY fonte").fetchall())
        return {
            "vagas_por_status": por_status,
            "vagas_por_fonte": por_fonte,
            "rascunhos_pendentes": pendentes,
            "enviados_hoje": enviados_hoje,
            "enviados_total": enviados_total,
        }
