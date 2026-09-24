"""Tarefas longas (coleta, avaliação, sincronização) em segundo plano, uma por vez."""

import logging
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from .db import Banco
from .models import Tarefa

log = logging.getLogger(__name__)

Progresso = Callable[[int, int, str], None]


class TarefaEmAndamento(RuntimeError):
    def __init__(self, tarefa: Tarefa):
        super().__init__(f"Já existe uma tarefa rodando: {tarefa.tipo} (#{tarefa.id}).")
        self.tarefa = tarefa


class GerenciadorTarefas:
    def __init__(self, banco: Banco):
        self.banco = banco
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="tarefa")
        self._trava = threading.Lock()

    def iniciar(self, tipo: str, funcao: Callable[[Progresso], dict]) -> Tarefa:
        with self._trava:
            if rodando := self.banco.tarefa_rodando():
                raise TarefaEmAndamento(rodando)
            tarefa = self.banco.criar_tarefa(tipo, "iniciando")

        def progresso(i: int, total: int, mensagem: str) -> None:
            self.banco.atualizar_tarefa(tarefa.id, progresso=i, total=total, mensagem=mensagem)

        def executar() -> None:
            try:
                resultado = funcao(progresso)
                self.banco.atualizar_tarefa(tarefa.id, status="concluida", resultado=resultado, mensagem="concluída")
            except Exception as e:
                log.exception("tarefa %s falhou", tipo)
                self.banco.atualizar_tarefa(tarefa.id, status="erro", mensagem=str(e)[:500])

        self._executor.submit(executar)
        return tarefa

    def encerrar(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)
