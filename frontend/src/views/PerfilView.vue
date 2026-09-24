<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { api } from '../api/client'
import type { Perfil } from '../api/tipos'
import CampoLista from '../components/CampoLista.vue'
import { tentar } from '../composables/toast'
import { useApp } from '../stores/app'

const app = useApp()
const perfil = ref<Perfil | null>(null)
const enviando = ref(false)
const salvando = ref(false)
const arrastando = ref(false)
const entrada = ref<HTMLInputElement | null>(null)

const SENIORIDADES = ['estagio', 'junior', 'pleno', 'senior', 'especialista', 'lideranca']

onMounted(async () => {
  perfil.value = (await tentar(() => api.perfil())) ?? null
})

async function enviar(arquivo: File | undefined) {
  if (!arquivo) return
  if (arquivo.type !== 'application/pdf' && !arquivo.name.toLowerCase().endsWith('.pdf')) {
    await tentar(() => Promise.reject(new Error('Envie o currículo em PDF.')))
    return
  }
  enviando.value = true
  const p = await tentar(() => api.enviarCurriculo(arquivo), 'Perfil gerado. Confira os dados abaixo.')
  enviando.value = false
  if (p) {
    perfil.value = p
    app.mudou()
  }
}

function aoSoltar(e: DragEvent) {
  arrastando.value = false
  enviar(e.dataTransfer?.files[0])
}

async function salvar() {
  if (!perfil.value) return
  salvando.value = true
  await tentar(() => api.salvarPerfil(perfil.value!), 'Perfil salvo.')
  salvando.value = false
}

function novaExperiencia() {
  perfil.value?.experiencias.unshift({ cargo: '', empresa: '', periodo: '', destaques: [] })
}
</script>

