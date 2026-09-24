<script setup lang="ts">
defineProps<{ titulo: string; texto?: string }>()
</script>

<template>
  <div class="cartao flex flex-col items-center px-6 py-14 text-center">
    <p class="text-base font-medium">{{ titulo }}</p>
    <p v-if="texto" class="mt-1 max-w-md text-sm text-texto-2">{{ texto }}</p>
    <div v-if="$slots.default" class="mt-5 flex flex-wrap justify-center gap-2"><slot /></div>
  </div>
</template>
