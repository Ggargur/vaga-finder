<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted } from 'vue'
import { RouterLink, RouterView } from 'vue-router'

import BarraTarefa from './components/BarraTarefa.vue'
import Toasts from './components/Toasts.vue'
import { useApp } from './stores/app'

const app = useApp()
let intervalo: number | undefined

onMounted(() => {
  app.carregarEstado()
  intervalo = window.setInterval(app.carregarEstado, 15000)
})
onBeforeUnmount(() => clearInterval(intervalo))

const itens = computed(() => [
  { to: '/', rotulo: 'Painel' },
  { to: '/revisao', rotulo: 'Revisão', contador: app.estado?.rascunhos_pendentes },
  { to: '/vagas', rotulo: 'Vagas' },
  { to: '/aplicar', rotulo: 'Aplicar pelo link' },
  { to: '/historico', rotulo: 'Histórico' },
  { to: '/perfil', rotulo: 'Perfil' },
  { to: '/config', rotulo: 'Config' },
])
</script>

<template>
  <div class="min-h-screen md:flex">
    <aside class="border-b border-borda bg-superficie md:sticky md:top-0 md:h-screen md:w-56 md:shrink-0 md:border-r md:border-b-0">
      <div class="flex items-center gap-2 px-4 py-4 md:px-5 md:py-6">
        <img src="/favicon.svg" alt="" class="h-6 w-6" />
        <span class="font-semibold tracking-tight">vaga-finder</span>
      </div>
      <nav class="flex gap-1 overflow-x-auto px-2 pb-2 md:flex-col md:px-3" aria-label="Principal">
        <RouterLink
          v-for="i in itens"
          :key="i.to"
          :to="i.to"
          class="flex shrink-0 items-center justify-between gap-2 rounded-lg px-3 py-2 text-sm text-texto-2 hover:bg-superficie-2 hover:text-texto"
          active-class="!bg-marca-suave !text-marca font-medium"
        >
          {{ i.rotulo }}
          <span
            v-if="i.contador"
            class="rounded-full bg-marca px-1.5 text-[11px] leading-5 font-semibold text-white tabular-nums dark:text-fundo"
          >
            {{ i.contador }}
          </span>
        </RouterLink>
      </nav>
    </aside>

    <main class="min-w-0 flex-1 px-4 py-6 md:px-8 md:py-8">
      <div class="mx-auto max-w-6xl space-y-4">
        <BarraTarefa />
        <RouterView />
      </div>
    </main>
    <Toasts />
  </div>
</template>