<template>
  <header class="flex flex-wrap items-end justify-between gap-3">
    <div>
      <h1 class="text-2xl font-semibold tracking-tight">Perfil</h1>
      <p class="text-sm text-texto-2">
        O Claude usa este perfil para dar nota às vagas e escrever os emails. Ele nunca cita algo que não esteja aqui.
      </p>
    </div>
    <button v-if="perfil" class="botao primario" :disabled="salvando" @click="salvar">
      {{ salvando ? 'Salvando…' : 'Salvar perfil' }}
    </button>
  </header>

  <div
    class="cartao flex flex-col items-center gap-3 border-2 border-dashed px-6 py-8 text-center transition"
    :class="arrastando ? 'border-marca bg-marca-suave' : ''"
    @dragover.prevent="arrastando = true"
    @dragleave="arrastando = false"
    @drop.prevent="aoSoltar"
  >
    <template v-if="enviando">
      <span class="h-6 w-6 animate-spin rounded-full border-2 border-marca border-t-transparent" aria-hidden="true" />
      <p class="text-sm">Lendo o currículo com o Claude. Leva uns 30 segundos.</p>
    </template>
    <template v-else>
      <p class="font-medium">{{ perfil ? 'Enviar uma nova versão do currículo' : 'Envie seu currículo em PDF' }}</p>
      <p class="text-sm text-texto-2">
        Arraste o arquivo aqui ou
        <button class="link" @click="entrada?.click()">escolha no computador</button>.
        <template v-if="perfil"> O perfil atual será substituído.</template>
      </p>
      <a v-if="app.estado?.tem_curriculo" href="/api/perfil/curriculo" target="_blank" class="link text-xs">
        Ver currículo atual
      </a>
    </template>
    <input
      ref="entrada"
      type="file"
      accept="application/pdf,.pdf"
      class="hidden"
      @change="enviar(($event.target as HTMLInputElement).files?.[0])"
    />
  </div>

  <template v-if="perfil">
    <section class="cartao grid gap-4 p-5 md:grid-cols-2">
      <label>
        <span class="rotulo">Nome</span>
        <input v-model="perfil.nome" class="campo" />
      </label>
      <label>
        <span class="rotulo">Localização</span>
        <input v-model="perfil.localizacao" class="campo" />
      </label>
      <label>
        <span class="rotulo">Senioridade</span>
        <select v-model="perfil.senioridade" class="campo">
          <option v-for="s in SENIORIDADES" :key="s" :value="s">{{ s }}</option>
        </select>
      </label>
      <label>
        <span class="rotulo">Anos de experiência</span>
        <input v-model.number="perfil.anos_experiencia" type="number" min="0" class="campo" />
      </label>
      <label class="md:col-span-2">
        <span class="rotulo">Resumo</span>
        <textarea v-model="perfil.resumo" rows="3" class="campo" />
      </label>
      <CampoLista v-model="perfil.links" rotulo="Links (vão na assinatura)" :linhas="3" placeholder="https://linkedin.com/in/…" />
      <div class="space-y-3">
        <label class="flex items-center gap-2 text-sm">
          <input v-model="perfil.preferencias.remoto" type="checkbox" class="h-4 w-4 accent-[var(--marca)]" />
          Prefiro vagas remotas
        </label>
        <CampoLista v-model="perfil.preferencias.locais" rotulo="Cidades aceitas" :linhas="2" />
      </div>
    </section>

    <section class="cartao grid gap-4 p-5 md:grid-cols-3">
      <CampoLista
        v-model="perfil.cargos_alvo"
        rotulo="Cargos-alvo"
        :linhas="6"
        ajuda="Usados como termos de busca se você quiser."
      />
      <CampoLista
        v-model="perfil.palavras_chave"
        rotulo="Palavras-chave"
        :linhas="6"
        ajuda="Vagas sem nenhuma delas são descartadas antes de gastar cota do Claude."
      />
      <CampoLista v-model="perfil.skills" rotulo="Skills" :linhas="6" />
    </section>

    <section class="cartao space-y-4 p-5">
      <div class="flex items-center justify-between">
        <h2 class="font-medium">Experiências</h2>
        <button class="botao pequeno" @click="novaExperiencia">Adicionar</button>
      </div>
      <div
        v-for="(xp, i) in perfil.experiencias"
        :key="i"
        class="grid gap-3 rounded-lg border border-borda p-4 md:grid-cols-3"
      >
        <label>
          <span class="rotulo">Cargo</span>
          <input v-model="xp.cargo" class="campo" />
        </label>
        <label>
          <span class="rotulo">Empresa</span>
          <input v-model="xp.empresa" class="campo" />
        </label>
        <label>
          <span class="rotulo">Período</span>
          <input v-model="xp.periodo" class="campo" />
        </label>
        <div class="md:col-span-3">
          <CampoLista
            v-model="xp.destaques"
            rotulo="Resultados e destaques (um por linha)"
            :linhas="3"
            ajuda="Números concretos rendem os melhores emails."
          />
        </div>
        <button class="botao perigo pequeno w-fit" @click="perfil.experiencias.splice(i, 1)">Remover</button>
      </div>
    </section>

    <section class="cartao grid gap-4 p-5 md:grid-cols-2">
      <CampoLista v-model="perfil.formacao" rotulo="Formação" :linhas="3" />
      <div>
        <span class="rotulo">Idiomas</span>
        <div v-for="(id, i) in perfil.idiomas" :key="i" class="mb-2 flex gap-2">
          <input v-model="id.idioma" class="campo" placeholder="Idioma" />
          <input v-model="id.nivel" class="campo" placeholder="Nível" />
          <button class="botao perigo pequeno" aria-label="Remover idioma" @click="perfil.idiomas.splice(i, 1)">✕</button>
        </div>
        <button class="botao pequeno" @click="perfil.idiomas.push({ idioma: '', nivel: '' })">Adicionar idioma</button>
      </div>
    </section>

    <div class="flex justify-end">
      <button class="botao primario" :disabled="salvando" @click="salvar">
        {{ salvando ? 'Salvando…' : 'Salvar perfil' }}
      </button>
    </div>
  </template>
</template>
