<script setup lang="ts">
import { computed } from 'vue'

import { useApp } from '../stores/app'

const app = useApp()
const pct = computed(() => {
  const t = app.tarefa
  if (!t || !t.total) return null
  return Math.min(100, Math.round((t.progresso / t.total) * 100))
})
</script>

<template>
  <div v-if="app.tarefa" class="cartao px-4 py-3" role="status" aria-live="polite">
    <div class="flex items-center gap-3 text-sm">
      <span
        v-if="app.tarefa.status === 'rodando'"
        class="h-3 w-3 animate-spin rounded-full border-2 border-marca border-t-transparent"
        aria-hidden="true"
      />
      <span v-else-if="app.tarefa.status === 'concluida'" class="text-ok">✓</span>
      <span v-else class="text-erro">!</span>
      <span class="font-medium">{{ app.nomes[app.tarefa.tipo] ?? app.tarefa.tipo }}</span>
      <span class="truncate text-texto-2">{{ app.tarefa.mensagem }}</span>
    </div>
    <div v-if="app.tarefa.status === 'rodando'" class="mt-2 h-1.5 overflow-hidden rounded-full bg-superficie-2">
      <div v-if="pct !== null" class="h-full bg-marca transition-all" :style="{ width: `${pct}%` }" />
      <div v-else class="h-full w-1/3 animate-pulse bg-marca/60" />
    </div>
  </div>
</template>
