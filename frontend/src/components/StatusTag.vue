<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ status: string | null | undefined }>()

const MAPA: Record<string, [string, string]> = {
  nova: ['Nova', 'bg-superficie-2 text-texto-2'],
  filtrada: ['Filtrada', 'bg-superficie-2 text-texto-2'],
  avaliada: ['Avaliada', 'bg-marca-suave text-marca'],
  aplicada: ['Aplicada', 'bg-ok-suave text-ok'],
  pendente: ['Pendente', 'bg-atencao-suave text-atencao'],
  aprovado: ['Na fila', 'bg-marca-suave text-marca'],
  enviado: ['Enviado', 'bg-ok-suave text-ok'],
  rejeitado: ['Rejeitado', 'bg-superficie-2 text-texto-2'],
  erro: ['Erro', 'bg-erro-suave text-erro'],
}

const info = computed(() => MAPA[props.status ?? ''] ?? [props.status ?? '', 'bg-superficie-2 text-texto-2'])
</script>

<template>
  <span v-if="status" class="inline-flex rounded-full px-2 py-0.5 text-xs font-medium whitespace-nowrap" :class="info[1]">
    {{ info[0] }}
  </span>
</template>
