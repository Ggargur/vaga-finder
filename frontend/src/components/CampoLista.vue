<script setup lang="ts">
import { ref, watch } from 'vue'

/** Edita uma lista de textos, um por linha. */
const lista = defineModel<string[]>({ required: true })
defineProps<{ rotulo: string; ajuda?: string; linhas?: number; placeholder?: string }>()

const texto = ref(lista.value.join('\n'))
watch(lista, (v) => {
  if (v.join('\n') !== texto.value.split('\n').map((l) => l.trim()).filter(Boolean).join('\n')) texto.value = v.join('\n')
})
watch(texto, (t) => {
  lista.value = t
    .split('\n')
    .map((l) => l.trim())
    .filter(Boolean)
})
</script>

<template>
  <label class="block">
    <span class="rotulo">{{ rotulo }}</span>
    <textarea v-model="texto" class="campo font-mono text-[13px]" :rows="linhas ?? 4" :placeholder="placeholder" />
    <span v-if="ajuda" class="mt-1 block text-xs text-texto-2">{{ ajuda }}</span>
  </label>
</template>
