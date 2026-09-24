<script setup lang="ts">
import type { Aviso } from '../api/tipos'

defineProps<{ avisos: Aviso[] }>()
</script>

<template>
  <ul v-if="avisos.length" class="space-y-1.5">
    <li
      v-for="(a, i) in avisos"
      :key="i"
      class="flex gap-2 rounded-lg px-3 py-2 text-sm"
      :class="a.tipo === 'historico' ? 'bg-erro-suave text-erro' : 'bg-atencao-suave text-atencao'"
    >
      <span aria-hidden="true">{{ a.tipo === 'historico' ? '⟲' : '✎' }}</span>
      <span>
        {{ a.mensagem }}
        <q v-if="a.trecho" class="font-medium">{{ a.trecho }}</q>
      </span>
    </li>
  </ul>
</template>
