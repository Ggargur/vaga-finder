<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import { api } from '../api/client'
import type { VagaListada } from '../api/tipos'
import EstadoVazio from '../components/EstadoVazio.vue'
import NotaBadge from '../components/NotaBadge.vue'
import { tentar } from '../composables/toast'
import { nomeFonte, relativo } from '../formato'
import { useApp } from '../stores/app'

const app = useApp()
const vagas = ref<VagaListada[]>([])
const carregando = ref(true)
const notaMinima = computed(() => app.estado?.nota_minima ?? 70)

async function carregar() {
  vagas.value =
    (await tentar(() => api.vagas({ status: 'avaliada', nota_min: notaMinima.value, com_email: false, limite: 300 }))) ??
    []
  carregando.value = false
}
onMounted(carregar)
watch([() => app.versao, notaMinima], carregar)

async function aplicada(v: VagaListada) {
  if (await tentar(() => api.marcarAplicada(v.id), 'Registrado no histórico.')) {
    vagas.value = vagas.value.filter((x) => x.id !== v.id)
    app.mudou()
  }
}

async function descartar(v: VagaListada) {
  if (await tentar(() => api.descartarVaga(v.id))) vagas.value = vagas.value.filter((x) => x.id !== v.id)
}
</script>

<template>
  <header>
    <h1 class="text-2xl font-semibold tracking-tight">Aplicar pelo link</h1>
    <p class="text-sm text-texto-2">
      Vagas com nota {{ notaMinima }}+ que não publicam email. Candidate-se no site e marque aqui para entrar no histórico.
    </p>
  </header>

  <p v-if="carregando" class="text-sm text-texto-2">Carregando…</p>
  <EstadoVazio
    v-else-if="!vagas.length"
    titulo="Nada por aqui"
    texto="Quando o Claude avaliar vagas boas sem email de contato, elas aparecem nesta lista."
  />

  <ul v-else class="grid gap-3 md:grid-cols-2">
    <li v-for="v in vagas" :key="v.id" class="cartao flex flex-col gap-3 p-4">
      <div class="flex items-start gap-3">
        <NotaBadge :nota="v.avaliacao?.nota" />
        <div class="min-w-0 flex-1">
          <p class="font-medium">{{ v.titulo }}</p>
          <p class="text-sm text-texto-2">
            {{ v.empresa }} · {{ nomeFonte(v.fonte) }} · {{ v.remoto ? 'Remoto' : v.local }}
          </p>
        </div>
      </div>
      <p v-if="v.avaliacao" class="text-sm text-texto-2">{{ v.avaliacao.motivo }}</p>
      <div class="mt-auto flex flex-wrap items-center gap-2">
        <a :href="v.url" target="_blank" rel="noopener" class="botao primario pequeno">Abrir e candidatar ↗</a>
        <button class="botao pequeno" @click="aplicada(v)">Marquei como aplicada</button>
        <button class="botao perigo pequeno" @click="descartar(v)">Descartar</button>
        <span class="ml-auto text-xs text-texto-2">coletada {{ relativo(v.coletada_em) }}</span>
      </div>
    </li>
  </ul>
</template>
