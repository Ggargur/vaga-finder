<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { api } from '../api/client'
import type { Config } from '../api/tipos'
import CampoLista from '../components/CampoLista.vue'
import { avisar, tentar } from '../composables/toast'
import { useApp } from '../stores/app'

const app = useApp()
const cfg = ref<Config | null>(null)
const salvando = ref(false)
const testando = ref(false)

const MODELOS = [
  { valor: 'haiku', rotulo: 'Haiku (rápido, gasta menos cota)' },
  { valor: 'sonnet', rotulo: 'Sonnet (equilibrado)' },
  { valor: 'opus', rotulo: 'Opus (melhor texto, gasta mais cota)' },
]

const FONTES_SIMPLES = [
  { chave: 'gupy', nome: 'Gupy', desc: 'Vagas de empresas brasileiras.' },
  { chave: 'remotive', nome: 'Remotive', desc: 'Remotas internacionais.' },
  { chave: 'remoteok', nome: 'RemoteOK', desc: 'Remotas internacionais.' },
  { chave: 'himalayas', nome: 'Himalayas', desc: 'Remotas internacionais.' },
] as const

onMounted(async () => {
  cfg.value = (await tentar(() => api.config())) ?? null
})

async function salvar() {
  if (!cfg.value) return
  salvando.value = true
  const c = await tentar(() => api.salvarConfig(cfg.value!), 'Configuração salva.')
  salvando.value = false
  if (c) {
    cfg.value = c
    app.mudou()
  }
}

async function enviarTeste() {
  testando.value = true
  const r = await tentar(() => api.enviarTeste())
  testando.value = false
  if (r) avisar(`Email de teste enviado para ${r.enviado_para}. Confira a caixa de entrada.`, 'ok')
}
</script>

