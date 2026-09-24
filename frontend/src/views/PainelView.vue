<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import { api } from '../api/client'
import type { Tarefa } from '../api/tipos'
import { relativo } from '../formato'
import { useApp } from '../stores/app'

const app = useApp()
const tarefas = ref<Tarefa[]>([])

async function carregar() {
  tarefas.value = await api.tarefas().catch(() => [])
}
onMounted(carregar)
watch(() => app.versao, carregar)

const e = computed(() => app.estado)
const ocupado = computed(() => app.tarefa?.status === 'rodando')
const totalVagas = computed(() => Object.values(e.value?.vagas_por_fonte ?? {}).reduce((a, b) => a + b, 0))

const passos = computed(() => [
  { feito: !!e.value?.tem_perfil, texto: 'Enviar o currículo e revisar o perfil', to: '/perfil' },
  { feito: !!e.value?.gmail_configurado, texto: 'Configurar o Gmail no backend/.env', to: '/config' },
  { feito: totalVagas.value > 0, texto: 'Buscar as primeiras vagas', to: '/' },
])
const configurado = computed(() => passos.value.every((p) => p.feito))

function resumoTarefa(t: Tarefa): string {
  if (t.status !== 'concluida') return t.mensagem
  const r = t.resultado
  const c = t.tipo === 'buscar' ? r : r.coleta
  const partes = []
  if (c) partes.push(`${c.novas} novas`)
  if (r.avaliacao) partes.push(`${r.avaliacao.avaliadas} avaliadas, ${r.avaliacao.filtradas} filtradas`)
  if (r.redacao) partes.push(`${r.redacao.rascunhos} rascunhos`)
  if (t.tipo === 'sincronizar') partes.push(`${r.importados} importados`)
  if (c?.erros && Object.keys(c.erros).length) partes.push(`falhas: ${Object.keys(c.erros).join(', ')}`)
  return partes.join(' · ')
}
</script>

<template>
  <header class="flex flex-wrap items-end justify-between gap-4">
    <div>
      <h1 class="text-2xl font-semibold tracking-tight">Painel</h1>
      <p class="text-sm text-texto-2">Busque vagas, deixe o Claude avaliar e revise os emails antes de enviar.</p>
    </div>
    <div class="flex flex-wrap gap-2">
      <button class="botao" :disabled="ocupado" @click="app.iniciar('buscar')">Só buscar</button>
      <button class="botao" :disabled="ocupado || !e?.tem_perfil" @click="app.iniciar('avaliar')">Só avaliar</button>
      <button class="botao primario" :disabled="ocupado || !e?.tem_perfil" @click="app.iniciar('rodar')">
        Buscar e avaliar
      </button>
    </div>
  </header>

  <section v-if="e && !configurado" class="cartao p-5">
    <h2 class="font-medium">Primeiros passos</h2>
    <ol class="mt-3 space-y-2 text-sm">
      <li v-for="(p, i) in passos" :key="i" class="flex items-center gap-3">
        <span
          class="flex h-6 w-6 items-center justify-center rounded-full text-xs font-semibold"
          :class="p.feito ? 'bg-ok-suave text-ok' : 'bg-superficie-2 text-texto-2'"
        >
          {{ p.feito ? '✓' : i + 1 }}
        </span>
        <RouterLink v-if="!p.feito && p.to !== '/'" :to="p.to" class="link">{{ p.texto }}</RouterLink>
        <span v-else :class="p.feito ? 'text-texto-2 line-through' : ''">{{ p.texto }}</span>
      </li>
    </ol>
  </section>

  <section class="grid grid-cols-2 gap-3 lg:grid-cols-4">
    <RouterLink to="/revisao" class="cartao p-4 hover:border-marca">
      <p class="text-xs text-texto-2 uppercase">Para revisar</p>
      <p class="mt-1 text-3xl font-semibold tabular-nums">{{ e?.rascunhos_pendentes ?? '–' }}</p>
      <p class="text-xs text-texto-2">
        {{ e?.fila.aprovados ? `${e.fila.aprovados} na fila de envio` : 'rascunhos pendentes' }}
      </p>
    </RouterLink>
    <div class="cartao p-4">
      <p class="text-xs text-texto-2 uppercase">Enviados hoje</p>
      <p class="mt-1 text-3xl font-semibold tabular-nums">
        {{ e?.enviados_hoje ?? '–' }}<span class="text-base font-normal text-texto-2">/{{ e?.limite_diario }}</span>
      </p>
      <p class="text-xs text-texto-2">{{ e?.enviados_total ?? 0 }} no histórico</p>
    </div>
    <RouterLink to="/vagas" class="cartao p-4 hover:border-marca">
      <p class="text-xs text-texto-2 uppercase">Avaliadas</p>
      <p class="mt-1 text-3xl font-semibold tabular-nums">{{ e?.vagas_por_status.avaliada ?? 0 }}</p>
      <p class="text-xs text-texto-2">{{ e?.vagas_por_status.nova ?? 0 }} aguardando avaliação</p>
    </RouterLink>
    <div class="cartao p-4">
      <p class="text-xs text-texto-2 uppercase">Coletadas</p>
      <p class="mt-1 text-3xl font-semibold tabular-nums">{{ totalVagas }}</p>
      <p class="text-xs text-texto-2">{{ e?.vagas_por_status.filtrada ?? 0 }} descartadas no filtro</p>
    </div>
  </section>

  <section class="grid gap-4 lg:grid-cols-[2fr_1fr]">
    <div class="cartao">
      <h2 class="border-b border-borda px-5 py-3 font-medium">Últimas execuções</h2>
      <ul v-if="tarefas.length" class="divide-y divide-borda">
        <li v-for="t in tarefas.slice(0, 8)" :key="t.id" class="flex items-center gap-3 px-5 py-3 text-sm">
          <span
            class="h-2 w-2 shrink-0 rounded-full"
            :class="{ 'bg-ok': t.status === 'concluida', 'bg-erro': t.status === 'erro', 'animate-pulse bg-marca': t.status === 'rodando' }"
          />
          <span class="w-40 shrink-0 font-medium">{{ app.nomes[t.tipo] ?? t.tipo }}</span>
          <span class="min-w-0 flex-1 truncate text-texto-2" :title="resumoTarefa(t)">{{ resumoTarefa(t) }}</span>
          <span class="shrink-0 text-xs text-texto-2">{{ relativo(t.criada_em) }}</span>
        </li>
      </ul>
      <p v-else class="px-5 py-8 text-center text-sm text-texto-2">Nenhuma execução ainda.</p>
    </div>

    <div class="cartao p-5 text-sm">
      <h2 class="font-medium">Vagas por fonte</h2>
      <ul class="mt-3 space-y-2">
        <li v-for="(n, fonte) in e?.vagas_por_fonte" :key="fonte" class="flex justify-between">
          <span class="capitalize">{{ fonte }}</span>
          <span class="tabular-nums text-texto-2">{{ n }}</span>
        </li>
      </ul>
      <p v-if="!totalVagas" class="mt-2 text-texto-2">Nenhuma vaga coletada.</p>
      <button class="botao mt-5 w-full" :disabled="ocupado || !e?.gmail_configurado" @click="app.iniciar('sincronizar')">
        Sincronizar Enviados do Gmail
      </button>
      <p class="mt-2 text-xs text-texto-2">
        Importa candidaturas que você mandou por fora, para o vaga-finder não escrever de novo para os mesmos contatos.
      </p>
    </div>
  </section>
</template>
