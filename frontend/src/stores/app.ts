import { defineStore } from 'pinia'
import { ref } from 'vue'

import { api } from '../api/client'
import type { Estado, Tarefa } from '../api/tipos'
import { avisar } from '../composables/toast'

type TipoTarefa = 'buscar' | 'avaliar' | 'rodar' | 'sincronizar'

const NOMES: Record<string, string> = {
  buscar: 'Busca',
  avaliar: 'Avaliação',
  rodar: 'Busca e avaliação',
  sincronizar: 'Sincronização do Gmail',
}

function resumir(t: Tarefa): string {
  const r = t.resultado ?? {}
  const partes: string[] = []
  const coleta = t.tipo === 'buscar' ? r : r.coleta
  if (coleta) partes.push(`${coleta.novas ?? 0} vagas novas`)
  if (r.avaliacao) partes.push(`${r.avaliacao.avaliadas} avaliadas`)
  if (r.redacao) partes.push(`${r.redacao.rascunhos} rascunhos`)
  if (t.tipo === 'sincronizar') partes.push(`${r.importados ?? 0} envios importados`)
  const interrompido = r.avaliacao?.interrompido ?? r.redacao?.interrompido
  if (interrompido) partes.push(`interrompido: ${interrompido}`)
  return partes.join(', ')
}

export const useApp = defineStore('app', () => {
  const estado = ref<Estado | null>(null)
  const tarefa = ref<Tarefa | null>(null)
  /** Aumenta quando algo muda no servidor; as telas observam para recarregar. */
  const versao = ref(0)
  let timer: number | undefined

  async function carregarEstado() {
    try {
      estado.value = await api.estado()
      if (estado.value.tarefa_rodando && !tarefa.value) acompanhar(estado.value.tarefa_rodando)
    } catch {
      /* servidor fora do ar: a próxima rodada tenta de novo */
    }
  }

  function acompanhar(t: Tarefa) {
    tarefa.value = t
    clearTimeout(timer)
    const passo = async () => {
      try {
        const atual = await api.tarefa(t.id)
        tarefa.value = atual
        if (atual.status === 'rodando') {
          timer = window.setTimeout(passo, 2000)
          return
        }
        const nome = NOMES[atual.tipo] ?? atual.tipo
        if (atual.status === 'concluida') avisar(`${nome} concluída. ${resumir(atual)}`, 'ok', 8000)
        else avisar(`${nome} falhou: ${atual.mensagem}`, 'erro')
        versao.value++
        await carregarEstado()
        setTimeout(() => {
          if (tarefa.value?.id === atual.id) tarefa.value = null
        }, 4000)
      } catch {
        timer = window.setTimeout(passo, 4000)
      }
    }
    timer = window.setTimeout(passo, 1000)
  }

  async function iniciar(tipo: TipoTarefa) {
    try {
      acompanhar(await api.iniciarTarefa(tipo))
    } catch (e) {
      avisar(e instanceof Error ? e.message : String(e), 'erro')
    }
  }

  function mudou() {
    versao.value++
    carregarEstado()
  }

  return { estado, tarefa, versao, carregarEstado, iniciar, mudou, nomes: NOMES }
})