<template>
  <header class="flex flex-wrap items-end justify-between gap-3">
    <div>
      <h1 class="text-2xl font-semibold tracking-tight">Config</h1>
      <p class="text-sm text-texto-2">Salvo em backend/config.yaml.</p>
    </div>
    <button class="botao primario" :disabled="salvando || !cfg" @click="salvar">
      {{ salvando ? 'Salvando…' : 'Salvar' }}
    </button>
  </header>

  <template v-if="cfg">
    <section class="cartao space-y-4 p-5">
      <h2 class="font-medium">Gmail</h2>
      <p v-if="app.estado?.gmail_configurado" class="text-sm">
        Enviando como <strong>{{ app.estado.gmail_user }}</strong>.
      </p>
      <div v-else class="rounded-lg bg-atencao-suave px-4 py-3 text-sm text-atencao">
        Preencha <code>GMAIL_USER</code> e <code>GMAIL_APP_PASSWORD</code> em <code>backend/.env</code> e reinicie o servidor.
        A senha de app é gerada em
        <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noopener" class="underline">myaccount.google.com/apppasswords</a>
        (exige verificação em 2 etapas).
      </div>
      <div class="flex flex-wrap gap-2">
        <button class="botao" :disabled="!app.estado?.gmail_configurado || testando" @click="enviarTeste">
          {{ testando ? 'Enviando…' : 'Enviar email de teste para mim' }}
        </button>
        <button
          class="botao"
          :disabled="!app.estado?.gmail_configurado || app.tarefa?.status === 'rodando'"
          @click="app.iniciar('sincronizar')"
        >
          Sincronizar Enviados
        </button>
      </div>
    </section>

    <section class="cartao grid gap-4 p-5 md:grid-cols-3">
      <h2 class="font-medium md:col-span-3">Busca</h2>
      <CampoLista
        v-model="cfg.busca.termos"
        rotulo="Termos de busca"
        :linhas="5"
        ajuda="Cada termo vira uma busca em cada fonte."
      />
      <CampoLista
        v-model="cfg.busca.exclusoes"
        rotulo="Descartar títulos com"
        :linhas="5"
        ajuda="Ex.: estágio, júnior, java."
      />
      <CampoLista
        v-model="cfg.busca.palavras_chave"
        rotulo="Palavras-chave do filtro"
        :linhas="5"
        ajuda="Vazio = usa as do seu perfil."
      />
      <label>
        <span class="rotulo">Máximo de vagas por fonte</span>
        <input v-model.number="cfg.busca.limite_por_fonte" type="number" min="1" max="500" class="campo" />
      </label>
    </section>

    <section class="cartao space-y-4 p-5">
      <h2 class="font-medium">Fontes</h2>
      <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <label v-for="f in FONTES_SIMPLES" :key="f.chave" class="flex gap-3 rounded-lg border border-borda p-3 text-sm">
          <input v-model="cfg.fontes[f.chave]" type="checkbox" class="mt-0.5 h-4 w-4 accent-[var(--marca)]" />
          <span>
            <span class="block font-medium">{{ f.nome }}</span>
            <span class="text-texto-2">{{ f.desc }}</span>
          </span>
        </label>
      </div>
      <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <CampoLista
          v-model="cfg.fontes.greenhouse"
          rotulo="Empresas no Greenhouse"
          :linhas="4"
          placeholder="gitlab"
          ajuda="O slug da URL boards.greenhouse.io/<slug>."
        />
        <CampoLista
          v-model="cfg.fontes.lever"
          rotulo="Empresas no Lever"
          :linhas="4"
          placeholder="spotify"
          ajuda="O slug da URL jobs.lever.co/<slug>."
        />
        <CampoLista
          v-model="cfg.fontes.ashby"
          rotulo="Empresas no Ashby"
          :linhas="4"
          placeholder="nubank"
          ajuda="O slug da URL jobs.ashbyhq.com/<slug>."
        />
        <CampoLista
          v-model="cfg.fontes.paginas"
          rotulo="Páginas de carreira"
          :linhas="4"
          placeholder="https://empresa.com/carreiras"
          ajuda="Se a página usar Greenhouse, Lever ou Ashby, o vaga-finder usa a API deles."
        />
      </div>
      <div class="rounded-lg border border-atencao/40 bg-atencao-suave p-4 text-sm">
        <label class="flex items-start gap-3">
          <input v-model="cfg.fontes.linkedin" type="checkbox" class="mt-0.5 h-4 w-4 accent-[var(--atencao)]" />
          <span>
            <span class="block font-medium text-atencao">LinkedIn (use por sua conta e risco)</span>
            <span class="text-texto-2">
              Os termos do LinkedIn proíbem coleta automatizada, e o IP pode ser bloqueado. O coletor usa só a busca
              pública, sem login, e poucas páginas por rodada.
            </span>
          </span>
        </label>
        <label v-if="cfg.fontes.linkedin" class="mt-3 block max-w-xs">
          <span class="rotulo">Localização no LinkedIn</span>
          <input v-model="cfg.fontes.linkedin_local" class="campo" />
        </label>
      </div>
    </section>

    <section class="cartao grid gap-4 p-5 md:grid-cols-3">
      <h2 class="font-medium md:col-span-3">Avaliação</h2>
      <label>
        <span class="rotulo">Nota mínima para redigir email: {{ cfg.avaliacao.nota_minima }}</span>
        <input v-model.number="cfg.avaliacao.nota_minima" type="range" min="0" max="100" step="5" class="w-full accent-[var(--marca)]" />
      </label>
      <label>
        <span class="rotulo">Modelo</span>
        <select v-model="cfg.avaliacao.modelo" class="campo">
          <option v-for="m in MODELOS" :key="m.valor" :value="m.valor">{{ m.rotulo }}</option>
        </select>
      </label>
      <label>
        <span class="rotulo">Vagas por chamada</span>
        <input v-model.number="cfg.avaliacao.lote" type="number" min="1" max="10" class="campo" />
      </label>
    </section>

    <section class="cartao grid gap-4 p-5 md:grid-cols-3">
      <h2 class="font-medium md:col-span-3">Redação</h2>
      <label>
        <span class="rotulo">Modelo</span>
        <select v-model="cfg.redacao.modelo" class="campo">
          <option v-for="m in MODELOS" :key="m.valor" :value="m.valor">{{ m.rotulo }}</option>
        </select>
      </label>
      <label>
        <span class="rotulo">Palavras (mín.)</span>
        <input v-model.number="cfg.redacao.palavras_min" type="number" min="40" class="campo" />
      </label>
      <label>
        <span class="rotulo">Palavras (máx.)</span>
        <input v-model.number="cfg.redacao.palavras_max" type="number" min="60" class="campo" />
      </label>
      <label class="md:col-span-3">
        <span class="rotulo">Assinatura fixa (opcional)</span>
        <textarea
          v-model="cfg.redacao.assinatura"
          rows="3"
          class="campo"
          placeholder="Vazio = nome e links do perfil"
        />
      </label>
    </section>

    <section class="cartao grid gap-4 p-5 md:grid-cols-3">
      <h2 class="font-medium md:col-span-3">Envio</h2>
      <label>
        <span class="rotulo">Limite por dia</span>
        <input v-model.number="cfg.envio.limite_diario" type="number" min="1" max="100" class="campo" />
      </label>
      <label>
        <span class="rotulo">Dias até escrever de novo ao mesmo contato</span>
        <input v-model.number="cfg.envio.dias_entre_contatos" type="number" min="0" class="campo" />
      </label>
      <div class="grid grid-cols-2 gap-2">
        <label>
          <span class="rotulo">Pausa mín. (s)</span>
          <input v-model.number="cfg.envio.pausa_min_s" type="number" min="0" class="campo" />
        </label>
        <label>
          <span class="rotulo">Pausa máx. (s)</span>
          <input v-model.number="cfg.envio.pausa_max_s" type="number" min="0" class="campo" />
        </label>
      </div>
      <label class="flex items-center gap-2 text-sm md:col-span-3">
        <input v-model="cfg.envio.anexar_curriculo" type="checkbox" class="h-4 w-4 accent-[var(--marca)]" />
        Anexar o currículo em PDF
      </label>
    </section>

    <div class="flex justify-end">
      <button class="botao primario" :disabled="salvando" @click="salvar">{{ salvando ? 'Salvando…' : 'Salvar' }}</button>
    </div>
  </template>
</template>
