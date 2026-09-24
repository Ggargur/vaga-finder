<script setup lang="ts">
import { onBeforeUnmount, watch } from 'vue'

const aberto = defineModel<boolean>('aberto', { required: true })
defineProps<{ titulo?: string; largo?: boolean }>()

function aoTeclar(e: KeyboardEvent) {
  if (e.key === 'Escape') aberto.value = false
}

watch(aberto, (v) => {
  if (v) document.addEventListener('keydown', aoTeclar)
  else document.removeEventListener('keydown', aoTeclar)
})
onBeforeUnmount(() => document.removeEventListener('keydown', aoTeclar))
</script>

<template>
  <Teleport to="body">
    <div v-if="aberto" class="fixed inset-0 z-40 flex items-end justify-center bg-black/40 sm:items-center sm:p-6" @click.self="aberto = false">
      <div
        role="dialog"
        aria-modal="true"
        class="cartao flex max-h-[92vh] w-full flex-col shadow-xl"
        :class="largo ? 'sm:max-w-4xl' : 'sm:max-w-lg'"
      >
        <header class="flex items-start gap-3 border-b border-borda px-5 py-4">
          <h2 class="flex-1 text-base font-semibold">
            <slot name="titulo">{{ titulo }}</slot>
          </h2>
          <button class="text-texto-2 hover:text-texto" aria-label="Fechar" @click="aberto = false">✕</button>
        </header>
        <div class="overflow-y-auto px-5 py-4">
          <slot />
        </div>
        <footer v-if="$slots.rodape" class="flex flex-wrap justify-end gap-2 border-t border-borda px-5 py-3">
          <slot name="rodape" />
        </footer>
      </div>
    </div>
  </Teleport>
</template>
