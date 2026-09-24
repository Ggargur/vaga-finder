<script setup lang="ts">
import { fechar, toasts } from '../composables/toast'

const cores = {
  ok: 'border-ok/40 bg-ok-suave text-ok',
  erro: 'border-erro/40 bg-erro-suave text-erro',
  info: 'border-borda bg-superficie text-texto',
}
</script>

<template>
  <div class="pointer-events-none fixed right-4 bottom-4 left-4 z-50 flex flex-col items-end gap-2 sm:left-auto">
    <TransitionGroup
      enter-from-class="opacity-0 translate-y-2"
      leave-to-class="opacity-0"
      enter-active-class="transition duration-200"
      leave-active-class="transition duration-200"
    >
      <div
        v-for="t in toasts"
        :key="t.id"
        role="status"
        class="pointer-events-auto flex w-full max-w-md items-start gap-3 rounded-lg border px-4 py-3 text-sm shadow-lg"
        :class="cores[t.tipo]"
      >
        <span class="flex-1 whitespace-pre-line">{{ t.texto }}</span>
        <button class="opacity-60 hover:opacity-100" aria-label="Fechar" @click="fechar(t.id)">✕</button>
      </div>
    </TransitionGroup>
  </div>
</template>
