<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'

import { api } from '../api/client'
import type { Envio } from '../api/tipos'
import EstadoVazio from '../components/EstadoVazio.vue'
import { tentar } from '../composables/toast'
import { ROTULO_ORIGEM, formatarDataHora } from '../formato'
import { useApp } from '../stores/app'

const app = useApp()
const envios = ref<Envio[]>([])
const busca = ref('')
const origem = ref('')
const aberto = ref<number | null>(null)
const carregando = ref(true)

async function carregar() {
  envios.value = (await tentar(() => api.envios(busca.value, origem.value))) ?? []
  carregando.value = false
}

let atraso: number | undefined
watch([busca, origem], () => {
  clearTimeout(atraso)
  atraso = window.setTimeout(carregar, 250)
})
watch(() => app.versao, carregar)
onMounted(carregar)

const coresOrigem: Record<string, string> = {
  ferramenta: 'bg-marca-suave text-marca',
  gmail: 'bg-superficie-2 text-texto-2',
  manual: 'bg-atencao-suave text-atencao',
}
</script>

<template>
  <header class="flex flex-wrap items-end justify-between gap-3">
    <div>
      <h1 class="text-2xl font-semibold tracking-tight">Histórico</h1>
      <p class="text-sm text-texto-2">
        Tudo o que você já enviou. O vaga-finder consulta esta lista antes de cada envio para não repetir vaga nem contato.
      </p>
    </div>
    <button
      class="botao"
      :disabled="app.tarefa?.status === 'rodando' || !app.estado?.gmail_configurado"
      @click="app.iniciar('sincronizar')"
    >
      Sincronizar Gmail
    </button>
  </header>

  <div class="cartao flex flex-col gap-3 p-4 sm:flex-row">
    <input v-model="busca" type="search" class="campo" placeholder="Buscar por email, empresa, vaga ou assunto" />
    <select v-model="origem" class="campo sm:w-48">
      <option value="">Todas as origens</option>
      <option value="ferramenta">vaga-finder</option>
      <option value="gmail">Gmail (importado)</option>
      <option value="manual">Pelo link</option>
    </select>
  </div>

  <p v-if="carregando" class="text-sm text-texto-2">Carregando…</p>
  <EstadoVazio
    v-else-if="!envios.length"
    titulo="Nenhum envio registrado"
    texto="Os emails aprovados na Revisão aparecem aqui. Sincronize o Gmail para trazer candidaturas antigas."
  />

  <ul v-else class="cartao divide-y divide-borda">
    <li v-for="(e, i) in envios" :key="e.id ?? i">
      <button class="flex w-full flex-wrap items-center gap-x-4 gap-y-1 px-5 py-3 text-left text-sm hover:bg-superficie-2" @click="aberto = aberto === i ? null : i">
        <span class="w-32 shrink-0 text-texto-2 tabular-nums">{{ formatarDataHora(e.enviado_em) }}</span>
        <span class="min-w-0 flex-1">
          <span class="block truncate font-medium">{{ e.titulo || e.assunto || '(sem assunto)' }}</span>
          <span class="block truncate text-xs text-texto-2">
            {{ [e.empresa, e.destinatario ?? 'candidatura pelo link'].filter(Boolean).join(' · ') }}
          </span>
        </span>
        <span class="rounded-full px-2 py-0.5 text-xs font-medium" :class="coresOrigem[e.origem]">
          {{ ROTULO_ORIGEM[e.origem] }}
        </span>
      </button>
      <div v-if="aberto === i" class="space-y-2 border-t border-borda bg-superficie-2 px-5 py-4 text-sm">
        <p v-if="e.assunto"><span class="text-texto-2">Assunto:</span> {{ e.assunto }}</p>
        <p v-if="e.url"><a :href="e.url" target="_blank" rel="noopener" class="link">Abrir vaga ↗</a></p>
        <p v-if="e.corpo" class="whitespace-pre-line">{{ e.corpo }}</p>
        <p v-else class="text-texto-2">Corpo não registrado ({{ ROTULO_ORIGEM[e.origem] }}).</p>
      </div>
    </li>
  </ul>
</template>
