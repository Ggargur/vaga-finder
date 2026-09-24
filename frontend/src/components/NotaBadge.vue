<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ nota: number | null | undefined }>()

const classe = computed(() => {
  const n = props.nota
  if (n == null) return 'bg-superficie-2 text-texto-2'
  if (n >= 80) return 'bg-ok-suave text-ok'
  if (n >= 60) return 'bg-atencao-suave text-atencao'
  return 'bg-erro-suave text-erro'
})
</script>

<template>
  <span
    class="inline-flex h-8 min-w-10 items-center justify-center rounded-md px-2 text-sm font-semibold tabular-nums"
    :class="classe"
    :title="nota == null ? 'Ainda não avaliada' : `Aderência ${nota}/100`"
  >
    {{ nota ?? '—' }}
  </span>
</template>
